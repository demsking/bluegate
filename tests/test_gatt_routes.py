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
from dbus_next.errors import DBusError
from fastapi.testclient import TestClient

from bluegate.core.app import create_app
from bluegate.core.settings import Settings
from bluegate.models.gatt import GattCharacteristic
from bluegate.models.gatt import GattDescriptor
from bluegate.models.gatt import GattService

SERVICE = GattService(
  id="service0006",
  object_path="/org/bluez/hci0/dev_11_22_33_44_55_66/service0006",
  device_id="11:22:33:44:55:66",
  uuid="0000180d-0000-1000-8000-00805f9b34fb",
  primary=True,
)

CHARACTERISTIC = GattCharacteristic(
  id="char0008",
  object_path="/org/bluez/hci0/dev_11_22_33_44_55_66/service0006/char0008",
  device_id="11:22:33:44:55:66",
  service_id="service0006",
  uuid="00002a37-0000-1000-8000-00805f9b34fb",
  flags=["read", "notify"],
  notifying=False,
  value="0102",
)

DESCRIPTOR = GattDescriptor(
  id="desc000a",
  object_path="/org/bluez/hci0/dev_11_22_33_44_55_66/service0006/char0008/desc000a",
  device_id="11:22:33:44:55:66",
  service_id="service0006",
  characteristic_id="char0008",
  uuid="00002902-0000-1000-8000-00805f9b34fb",
  flags=["read", "write"],
  value="0000",
)


