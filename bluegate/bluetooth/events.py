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
import asyncio
from collections.abc import AsyncIterator

from bluegate.models.events import BluetoothEvent


class BluetoothEventBroker:
  def __init__(self) -> None:
    self._subscribers: set[asyncio.Queue[BluetoothEvent]] = set()

  async def publish(self, event: BluetoothEvent) -> None:
    for subscriber in list(self._subscribers):
      await subscriber.put(event)

  async def subscribe(self) -> AsyncIterator[asyncio.Queue[BluetoothEvent]]:
    queue: asyncio.Queue[BluetoothEvent] = asyncio.Queue()
    self._subscribers.add(queue)

    try:
      yield queue
    finally:
      self._subscribers.discard(queue)
