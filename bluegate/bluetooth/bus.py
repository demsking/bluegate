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
from collections.abc import Awaitable
from collections.abc import Callable

from dbus_next import BusType
from dbus_next.aio import MessageBus


class SystemBusClient:
  def __init__(self, bus_address: str | None = None) -> None:
    self._bus_address = bus_address
    self._bus: MessageBus | None = None

  async def connect(self) -> MessageBus:
    if self._bus is not None:
      return self._bus

    bus = MessageBus(bus_type=BusType.SYSTEM, bus_address=self._bus_address)
    self._bus = await bus.connect()

    return self._bus

  async def disconnect(self) -> None:
    if self._bus is None:
      return

    self._bus.disconnect()
    self._bus = None

  @property
  def connected(self) -> bool:
    return self._bus is not None


BusConnector = Callable[[], Awaitable[MessageBus]]
