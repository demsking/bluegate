# Copyright 2026 Sébastien Demanou. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse

from bluegate.api import adapters
from bluegate.api import devices
from bluegate.api import docs
from bluegate.api import gatt
from bluegate.api import health
from bluegate.api import pairing
from bluegate.api import websocket
from bluegate.api.errors import ApiException
from bluegate.bluetooth import create_bluetooth_manager
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.core.package import APP_DESCRIPTION
from bluegate.core.package import APP_NAME
from bluegate.core.package import APP_VERSION
from bluegate.core.settings import log_group
from bluegate.core.settings import Settings
from bluegate.models.error import ApiError
from bluegate.utils.logger import configure_logging


logger = logging.getLogger(__name__)


def create_app(settings: Settings) -> FastAPI:
  @asynccontextmanager
  async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    startup_started = perf_counter()
    ready = False

    configure_logging(settings.log_level, settings.log_file)

    logger.info(f"{APP_NAME} v{APP_VERSION}")
    log_group(settings, "Server", "server_host", "server_port", "api_prefix")
    log_group(settings, "CORS", "cors_allowed_origins")
    log_group(settings, "Logging", "log_level", "log_file")
    log_group(
      settings,
      "Bluetooth",
      "dbus_system_bus",
      "bluetooth_agent_capability",
      "scan_timeout",
      "websocket_heartbeat",
    )

    event_broker = BluetoothEventBroker()
    bluetooth_manager = create_bluetooth_manager(
      settings.dbus_system_bus,
      event_broker,
      settings.bluetooth_agent_capability,
    )
    app.state.bluetooth_manager = bluetooth_manager
    app.state.event_broker = event_broker
    app.state.websocket_heartbeat = settings.websocket_heartbeat

    try:
      await bluetooth_manager.initialize()
      app.state.pairing_agent = getattr(bluetooth_manager, "pairing_agent", None)
      ready = True
      logger.info(f"BlueGate ready: duration_ms={(perf_counter() - startup_started) * 1000:.1f}")

      yield
    finally:
      shutdown_started = perf_counter()

      if ready:
        logger.info("Shutting down BlueGate")
      else:
        logger.warning("BlueGate startup aborted; cleaning up resources")

      await app.state.bluetooth_manager.shutdown()

      logger.info(f"BlueGate stopped: duration_ms={(perf_counter() - shutdown_started) * 1000:.1f}")

  app = FastAPI(
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    title="BlueGate",
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    root_path="",
    servers=[
      {"url": settings.api_prefix},
    ],
    license_info={
      "name": "Apache 2.0",
      "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=[
      health.API_TAG_METADATA,
      adapters.API_TAG_METADATA,
      devices.API_TAG_METADATA,
      gatt.API_TAG_METADATA,
      pairing.API_TAG_METADATA,
      websocket.API_TAG_METADATA,
    ],
  )

  if len(settings.cors_allowed_origins) > 0:
    app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.cors_allowed_origins,
      allow_credentials=False,
      allow_methods=["*"],
      allow_headers=["*"],
    )
  else:
    logger.info("CORS middleware disabled: no allowed origins configured")

  @app.exception_handler(ApiException)
  async def api_exception_handler(_: Request, exc: ApiException) -> JSONResponse:
    payload = ApiError(code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

  @app.exception_handler(Exception)
  async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    payload = ApiError(code="INTERNAL_ERROR", message="Internal server error.", details={})
    return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))

  @app.get("/", include_in_schema=False)
  async def redirect_to_docs() -> HTMLResponse:
    return HTMLResponse(status_code=307, headers={"Location": prefix + docs.router.prefix + "/"})

  prefix = "" if settings.api_prefix == "/" else settings.api_prefix
  api_prefix = f"{prefix}/api" if prefix else "/api"

  app.include_router(health.router, prefix=prefix)
  app.include_router(adapters.router, prefix=api_prefix)
  app.include_router(devices.router, prefix=api_prefix)
  app.include_router(gatt.router, prefix=api_prefix)
  app.include_router(pairing.router, prefix=api_prefix)
  app.include_router(docs.router, prefix=prefix)
  app.include_router(websocket.router, prefix=api_prefix)
  app.include_router(websocket.router, prefix=prefix)

  return app
