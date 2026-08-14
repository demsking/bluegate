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


class Adapter(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: str = Field(..., description="BlueZ adapter identifier (example: hci0).")
  object_path: str = Field(..., description="D-Bus object path of the adapter.")
  name: str | None = Field(default=None, description="Adapter name as reported by BlueZ.")
  alias: str | None = Field(default=None, description="Adapter alias as reported by BlueZ.")
  address: str | None = Field(default=None, description="Adapter MAC address.")
  powered: bool = Field(..., description="Whether the adapter is powered.")
  discoverable: bool = Field(..., description="Whether the adapter is discoverable.")
  pairable: bool = Field(..., description="Whether the adapter accepts pairing requests.")
  discovering: bool = Field(..., description="Whether discovery is currently active.")
  device_count: int = Field(..., ge=0, description="Number of known devices attached to this adapter.")


class AdapterPatch(BaseModel):
  model_config = ConfigDict(extra="forbid")

  powered: bool | None = Field(default=None, description="Set adapter power state.")
  discoverable: bool | None = Field(default=None, description="Set adapter discoverable state.")
  pairable: bool | None = Field(default=None, description="Set adapter pairable state.")
