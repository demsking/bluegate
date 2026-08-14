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
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
  """Application configuration settings for BlueGate.

  All settings can be configured via environment variables.
  Service URLs are optional - if not provided, the service will run in chat-only mode.
  """

  model_config = SettingsConfigDict(
    env_prefix="BLUEGATE_",
    strict=True,
    extra="ignore",
  )

  server_host: str = Field(
    default="127.0.0.1",
    description="Host address to bind the server to. Use '0.0.0.0' to listen on all interfaces.",
  )

  server_port: int = Field(
    default=8765,
    ge=1,
    le=65535,
    description="Port number to bind the server to. Must be between 1 and 65535.",
  )

  api_prefix: str = Field(default="/api", description="API prefix for all endpoints.")

  log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="Logging level.")  # pyrefly: ignore [bad-assignment]
  log_file: str | None = Field(default=None, description="Path to rotating log file.")

  dbus_system_bus: str | None = Field(
    default=None,
    description="Optional system bus address. If unset, dbus-next will use the default system bus socket.",
  )

  bluetooth_agent_capability: Literal[
    "DisplayOnly",
    "DisplayYesNo",
    "KeyboardOnly",
    "NoInputNoOutput",
    "KeyboardDisplay",
  ] = Field(default="DisplayYesNo", description="BlueZ agent IO capability.")

  scan_timeout: int = Field(default=20, ge=1, le=600, description="Default Bluetooth scan timeout in seconds.")
  websocket_heartbeat: int = Field(
    default=30,
    ge=5,
    le=300,
    description="WebSocket heartbeat interval in seconds.",
  )

  cors_allowed_origins: Any = Field(
    default_factory=lambda: ["*"],
    description=("Allowed CORS origins for browser clients."),
  )

  @field_validator("api_prefix")
  @classmethod
  def validate_api_prefix(cls, value: str) -> str:
    if not value.startswith("/"):
      raise ValueError("BLUEGATE_API_PREFIX must start with '/'")

    return value.rstrip("/") or "/"

  @field_validator("dbus_system_bus")
  @classmethod
  def validate_dbus_system_bus(cls, value: str | None) -> str | None:
    if value is None:
      return None

    normalized = value.strip()
    return normalized or None

  @field_validator("cors_allowed_origins", mode="before")
  @classmethod
  def validate_cors_allowed_origins(cls, value: list[str] | str) -> list[str]:
    if isinstance(value, list):
      origins = [str(origin).strip() for origin in value if str(origin).strip()]

      return origins or ["*"]

    raw = value.strip()

    if not raw:
      return ["*"]

    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]

    return origins or ["*"]


@lru_cache
def get_settings() -> Settings:
  """Return cached application settings."""
  return Settings()


def _format(value: Any) -> str:
  if value is None:
    return "None"

  if isinstance(value, Path):
    return str(value)

  if isinstance(value, list):
    return ",".join(str(item) for item in value)

  return str(value)


SENSITIVE_FIELDS = {"mqtt_password", "mqtt_tls_ca_cert"}


def log_group(settings: Settings, name: str, *fields: str) -> None:
  """Log a group of related settings without exposing sensitive credentials."""
  values: list[str] = []

  for field in fields:
    value = getattr(settings, field)
    if field in SENSITIVE_FIELDS and value:
      formatted_val = "[set]"
    else:
      formatted_val = _format(value)

    values.append(f"{field}={formatted_val}")

  logger.info("%s settings: %s", name, " ".join(values))
