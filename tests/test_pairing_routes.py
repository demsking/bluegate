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
from fastapi.testclient import TestClient

from bluegate.core.app import create_app
from bluegate.core.settings import Settings
from bluegate.models.pairing import PairingRequest


class FakePairingAgent:
  def __init__(self) -> None:
    self._requests: dict[str, PairingRequest] = {
      "req-1": PairingRequest(
        id="req-1",
        kind="passkey_confirm",
        device_id="11:22:33:44:55:66",
        device_object_path="/org/bluez/hci0/dev_11_22_33_44_55_66",
        passkey=123456,
      ),
    }
    self.resolved: dict[str, object] = {}

  def list_pending(self) -> list[PairingRequest]:
    return list(self._requests.values())

  def get_request(self, request_id: str) -> PairingRequest | None:
    return self._requests.get(request_id)

  def confirm(self, request_id: str, accept: bool) -> bool:
    return self._resolve(request_id, accept)

  def cancel(self, request_id: str) -> bool:
    return self._resolve(request_id, None)

  def submit_pin(self, request_id: str, pin_code: str) -> bool:
    return self._resolve(request_id, pin_code)

  def submit_passkey(self, request_id: str, passkey: int) -> bool:
    return self._resolve(request_id, passkey)

  def _resolve(self, request_id: str, value: object) -> bool:
    if request_id not in self._requests:
      return False

    self.resolved[request_id] = value
    del self._requests[request_id]
    return True


class FakeBluetoothManagerWithAgent:
  def __init__(self) -> None:
    self.dbus_connected = True
    self.bluez_available = True
    self.pairing_agent = FakePairingAgent()

  async def initialize(self) -> None:
    return None

  async def shutdown(self) -> None:
    return None


class FakeBluetoothManagerWithoutAgent:
  def __init__(self) -> None:
    self.dbus_connected = True
    self.bluez_available = False
    self.pairing_agent = None

  async def initialize(self) -> None:
    return None

  async def shutdown(self) -> None:
    return None


def test_list_get_and_confirm_pairing_request(monkeypatch) -> None:
  def _factory(*_args: object, **_kwargs: object) -> FakeBluetoothManagerWithAgent:
    return FakeBluetoothManagerWithAgent()

  monkeypatch.setattr("bluegate.core.app.create_bluetooth_manager", _factory)
  app = create_app(Settings())

  with TestClient(app) as client:
    list_response = client.get("/api/pairing/")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == "req-1"

    get_response = client.get("/api/pairing/req-1")
    assert get_response.status_code == 200
    assert get_response.json()["passkey"] == 123456

    confirm_response = client.post("/api/pairing/req-1/confirm")
    assert confirm_response.status_code == 202
    assert confirm_response.json() == {"confirmed": True}

    missing_response = client.get("/api/pairing/req-1")
    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == "PAIRING_REQUEST_NOT_FOUND"


def test_cancel_pin_and_passkey_submission_routes(monkeypatch) -> None:
  def _factory(*_args: object, **_kwargs: object) -> FakeBluetoothManagerWithAgent:
    return FakeBluetoothManagerWithAgent()

  monkeypatch.setattr("bluegate.core.app.create_bluetooth_manager", _factory)
  app = create_app(Settings())

  with TestClient(app) as client:
    cancel_response = client.post("/api/pairing/req-1/cancel")
    assert cancel_response.status_code == 202

    pin_response = client.post("/api/pairing/unknown/pin", json={"pin_code": "1234"})
    assert pin_response.status_code == 404

    passkey_response = client.post("/api/pairing/unknown/passkey", json={"passkey": 654321})
    assert passkey_response.status_code == 404


def test_pairing_routes_return_503_when_agent_unavailable(monkeypatch) -> None:
  def _factory(*_args: object, **_kwargs: object) -> FakeBluetoothManagerWithoutAgent:
    return FakeBluetoothManagerWithoutAgent()

  monkeypatch.setattr("bluegate.core.app.create_bluetooth_manager", _factory)
  app = create_app(Settings())

  with TestClient(app) as client:
    response = client.get("/api/pairing/")

  assert response.status_code == 503
  assert response.json()["code"] == "BLUETOOTH_AGENT_UNAVAILABLE"
