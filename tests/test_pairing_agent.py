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

import pytest
from dbus_next.errors import DBusError

from bluegate.bluetooth.agent import PairingAgent
from bluegate.bluetooth.events import BluetoothEventBroker

DEVICE_PATH = "/org/bluez/hci0/dev_11_22_33_44_55_66"


def test_request_confirmation_accepted_resolves_without_error() -> None:
  async def _run() -> None:
    agent = PairingAgent(BluetoothEventBroker())

    async def _accept_flow() -> None:
      await asyncio.sleep(0.01)
      request = agent.list_pending()[0]
      assert request.kind == "passkey_confirm"
      assert request.passkey == 123456
      assert agent.confirm(request.id, True)

    flow = asyncio.create_task(_accept_flow())
    await agent._on_request_confirmation(DEVICE_PATH, 123456)
    await flow

  asyncio.run(_run())


def test_request_confirmation_rejected_raises_dbus_error() -> None:
  async def _run() -> None:
    agent = PairingAgent(BluetoothEventBroker())

    async def _reject_flow() -> None:
      await asyncio.sleep(0.01)
      request = agent.list_pending()[0]
      agent.confirm(request.id, False)

    flow = asyncio.create_task(_reject_flow())
    with pytest.raises(DBusError):
      await agent._on_request_confirmation(DEVICE_PATH, 123456)

    await flow

  asyncio.run(_run())


def test_request_pin_code_returns_submitted_value() -> None:
  async def _run() -> None:
    agent = PairingAgent(BluetoothEventBroker())

    async def _submit_flow() -> None:
      await asyncio.sleep(0.01)
      request = agent.list_pending()[0]
      assert request.kind == "pin_code"
      assert request.device_id == "11:22:33:44:55:66"
      assert agent.submit_pin(request.id, "1234")

    flow = asyncio.create_task(_submit_flow())
    pin = await agent._on_request_pin_code(DEVICE_PATH)
    await flow

    assert pin == "1234"

  asyncio.run(_run())


def test_request_pin_code_without_submission_raises_dbus_error() -> None:
  async def _run() -> None:
    agent = PairingAgent(BluetoothEventBroker())

    async def _cancel_flow() -> None:
      await asyncio.sleep(0.01)
      request = agent.list_pending()[0]
      agent.cancel(request.id)

    flow = asyncio.create_task(_cancel_flow())
    with pytest.raises(DBusError):
      await agent._on_request_pin_code(DEVICE_PATH)

    await flow

  asyncio.run(_run())


def test_request_passkey_allows_zero_value() -> None:
  async def _run() -> None:
    agent = PairingAgent(BluetoothEventBroker())

    async def _submit_flow() -> None:
      await asyncio.sleep(0.01)
      request = agent.list_pending()[0]
      assert request.kind == "passkey_request"
      assert agent.submit_passkey(request.id, 0)

    flow = asyncio.create_task(_submit_flow())
    passkey = await agent._on_request_passkey(DEVICE_PATH)
    await flow

    assert passkey == 0

  asyncio.run(_run())


def test_authorize_service_carries_uuid() -> None:
  async def _run() -> None:
    agent = PairingAgent(BluetoothEventBroker())

    async def _confirm_flow() -> None:
      await asyncio.sleep(0.01)
      request = agent.list_pending()[0]
      assert request.kind == "service_authorization"
      assert request.uuid == "0000110b-0000-1000-8000-00805f9b34fb"
      assert agent.confirm(request.id, True)

    flow = asyncio.create_task(_confirm_flow())
    await agent._on_authorize_service(DEVICE_PATH, "0000110b-0000-1000-8000-00805f9b34fb")
    await flow

  asyncio.run(_run())


def test_cancel_unknown_request_returns_false() -> None:
  agent = PairingAgent(BluetoothEventBroker())
  assert agent.cancel("unknown-request-id") is False


def test_dbus_cancel_rejects_last_pending_request() -> None:
  async def _run() -> None:
    agent = PairingAgent(BluetoothEventBroker())

    async def _bluez_cancel_flow() -> None:
      await asyncio.sleep(0.01)
      agent.Cancel()

    flow = asyncio.create_task(_bluez_cancel_flow())
    with pytest.raises(DBusError):
      await agent._on_request_confirmation(DEVICE_PATH, 111111)

    await flow

  asyncio.run(_run())


def test_pairing_request_events_are_published_and_resolved() -> None:
  async def _run() -> None:
    broker = BluetoothEventBroker()
    agent = PairingAgent(broker)

    async with aclosing(broker.subscribe()) as subscriber:
      queue = await subscriber.__anext__()

      async def _accept_flow() -> None:
        request_event = await asyncio.wait_for(queue.get(), timeout=1)
        assert request_event.type == "pairing_request"
        assert agent.confirm(request_event.request.id, True)

      flow = asyncio.create_task(_accept_flow())
      await agent._on_request_confirmation(DEVICE_PATH, 654321)
      await flow

      resolved_event = await asyncio.wait_for(queue.get(), timeout=1)
      assert resolved_event.type == "pairing_request_resolved"

  asyncio.run(_run())


class _subscribe:
  def __init__(self, broker: BluetoothEventBroker) -> None:
    self._broker = broker
    self._generator = None

  async def __aenter__(self) -> asyncio.Queue:
    self._generator = self._broker.subscribe()
    return await self._generator.__anext__()

  async def __aexit__(self, *_exc_info: object) -> None:
    if self._generator is not None:
      await self._generator.aclose()
