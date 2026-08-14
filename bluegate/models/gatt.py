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
# Copyright 2026 Sebastien Demanou. All Rights Reserved.
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


class GattService(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: str = Field(..., description="D-Bus object path segment identifying the service.")
  object_path: str = Field(..., description="D-Bus object path of the service.")
  device_id: str = Field(..., description="Identifier of the parent device.")
  uuid: str = Field(..., description="128-bit service UUID.")
  primary: bool = Field(..., description="Whether this is a primary service.")


class GattCharacteristic(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: str = Field(..., description="D-Bus object path segment identifying the characteristic.")
  object_path: str = Field(..., description="D-Bus object path of the characteristic.")
  device_id: str = Field(..., description="Identifier of the parent device.")
  service_id: str = Field(..., description="Identifier of the parent service.")
  uuid: str = Field(..., description="128-bit characteristic UUID.")
  flags: list[str] = Field(default_factory=list, description="Supported operations (read, write, notify, ...).")
  notifying: bool = Field(default=False, description="Whether value change notifications are active.")
  value: str | None = Field(default=None, description="Last known value, hex-encoded.")


class GattDescriptor(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: str = Field(..., description="D-Bus object path segment identifying the descriptor.")
  object_path: str = Field(..., description="D-Bus object path of the descriptor.")
  device_id: str = Field(..., description="Identifier of the parent device.")
  service_id: str = Field(..., description="Identifier of the parent service.")
  characteristic_id: str = Field(..., description="Identifier of the parent characteristic.")
  uuid: str = Field(..., description="128-bit descriptor UUID.")
  flags: list[str] = Field(default_factory=list, description="Supported operations (read, write, ...).")
  value: str | None = Field(default=None, description="Last known value, hex-encoded.")


class GattValueWrite(BaseModel):
  model_config = ConfigDict(extra="forbid")

  value: str = Field(..., description="Hex-encoded bytes to write (e.g. 'a1b2c3').")
