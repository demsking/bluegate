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
from datetime import datetime
from datetime import UTC
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from bluegate.models.adapter import Adapter
from bluegate.models.device import Device
from bluegate.models.gatt import GattCharacteristic
from bluegate.models.pairing import PairingRequest


class EventBase(BaseModel):
  model_config = ConfigDict(extra="forbid")

  timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event creation time in UTC.")


class AdapterChangedEvent(EventBase):
  type: Literal["adapter_changed"] = "adapter_changed"
  adapter: Adapter


class DiscoveryStartedEvent(EventBase):
  type: Literal["discovery_started"] = "discovery_started"
  adapter_id: str


class DiscoveryStoppedEvent(EventBase):
  type: Literal["discovery_stopped"] = "discovery_stopped"
  adapter_id: str


class DeviceChangedEvent(EventBase):
  type: Literal["device_changed"] = "device_changed"
  device: Device


class DevicePairedEvent(EventBase):
  type: Literal["device_paired"] = "device_paired"
  device_id: str


class DeviceConnectedEvent(EventBase):
  type: Literal["device_connected"] = "device_connected"
  device_id: str


class DeviceDisconnectedEvent(EventBase):
  type: Literal["device_disconnected"] = "device_disconnected"
  device_id: str


class DeviceRemovedEvent(EventBase):
  type: Literal["device_removed"] = "device_removed"
  device_id: str


class PairingRequestEvent(EventBase):
  type: Literal["pairing_request"] = "pairing_request"
  request: PairingRequest


class PairingRequestResolvedEvent(EventBase):
  type: Literal["pairing_request_resolved"] = "pairing_request_resolved"
  request_id: str


class CharacteristicChangedEvent(EventBase):
  type: Literal["characteristic_changed"] = "characteristic_changed"
  characteristic: GattCharacteristic


BluetoothEvent = (
  AdapterChangedEvent
  | DiscoveryStartedEvent
  | DiscoveryStoppedEvent
  | DeviceChangedEvent
  | DevicePairedEvent
  | DeviceConnectedEvent
  | DeviceDisconnectedEvent
  | DeviceRemovedEvent
  | PairingRequestEvent
  | PairingRequestResolvedEvent
  | CharacteristicChangedEvent
)
