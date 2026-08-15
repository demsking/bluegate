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
from bluegate.core.settings import Settings


def test_api_prefix_is_normalized() -> None:
  settings = Settings(api_prefix="/api/")
  assert settings.api_prefix == "/api"


def test_dbus_system_bus_empty_is_none() -> None:
  settings = Settings(dbus_system_bus="   ")
  assert settings.dbus_system_bus is None


def test_cors_allowed_origins_accepts_comma_separated_values() -> None:
  settings = Settings(cors_allowed_origins="http://localhost:8080, https://ui.example.com")
  assert settings.cors_allowed_origins == ["http://localhost:8080", "https://ui.example.com"]


def test_cors_allowed_origins_accepts_json_array() -> None:
  settings = Settings(cors_allowed_origins='["http://localhost:8080", "https://ui.example.com"]')
  assert settings.cors_allowed_origins == ["http://localhost:8080", "https://ui.example.com"]


def test_cors_allowed_origins_defaults_to_disabled() -> None:
  settings = Settings()
  assert settings.cors_allowed_origins == []


def test_cors_allowed_origins_empty_string_disables_cors() -> None:
  settings = Settings(cors_allowed_origins="   ")
  assert settings.cors_allowed_origins == []
