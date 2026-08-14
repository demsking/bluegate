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
from fastapi import Request

from bluegate.api.errors import ApiException
from bluegate.bluetooth.agent import PairingAgent
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.bluetooth.manager import BluetoothManager


def get_bluetooth_manager(request: Request) -> BluetoothManager:
  manager = getattr(request.app.state, "bluetooth_manager", None)
  if manager is None:
    raise ApiException(
      code="BLUETOOTH_MANAGER_UNAVAILABLE",
      message="Bluetooth manager is not initialized.",
      status_code=503,
    )

  return manager


def get_event_broker(request: Request) -> BluetoothEventBroker:
  broker = getattr(request.app.state, "event_broker", None)
  if broker is None:
    raise ApiException(
      code="BLUETOOTH_EVENT_BROKER_UNAVAILABLE",
      message="Bluetooth event broker is not initialized.",
      status_code=503,
    )

  return broker


def get_pairing_agent(request: Request) -> PairingAgent:
  agent = getattr(request.app.state, "pairing_agent", None)
  if agent is None:
    raise ApiException(
      code="BLUETOOTH_AGENT_UNAVAILABLE",
      message="Bluetooth pairing agent is not registered with BlueZ.",
      status_code=503,
    )

  return agent
