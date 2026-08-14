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
from contextlib import aclosing
from types import SimpleNamespace

from bluegate.bluetooth.bus import SystemBusClient
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.bluetooth.manager import BlueZManager
from bluegate.models.adapter import Adapter
from bluegate.models.device import Device


def _make_adapter(adapter_id: str = "hci0") -> Adapter:
  return Adapter(
    id=adapter_id,
    object_path=f"/org/bluez/{adapter_id}",
    name="Adapter",
    alias="Adapter",
    address="AA:BB:CC:DD:EE:FF",
    powered=True,
    discoverable=False,
    pairable=True,
    discovering=False,
    device_count=0,
  )


def _make_device(device_id: str = "11:22:33:44:55:66") -> Device:
  return Device(
    id=device_id,
    object_path="/org/bluez/hci0/dev_11_22_33_44_55_66",
    adapter_id="hci0",
    name="Headset",
    alias="Headset",
    address=device_id,
    address_type="public",
    icon=None,
    device_class=None,
    appearance=None,
    rssi=-50,
    tx_power=None,
    paired=True,
    trusted=True,
    connected=True,
    blocked=False,
    services_resolved=False,
    uuids=[],
  )


def test_handle_interfaces_removed_publishes_device_removed_event() -> None:
  async def _run() -> None:
    broker = BluetoothEventBroker()
    manager = BlueZManager(SystemBusClient(), broker)

    message = SimpleNamespace(body=["/org/bluez/hci0/dev_11_22_33_44_55_66", ["org.bluez.Device1"]])

    async with aclosing(broker.subscribe()) as subscriber:
      queue = await subscriber.__anext__()
      await manager._handle_interfaces_removed(message)
      event = await asyncio.wait_for(queue.get(), timeout=1)

    assert event.type == "device_removed"
    assert event.device_id == "11:22:33:44:55:66"

  asyncio.run(_run())


def test_handle_properties_changed_publishes_device_changed_event(monkeypatch) -> None:
  async def _run() -> None:
    broker = BluetoothEventBroker()
    manager = BlueZManager(SystemBusClient(), broker)

    device = _make_device()

    async def fake_get_device(device_id: str) -> Device | None:
      return device

    monkeypatch.setattr(manager, "get_device", fake_get_device)

    message = SimpleNamespace(path="/org/bluez/hci0/dev_11_22_33_44_55_66")

    async with aclosing(broker.subscribe()) as subscriber:
      queue = await subscriber.__anext__()
      await manager._handle_properties_changed(message)
      event = await asyncio.wait_for(queue.get(), timeout=1)

    assert event.type == "device_changed"
    assert event.device.id == device.id

  asyncio.run(_run())


def test_handle_properties_changed_publishes_adapter_changed_event(monkeypatch) -> None:
  async def _run() -> None:
    broker = BluetoothEventBroker()
    manager = BlueZManager(SystemBusClient(), broker)

    adapter = _make_adapter()

    async def fake_get_adapter(adapter_id: str) -> Adapter | None:
      return adapter

    monkeypatch.setattr(manager, "get_adapter", fake_get_adapter)

    message = SimpleNamespace(path="/org/bluez/hci0")

    async with aclosing(broker.subscribe()) as subscriber:
      queue = await subscriber.__anext__()
      await manager._handle_properties_changed(message)
      event = await asyncio.wait_for(queue.get(), timeout=1)

    assert event.type == "adapter_changed"
    assert event.adapter.id == "hci0"

  asyncio.run(_run())
