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
from datetime import datetime
from datetime import UTC
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

PairingRequestKind = Literal[
  "pin_code",
  "passkey_request",
  "passkey_confirm",
  "confirmation",
  "authorization",
  "service_authorization",
]


class PairingRequest(BaseModel):
  model_config = ConfigDict(extra="forbid")

  id: str = Field(..., description="Unique identifier of the pairing request.")
  kind: PairingRequestKind = Field(..., description="Kind of input expected from the user.")
  device_id: str = Field(..., description="Identifier of the device requesting pairing.")
  device_object_path: str = Field(..., description="D-Bus object path of the device.")
  passkey: int | None = Field(default=None, description="Passkey to confirm or display, when applicable.")
  uuid: str | None = Field(default=None, description="Service UUID, when applicable.")
  created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Request creation time in UTC.")


class PinCodeSubmission(BaseModel):
  model_config = ConfigDict(extra="forbid")

  pin_code: str = Field(..., min_length=1, max_length=16, description="PIN code entered by the user.")


class PasskeySubmission(BaseModel):
  model_config = ConfigDict(extra="forbid")

  passkey: int = Field(..., ge=0, le=999_999, description="Six-digit passkey entered by the user.")
