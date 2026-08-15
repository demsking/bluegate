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
import asyncio
from contextlib import aclosing

from dbus_next import DBusError
from dbus_next.signature import Variant

from bluegate.bluetooth.bus import SystemBusClient
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.bluetooth.manager import BlueZManager
from bluegate.models.device import Device

DEVICE_PATH = "/org/bluez/hci0/dev_11_22_33_44_55_66"
SERVICE_PATH = f"{DEVICE_PATH}/service0006"
CHARACTERISTIC_PATH = f"{SERVICE_PATH}/char0008"
DESCRIPTOR_PATH = f"{CHARACTERISTIC_PATH}/desc000a"


def _make_device() -> Device:
  return Device(
    id="11:22:33:44:55:66",
    object_path=DEVICE_PATH,
    adapter_id="hci0",
    name="Heart Rate Monitor",
    alias="Heart Rate Monitor",
    address="11:22:33:44:55:66",
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
    services_resolved=True,
    uuids=[],
  )


def _managed_objects() -> dict[str, dict[str, dict[str, Variant]]]:
  return {
    SERVICE_PATH: {
      "org.bluez.GattService1": {
        "UUID": Variant("s", "0000180d-0000-1000-8000-00805f9b34fb"),
        "Primary": Variant("b", True),
      },
    },
    CHARACTERISTIC_PATH: {
      "org.bluez.GattCharacteristic1": {
        "UUID": Variant("s", "00002a37-0000-1000-8000-00805f9b34fb"),
        "Flags": Variant("as", ["read", "notify"]),
        "Notifying": Variant("b", False),
        "Value": Variant("ay", b"\x01\x02"),
      },
    },
    DESCRIPTOR_PATH: {
      "org.bluez.GattDescriptor1": {
        "UUID": Variant("s", "00002902-0000-1000-8000-00805f9b34fb"),
        "Flags": Variant("as", ["read", "write"]),
        "Value": Variant("ay", b"\x00\x00"),
      },
    },
  }


class _FakeInterface:
  def __init__(self) -> None:
    self.read_calls = 0
    self.write_calls: list[tuple[list[int], dict]] = []
    self.start_notify_calls = 0
    self.stop_notify_calls = 0

  async def call_read_value(self, options: dict) -> list[int]:
    self.read_calls += 1
    return []

  async def call_write_value(self, value: list[int], options: dict) -> None:
    self.write_calls.append((value, options))

  async def call_start_notify(self) -> None:
    self.start_notify_calls += 1

  async def call_stop_notify(self) -> None:
    self.stop_notify_calls += 1


def _make_manager(monkeypatch, broker: BluetoothEventBroker | None = None) -> BlueZManager:
  manager = BlueZManager(SystemBusClient(), broker)

  async def fake_get_managed_objects() -> dict[str, dict[str, dict[str, Variant]]]:
    return _managed_objects()

  async def fake_get_device(device_id: str) -> Device | None:
    device = _make_device()
    return device if device_id == device.id else None

  monkeypatch.setattr(manager, "_get_managed_objects", fake_get_managed_objects)
  monkeypatch.setattr(manager, "get_device", fake_get_device)

  return manager


def test_list_services_returns_services_under_device(monkeypatch) -> None:
  async def _run() -> None:
    manager = _make_manager(monkeypatch)

    services = await manager.list_services("11:22:33:44:55:66")

    assert len(services) == 1
    assert services[0].id == "service0006"
    assert services[0].uuid == "0000180d-0000-1000-8000-00805f9b34fb"
    assert services[0].primary is True

  asyncio.run(_run())


def test_list_characteristics_returns_characteristics_under_service(monkeypatch) -> None:
  async def _run() -> None:
    manager = _make_manager(monkeypatch)

    characteristics = await manager.list_characteristics("11:22:33:44:55:66", "service0006")

    assert len(characteristics) == 1
    characteristic = characteristics[0]
    assert characteristic.id == "char0008"
    assert characteristic.uuid == "00002a37-0000-1000-8000-00805f9b34fb"
    assert characteristic.flags == ["read", "notify"]
    assert characteristic.notifying is False
    assert characteristic.value == "0102"

  asyncio.run(_run())