class FakeGattBluetoothManager:
  def __init__(self) -> None:
    self.dbus_connected = True
    self.bluez_available = True
    self.written_value: bytes | None = None
    self.fail_dbus_error = False

  async def initialize(self) -> None:
    return None

  async def shutdown(self) -> None:
    return None

  async def list_services(self, device_id: str) -> list[GattService]:
    return [SERVICE] if device_id == SERVICE.device_id else []

  async def get_service(self, device_id: str, service_id: str) -> GattService | None:
    if device_id == SERVICE.device_id and service_id == SERVICE.id:
      return SERVICE

    return None

  async def list_characteristics(self, device_id: str, service_id: str) -> list[GattCharacteristic]:
    if device_id == SERVICE.device_id and service_id == SERVICE.id:
      return [CHARACTERISTIC]

    return []

  async def get_characteristic(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    if (device_id, service_id, characteristic_id) == (SERVICE.device_id, SERVICE.id, CHARACTERISTIC.id):
      return CHARACTERISTIC

    return None

  async def read_characteristic(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    if self.fail_dbus_error:
      raise DBusError("org.bluez.Error.Failed", "read failed")

    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def write_characteristic(
    self, device_id: str, service_id: str, characteristic_id: str, value: bytes
  ) -> GattCharacteristic | None:
    if self.fail_dbus_error:
      raise DBusError("org.bluez.Error.Failed", "write failed")

    self.written_value = value
    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def start_notify(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def stop_notify(self, device_id: str, service_id: str, characteristic_id: str) -> GattCharacteristic | None:
    return await self.get_characteristic(device_id, service_id, characteristic_id)

  async def list_descriptors(self, device_id: str, service_id: str, characteristic_id: str) -> list[GattDescriptor]:
    if (device_id, service_id, characteristic_id) == (SERVICE.device_id, SERVICE.id, CHARACTERISTIC.id):
      return [DESCRIPTOR]

    return []

  async def get_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str
  ) -> GattDescriptor | None:
    if (device_id, service_id, characteristic_id, descriptor_id) == (
      SERVICE.device_id,
      SERVICE.id,
      CHARACTERISTIC.id,
      DESCRIPTOR.id,
    ):
      return DESCRIPTOR

    return None

  async def read_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str
  ) -> GattDescriptor | None:
    return await self.get_descriptor(device_id, service_id, characteristic_id, descriptor_id)

  async def write_descriptor(
    self, device_id: str, service_id: str, characteristic_id: str, descriptor_id: str, value: bytes
  ) -> GattDescriptor | None:
    self.written_value = value
    return await self.get_descriptor(device_id, service_id, characteristic_id, descriptor_id)


def _create_client(monkeypatch, manager: FakeGattBluetoothManager) -> TestClient:
  def _factory(*_args: object, **_kwargs: object) -> FakeGattBluetoothManager:
    return manager

  monkeypatch.setattr("bluegate.core.app.create_bluetooth_manager", _factory)
  app = create_app(Settings())
  return TestClient(app)


def test_list_and_get_services(monkeypatch) -> None:
  with _create_client(monkeypatch, FakeGattBluetoothManager()) as client:
    list_response = client.get("/api/devices/11:22:33:44:55:66/services")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == "service0006"

    get_response = client.get("/api/devices/11:22:33:44:55:66/services/service0006")
    assert get_response.status_code == 200
    assert get_response.json()["uuid"] == SERVICE.uuid

    missing_response = client.get("/api/devices/11:22:33:44:55:66/services/unknown")
    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == "BLUETOOTH_GATT_SERVICE_NOT_FOUND"


def test_list_and_get_characteristics(monkeypatch) -> None:
  with _create_client(monkeypatch, FakeGattBluetoothManager()) as client:
    list_response = client.get("/api/devices/11:22:33:44:55:66/services/service0006/characteristics")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == "char0008"

    get_response = client.get("/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008")
    assert get_response.status_code == 200
    assert get_response.json()["value"] == "0102"

    missing_response = client.get("/api/devices/11:22:33:44:55:66/services/service0006/characteristics/unknown")
    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == "BLUETOOTH_GATT_CHARACTERISTIC_NOT_FOUND"


def test_read_and_write_characteristic(monkeypatch) -> None:
  manager = FakeGattBluetoothManager()
  with _create_client(monkeypatch, manager) as client:
    read_response = client.post("/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/read")
    assert read_response.status_code == 200
    assert read_response.json()["value"] == "0102"

    write_response = client.post(
      "/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/write",
      json={"value": "0a0b"},
    )
    assert write_response.status_code == 200
    assert manager.written_value == bytes([0x0A, 0x0B])

    invalid_response = client.post(
      "/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/write",
      json={"value": "not-hex"},
    )
    assert invalid_response.status_code == 400
    assert invalid_response.json()["code"] == "BLUETOOTH_GATT_INVALID_VALUE"


def test_dbus_error_is_translated_to_502(monkeypatch) -> None:
  manager = FakeGattBluetoothManager()
  manager.fail_dbus_error = True

  with _create_client(monkeypatch, manager) as client:
    response = client.post("/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/read")

  assert response.status_code == 502
  assert response.json()["code"] == "BLUETOOTH_GATT_OPERATION_FAILED"


def test_notify_start_and_stop(monkeypatch) -> None:
  with _create_client(monkeypatch, FakeGattBluetoothManager()) as client:
    start_response = client.post("/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/notify/start")
    assert start_response.status_code == 200

    stop_response = client.post("/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/notify/stop")
    assert stop_response.status_code == 200


def test_list_and_read_write_descriptors(monkeypatch) -> None:
  manager = FakeGattBluetoothManager()
  with _create_client(monkeypatch, manager) as client:
    list_response = client.get("/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/descriptors")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == "desc000a"

    get_response = client.get(
      "/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/descriptors/desc000a"
    )
    assert get_response.status_code == 200

    read_response = client.post(
      "/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/descriptors/desc000a/read"
    )
    assert read_response.status_code == 200

    write_response = client.post(
      "/api/devices/11:22:33:44:55:66/services/service0006/characteristics/char0008/descriptors/desc000a/write",
      json={"value": "ff"},
    )
    assert write_response.status_code == 200
    assert manager.written_value == bytes([0xFF])
