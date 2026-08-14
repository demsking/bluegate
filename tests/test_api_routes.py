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
from fastapi.testclient import TestClient

from bluegate.core.app import create_app
from bluegate.core.settings import Settings
from bluegate.models.adapter import Adapter
from bluegate.models.adapter import AdapterPatch
from bluegate.models.device import Device


class FakeBluetoothManager:
  def __init__(self) -> None:
    self.dbus_connected = True
    self.bluez_available = True
    self._adapter = Adapter(
      id="hci0",
      object_path="/org/bluez/hci0",
      name="Adapter",
      alias="Adapter",
      address="AA:BB:CC:DD:EE:FF",
      powered=True,
      discoverable=False,
      pairable=True,
      discovering=False,
      device_count=1,
    )
    self._device = Device(
      id="11:22:33:44:55:66",
      object_path="/org/bluez/hci0/dev_11_22_33_44_55_66",
      adapter_id="hci0",
      name="Headset",
      alias="Headset",
      address="11:22:33:44:55:66",
      address_type="public",
      icon="audio-headset",
      device_class=0,
      appearance=0,
      rssi=-55,
      tx_power=4,
      paired=False,
      trusted=False,
      connected=False,
      blocked=False,
      services_resolved=False,
      uuids=[],
    )

  async def initialize(self) -> None:
    return None

  async def shutdown(self) -> None:
    return None

  async def list_adapters(self) -> list[Adapter]:
    return [self._adapter]

  async def get_adapter(self, adapter_id: str) -> Adapter | None:
    if adapter_id == self._adapter.id:
      return self._adapter

    return None

  async def patch_adapter(self, adapter_id: str, patch: AdapterPatch) -> Adapter | None:
    if adapter_id != self._adapter.id:
      return None

    self._adapter = self._adapter.model_copy(update=patch.model_dump(exclude_none=True))
    return self._adapter

  async def start_discovery(self, adapter_id: str) -> bool:
    return adapter_id == self._adapter.id

  async def stop_discovery(self, adapter_id: str) -> bool:
    return adapter_id == self._adapter.id

  async def list_devices(self) -> list[Device]:
    return [self._device]

  async def get_device(self, device_id: str) -> Device | None:
    if device_id == self._device.id:
      return self._device

    return None

  async def pair_device(self, device_id: str) -> bool:
    return device_id == self._device.id

  async def connect_device(self, device_id: str) -> bool:
    return device_id == self._device.id

  async def disconnect_device(self, device_id: str) -> bool:
    return device_id == self._device.id

  async def trust_device(self, device_id: str, trusted: bool) -> bool:
    if device_id != self._device.id:
      return False

    self._device = self._device.model_copy(update={"trusted": trusted})
    return True

  async def remove_device(self, device_id: str) -> bool:
    return device_id == self._device.id


def test_adapters_and_devices_routes(monkeypatch) -> None:
  fake_manager = FakeBluetoothManager()

  def _factory(*_args: object, **_kwargs: object) -> FakeBluetoothManager:
    return fake_manager

  monkeypatch.setattr("bluegate.core.app.create_bluetooth_manager", _factory)

  app = create_app(Settings())

  with TestClient(app) as client:
    adapters_response = client.get("/api/adapters/")
    assert adapters_response.status_code == 200
    assert adapters_response.json()[0]["id"] == "hci0"

    patch_response = client.patch("/api/adapters/hci0", json={"powered": False})
    assert patch_response.status_code == 200
    assert patch_response.json()["powered"] is False

    scan_response = client.post("/api/adapters/hci0/scan")
    assert scan_response.status_code == 202

    devices_response = client.get("/api/devices/")
    assert devices_response.status_code == 200
    assert devices_response.json()[0]["id"] == "11:22:33:44:55:66"

    trust_response = client.post("/api/devices/11:22:33:44:55:66/trust")
    assert trust_response.status_code == 202
    assert trust_response.json()["trusted"] is True


def test_not_found_errors_are_structured(monkeypatch) -> None:
  fake_manager = FakeBluetoothManager()

  def _factory(*_args: object, **_kwargs: object) -> FakeBluetoothManager:
    return fake_manager

  monkeypatch.setattr("bluegate.core.app.create_bluetooth_manager", _factory)

  app = create_app(Settings())

  with TestClient(app) as client:
    response = client.get("/api/adapters/hci9")

  assert response.status_code == 404
  payload = response.json()
  assert payload["code"] == "BLUETOOTH_ADAPTER_NOT_FOUND"
  assert "message" in payload
  assert "details" in payload


def test_websocket_receives_device_change_event(monkeypatch) -> None:
  fake_manager = FakeBluetoothManager()

  def _factory(*_args: object, **_kwargs: object) -> FakeBluetoothManager:
    return fake_manager

  monkeypatch.setattr("bluegate.core.app.create_bluetooth_manager", _factory)

  app = create_app(Settings())

  with TestClient(app) as client:
    with client.websocket_connect("/api/ws/") as websocket:
      response = client.post("/api/devices/11:22:33:44:55:66/trust")
      assert response.status_code == 202

      event = websocket.receive_json()
      assert event["type"] == "device_changed"
      assert event["device"]["id"] == "11:22:33:44:55:66"
      assert event["device"]["trusted"] is True