def test_list_descriptors_returns_descriptors_under_characteristic(monkeypatch) -> None:
  async def _run() -> None:
    manager = _make_manager(monkeypatch)

    descriptors = await manager.list_descriptors("11:22:33:44:55:66", "service0006", "char0008")

    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor.id == "desc000a"
    assert descriptor.uuid == "00002902-0000-1000-8000-00805f9b34fb"
    assert descriptor.value == "0000"

  asyncio.run(_run())


def test_unknown_service_returns_empty_lists(monkeypatch) -> None:
  async def _run() -> None:
    manager = _make_manager(monkeypatch)

    assert await manager.get_service("11:22:33:44:55:66", "service9999") is None
    assert await manager.list_characteristics("11:22:33:44:55:66", "service9999") == []

  asyncio.run(_run())


def test_list_adapters_returns_empty_when_bluez_is_missing(monkeypatch) -> None:
  async def _run() -> None:
    manager = BlueZManager(SystemBusClient())
    manager._bluez_available = True

    async def fake_get_managed_objects() -> dict[str, dict[str, dict[str, Variant]]]:
      raise DBusError(
        "org.freedesktop.DBus.Error.ServiceUnknown",
        "The name org.bluez was not provided by any .service files",
      )

    monkeypatch.setattr(manager, "_get_managed_objects", fake_get_managed_objects)

    assert await manager.list_adapters() == []
    assert manager.bluez_available is False

  asyncio.run(_run())


def test_read_characteristic_invokes_dbus_and_refreshes_value(monkeypatch) -> None:
  async def _run() -> None:
    manager = _make_manager(monkeypatch)
    fake_interface = _FakeInterface()

    async def fake_get_interface(path: str, interface_name: str) -> _FakeInterface:
      assert path == CHARACTERISTIC_PATH
      assert interface_name == "org.bluez.GattCharacteristic1"
      return fake_interface

    monkeypatch.setattr(manager, "_get_interface", fake_get_interface)

    characteristic = await manager.read_characteristic("11:22:33:44:55:66", "service0006", "char0008")

    assert fake_interface.read_calls == 1
    assert characteristic is not None
    assert characteristic.value == "0102"

  asyncio.run(_run())


def test_write_characteristic_sends_bytes_to_dbus(monkeypatch) -> None:
  async def _run() -> None:
    manager = _make_manager(monkeypatch)
    fake_interface = _FakeInterface()

    async def fake_get_interface(path: str, interface_name: str) -> _FakeInterface:
      return fake_interface

    monkeypatch.setattr(manager, "_get_interface", fake_get_interface)

    characteristic = await manager.write_characteristic("11:22:33:44:55:66", "service0006", "char0008", bytes([0x0A, 0x0B]))

    assert fake_interface.write_calls == [([0x0A, 0x0B], {})]
    assert characteristic is not None

  asyncio.run(_run())


def test_start_and_stop_notify_call_dbus_methods(monkeypatch) -> None:
  async def _run() -> None:
    manager = _make_manager(monkeypatch)
    fake_interface = _FakeInterface()

    async def fake_get_interface(path: str, interface_name: str) -> _FakeInterface:
      return fake_interface

    monkeypatch.setattr(manager, "_get_interface", fake_get_interface)

    await manager.start_notify("11:22:33:44:55:66", "service0006", "char0008")
    await manager.stop_notify("11:22:33:44:55:66", "service0006", "char0008")

    assert fake_interface.start_notify_calls == 1
    assert fake_interface.stop_notify_calls == 1

  asyncio.run(_run())


def test_handle_properties_changed_publishes_characteristic_changed_event(monkeypatch) -> None:
  async def _run() -> None:
    broker = BluetoothEventBroker()
    manager = _make_manager(monkeypatch, broker)

    async with aclosing(broker.subscribe()) as subscriber:
      queue = await subscriber.__anext__()
      await manager._handle_characteristic_properties_changed(CHARACTERISTIC_PATH)
      event = await asyncio.wait_for(queue.get(), timeout=1)

    assert event.type == "characteristic_changed"
    assert event.characteristic.id == "char0008"

  asyncio.run(_run())
