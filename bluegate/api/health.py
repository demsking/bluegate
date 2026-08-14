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
from fastapi import APIRouter
from fastapi import Request

from bluegate.core.package import APP_VERSION
from bluegate.models.health import HealthStatus


API_TAG_METADATA = {
  "name": "Server Endpoints",
  "description": (
    "Operational health and readiness endpoints. Use this tag for lightweight "
    "checks that confirm the API process is alive and report basic runtime "
    "metadata such as the version."
  ),
}

router = APIRouter(prefix="/health", tags=[API_TAG_METADATA["name"]])


@router.get(
  "/",
  summary="Health check",
  description=(
    "Return a lightweight health response for load balancers, Docker health checks, and monitoring tools. "
    "The response confirms the API is alive and includes the application version."
  ),
  responses={
    200: {
      "content": {
        "application/json": {
          "example": HealthStatus.model_validate(
            {
              "status": "healthy",
              "application": "ready",
              "dbus": "connected",
              "bluez": "available",
              "adapters": 1,
              "version": APP_VERSION,
            }
          )
        }
      }
    }
  },
)
async def health(request: Request) -> HealthStatus:
  manager = getattr(request.app.state, "bluetooth_manager", None)
  if manager is None:
    return HealthStatus(
      status="degraded",
      dbus="disconnected",
      bluez="unavailable",
      adapters=0,
      version=APP_VERSION,
    )

  adapters = await manager.list_adapters() if manager.bluez_available else []
  dbus_status = "connected" if manager.dbus_connected else "disconnected"
  bluez_status = "available" if manager.bluez_available else "unavailable"
  global_status = "healthy" if dbus_status == "connected" and bluez_status == "available" else "degraded"

  return HealthStatus(
    status=global_status,
    dbus=dbus_status,
    bluez=bluez_status,
    adapters=len(adapters),
    version=APP_VERSION,
  )
