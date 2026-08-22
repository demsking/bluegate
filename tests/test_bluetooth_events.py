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

from dbus_next.signature import Variant

from bluegate.bluetooth.bus import SystemBusClient
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.bluetooth.manager import BlueZManager
from bluegate.bluetooth.manager import MANUAL_DISCONNECT_SUPPRESSION_SECONDS
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
    battery_level=92,
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


def test_list_devices_reads_battery_level_from_battery_interface(monkeypatch) -> None:
  async def _run() -> None:
    manager = BlueZManager(SystemBusClient(), BluetoothEventBroker())

    async def fake_get_managed_objects() -> dict[str, dict[str, dict[str, Variant]]]:
      return {
        "/org/bluez/hci0/dev_11_22_33_44_55_66": {
          "org.bluez.Device1": {
            "Adapter": Variant("o", "/org/bluez/hci0"),
            "Address": Variant("s", "11:22:33:44:55:66"),
            "Name": Variant("s", "Headset"),
            "Alias": Variant("s", "Headset"),
            "AddressType": Variant("s", "public"),
            "Paired": Variant("b", True),
            "Trusted": Variant("b", True),
            "Connected": Variant("b", True),
            "Blocked": Variant("b", False),
            "ServicesResolved": Variant("b", False),
            "UUIDs": Variant("as", []),
          },
          "org.bluez.Battery1": {
            "Percentage": Variant("y", 92),
          },
        }
      }

    monkeypatch.setattr(manager, "_get_managed_objects", fake_get_managed_objects)

    devices = await manager.list_devices()

    assert len(devices) == 1
    assert devices[0].battery_level == 92

  asyncio.run(_run())


def test_handle_properties_changed_auto_connects_trusted_paired_device(monkeypatch) -> None:
  async def _run() -> None:
    broker = BluetoothEventBroker()
    manager = BlueZManager(SystemBusClient(), broker)

    device = _make_device().model_copy(update={"connected": False, "paired": True, "trusted": True})
    connect_calls: list[str] = []

    class FakeDeviceInterface:
      async def call_connect(self) -> None:
        connect_calls.append(device.id)

    async def fake_get_device(device_id: str) -> Device | None:
      if device_id == device.id:
        return device
      return None

    async def fake_get_device_interface(_path: str) -> FakeDeviceInterface:
      return FakeDeviceInterface()

    monkeypatch.setattr(manager, "get_device", fake_get_device)
    monkeypatch.setattr(manager, "_get_device_interface", fake_get_device_interface)

    message = SimpleNamespace(path=device.object_path)

    await manager._handle_properties_changed(message)

    assert connect_calls == [device.id]

  asyncio.run(_run())


def test_disconnect_temporarily_suppresses_auto_connect(monkeypatch) -> None:
  async def _run() -> None:
    manager = BlueZManager(SystemBusClient(), BluetoothEventBroker())
    device = _make_device().model_copy(update={"connected": True, "paired": True, "trusted": True})
    connect_calls: list[str] = []

    class FakeDeviceInterface:
      async def call_disconnect(self) -> None:
        return None

      async def call_connect(self) -> None:
        connect_calls.append(device.id)

    async def fake_get_device(device_id: str) -> Device | None:
      if device_id != device.id:
        return None
      return device

    async def fake_get_device_interface(_path: str) -> FakeDeviceInterface:
      return FakeDeviceInterface()

    monkeypatch.setattr(manager, "get_device", fake_get_device)
    monkeypatch.setattr(manager, "_get_device_interface", fake_get_device_interface)

    disconnected = await manager.disconnect_device(device.id)
    assert disconnected is True

    device.connected = False
    await manager._maybe_auto_connect_device(device.id)
    assert connect_calls == []

    manager._auto_connect_suppressed_until[device.id] = 0.0
    await manager._maybe_auto_connect_device(device.id)
    assert connect_calls == [device.id]

    assert MANUAL_DISCONNECT_SUPPRESSION_SECONDS > 0

  asyncio.run(_run())
