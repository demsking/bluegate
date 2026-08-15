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
import logging
from typing import TypeAlias
from uuid import uuid4

from dbus_next.errors import DBusError
from dbus_next.service import method
from dbus_next.service import ServiceInterface

from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.models.events import PairingRequestEvent
from bluegate.models.events import PairingRequestResolvedEvent
from bluegate.models.pairing import PairingRequest
from bluegate.models.pairing import PairingRequestKind

logger = logging.getLogger(__name__)

AGENT_PATH = "/bluegate/agent"
AGENT_INTERFACE = "org.bluez.Agent1"

# Type aliases used only to satisfy static type checkers for dbus-next
# D-Bus signature annotations ("o", "s", "u", "q").
o: TypeAlias = str
s: TypeAlias = str
u: TypeAlias = int
q: TypeAlias = int

_PairingResult = str | int | bool | None


class PairingAgent(ServiceInterface):
  """BlueZ Agent1 implementation that bridges pairing prompts to the event broker.

  Each BlueZ callback creates a pending `PairingRequest`, publishes it on the
  event broker, and awaits a resolution submitted through the REST API
  (confirm/cancel/pin/passkey). No PIN, passkey, or other pairing secret is
  ever logged.
  """

  def __init__(self, event_broker: BluetoothEventBroker) -> None:
    super().__init__(AGENT_INTERFACE)
    self._event_broker = event_broker
    self._pending: dict[str, asyncio.Future[_PairingResult]] = {}
    self._requests: dict[str, PairingRequest] = {}
    self._last_request_id: str | None = None

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

  def _resolve(self, request_id: str, value: _PairingResult) -> bool:
    future = self._pending.get(request_id)
    if future is None or future.done():
      return False

    future.set_result(value)
    return True

  async def _request(
    self,
    kind: PairingRequestKind,
    object_path: str,
    passkey: int | None = None,
    uuid: str | None = None,
  ) -> _PairingResult:
    request_id = str(uuid4())
    request = PairingRequest(
      id=request_id,
      kind=kind,
      device_id=_device_id_from_path(object_path),
      device_object_path=object_path,
      passkey=passkey,
      uuid=uuid,
    )

    future: asyncio.Future[_PairingResult] = asyncio.get_running_loop().create_future()
    self._pending[request_id] = future
    self._requests[request_id] = request
    self._last_request_id = request_id

    logger.info("Bluetooth pairing request created: kind=%s device_id=%s", kind, request.device_id)
    await self._event_broker.publish(PairingRequestEvent(request=request))

    try:
      return await future
    finally:
      self._pending.pop(request_id, None)
      self._requests.pop(request_id, None)
      if self._last_request_id == request_id:
        self._last_request_id = None

      await self._event_broker.publish(PairingRequestResolvedEvent(request_id=request_id))

  @method()
  async def RequestPinCode(self, device: "o") -> "s":
    return await self._on_request_pin_code(device)

  @method()
  def DisplayPinCode(self, device: "o", pincode: "s") -> None:
    logger.info("BlueZ requested display of a PIN code for device_id=%s", _device_id_from_path(device))

  @method()
  async def RequestPasskey(self, device: "o") -> "u":
    return await self._on_request_passkey(device)

  @method()
  def DisplayPasskey(self, device: "o", passkey: "u", entered: "q") -> None:
    logger.info("BlueZ requested display of a passkey for device_id=%s", _device_id_from_path(device))

  @method()
  async def RequestConfirmation(self, device: "o", passkey: "u") -> None:
    await self._on_request_confirmation(device, passkey)

  @method()
  async def RequestAuthorization(self, device: "o") -> None:
    await self._on_request_authorization(device)

  @method()
  async def AuthorizeService(self, device: "o", uuid: "s") -> None:
    await self._on_authorize_service(device, uuid)

  @method()
  def Cancel(self) -> None:
    logger.info("BlueZ cancelled the pending pairing request")

    if self._last_request_id is not None:
      self._resolve(self._last_request_id, None)

  @method()
  def Release(self) -> None:
    logger.info("BlueZ released the pairing agent")

  async def _on_request_pin_code(self, device: str) -> str:
    result = await self._request("pin_code", device)
    if not result:
      raise DBusError("org.bluez.Error.Rejected", "No PIN code provided")

    return str(result)

  async def _on_request_passkey(self, device: str) -> int:
    result = await self._request("passkey_request", device)
    if result is None:
      raise DBusError("org.bluez.Error.Rejected", "No passkey provided")

    return int(result)

  async def _on_request_confirmation(self, device: str, passkey: int) -> None:
    result = await self._request("passkey_confirm", device, passkey=passkey)
    if not result:
      raise DBusError("org.bluez.Error.Rejected", "Passkey was not confirmed")

  async def _on_request_authorization(self, device: str) -> None:
    result = await self._request("authorization", device)
    if not result:
      raise DBusError("org.bluez.Error.Rejected", "Authorization was not granted")

  async def _on_authorize_service(self, device: str, uuid: str) -> None:
    result = await self._request("service_authorization", device, uuid=uuid)
    if not result:
      raise DBusError("org.bluez.Error.Rejected", "Service was not authorized")


def _device_id_from_path(path: str) -> str:
  leaf = path.rsplit("/", 1)[-1]
  if leaf.startswith("dev_"):
    return leaf.removeprefix("dev_").replace("_", ":")

  return leaf
