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
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class Device(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: str = Field(..., description="Stable device identifier. Uses MAC address when available.")
  object_path: str = Field(..., description="D-Bus object path of the device.")
  adapter_id: str = Field(..., description="Identifier of the parent adapter.")
  name: str | None = Field(default=None, description="Remote device name.")
  alias: str | None = Field(default=None, description="Remote device alias.")
  address: str | None = Field(default=None, description="Remote MAC address.")
  address_type: str | None = Field(default=None, description="Address type (public, random, etc.).")
  icon: str | None = Field(default=None, description="Icon hint exposed by BlueZ.")
  device_class: int | None = Field(default=None, description="Bluetooth class for classic devices.")
  appearance: int | None = Field(default=None, description="BLE appearance value.")
  rssi: int | None = Field(default=None, description="Most recent RSSI value in dBm.")
  battery_level: int | None = Field(default=None, ge=0, le=100, description="Battery level percentage when exposed by BlueZ.")
  tx_power: int | None = Field(default=None, description="Most recent TxPower value in dBm.")
  paired: bool = Field(..., description="Whether the device is paired.")
  trusted: bool = Field(..., description="Whether the device is trusted.")
  connected: bool = Field(..., description="Whether the device is connected.")
  blocked: bool = Field(..., description="Whether the device is blocked.")
  services_resolved: bool = Field(..., description="Whether GATT/services were resolved.")
  uuids: list[str] = Field(default_factory=list, description="Advertised UUIDs.")


class DevicePatch(BaseModel):
  model_config = ConfigDict(extra="forbid")

  alias: str | None = Field(default=None, description="Set remote device alias as reported by BlueZ.")
