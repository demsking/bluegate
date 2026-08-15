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

from dbus_next.errors import DBusError
from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from bluegate.api.dependencies import get_bluetooth_manager
from bluegate.api.dependencies import get_event_broker
from bluegate.api.errors import ApiException
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.bluetooth.manager import BluetoothManager
from bluegate.models.adapter import Adapter
from bluegate.models.adapter import AdapterPatch
from bluegate.models.events import AdapterChangedEvent
from bluegate.models.events import DiscoveryStartedEvent
from bluegate.models.events import DiscoveryStoppedEvent

API_TAG_METADATA = {
  "name": "Bluetooth Adapters",
  "description": "Manage Bluetooth adapters exposed by BlueZ.",
}

router = APIRouter(prefix="/adapters", tags=[API_TAG_METADATA["name"]])


def _dbus_diagnostics(exc: DBusError) -> dict[str, str | bool]:
  message = str(exc)
  normalized_message = message.lower()

  if exc.type == "org.bluez.Error.InProgress":
    return {
      "reason": "operation_in_progress",
      "retryable": True,
      "hint": "A previous Bluetooth operation is still running; retry after a short delay.",
    }

  if exc.type == "org.bluez.Error.NotReady":
    return {
      "reason": "adapter_not_ready",
      "retryable": True,
      "hint": "The Bluetooth adapter is not ready; verify it is powered and not blocked by rfkill.",
    }

  if exc.type == "org.bluez.Error.NotAvailable":
    return {
      "reason": "adapter_unavailable",
      "retryable": False,
      "hint": "The adapter is unavailable on this host; check controller presence and bluetoothd status.",
    }

  if exc.type == "org.bluez.Error.NotSupported":
    return {
      "reason": "operation_not_supported",
      "retryable": False,
      "hint": "The adapter does not support this operation.",
    }

  if "br-connection-create-socket" in normalized_message:
    return {
      "reason": "socket_creation_failed",
      "retryable": True,
      "hint": "BlueZ failed to create a BR/EDR connection socket on this node; check bluetoothd logs, kernel Bluetooth modules, firmware, and rfkill state.",
    }

  if exc.type == "org.bluez.Error.Failed":
    return {
      "reason": "operation_failed",
      "retryable": False,
      "hint": "BlueZ reported a generic failure; consult bluetoothd journal logs around the same timestamp for root cause.",
    }

  return {
    "reason": "dbus_error",
    "retryable": False,
    "hint": "Unexpected D-Bus error from BlueZ.",
  }


async def _call_discovery(operation: str, adapter_id: str, action: Callable[[], Awaitable[bool]]) -> bool:
  try:
    return await action()
  except DBusError as exc:
    if operation == "start" and exc.type == "org.bluez.Error.InProgress":
      return True

    if operation == "stop" and exc.type == "org.bluez.Error.Failed" and "no discovery started" in str(exc).lower():
      return True

    diagnostics = _dbus_diagnostics(exc)

    raise ApiException(
      code="BLUETOOTH_ADAPTER_SCAN_FAILED",
      message="The Bluetooth discovery operation failed.",
      status_code=status.HTTP_502_BAD_GATEWAY,
      details={
        "adapter_id": adapter_id,
        "operation": operation,
        "dbus_error": exc.type,
        "dbus_message": str(exc),
        "reason": diagnostics["reason"],
        "retryable": diagnostics["retryable"],
        "hint": diagnostics["hint"],
      },
    ) from exc


@router.get("/", summary="List adapters")
async def list_adapters(manager: BluetoothManager = Depends(get_bluetooth_manager)) -> list[Adapter]:
  return await manager.list_adapters()


@router.get("/{adapter_id}", summary="Get adapter")
async def get_adapter(adapter_id: str, manager: BluetoothManager = Depends(get_bluetooth_manager)) -> Adapter:
  adapter = await manager.get_adapter(adapter_id)
  if adapter is None:
    raise ApiException(
      code="BLUETOOTH_ADAPTER_NOT_FOUND",
      message="The Bluetooth adapter does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"adapter_id": adapter_id},
    )

  return adapter


@router.patch("/{adapter_id}", summary="Update adapter")
async def patch_adapter(
  adapter_id: str,
  patch: AdapterPatch,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> Adapter:
  adapter = await manager.patch_adapter(adapter_id, patch)
  if adapter is None:
    raise ApiException(
      code="BLUETOOTH_ADAPTER_NOT_FOUND",
      message="The Bluetooth adapter does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"adapter_id": adapter_id},
    )

  await broker.publish(AdapterChangedEvent(adapter=adapter))
  return adapter


@router.post("/{adapter_id}/scan", summary="Start discovery", status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
  adapter_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  success = await _call_discovery("start", adapter_id, lambda: manager.start_discovery(adapter_id))
  if not success:
    raise ApiException(
      code="BLUETOOTH_ADAPTER_NOT_FOUND",
      message="The Bluetooth adapter does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"adapter_id": adapter_id},
    )

  await broker.publish(DiscoveryStartedEvent(adapter_id=adapter_id))
  return {"started": True}


@router.delete("/{adapter_id}/scan", summary="Stop discovery")
async def stop_scan(
  adapter_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  success = await _call_discovery("stop", adapter_id, lambda: manager.stop_discovery(adapter_id))
  if not success:
    raise ApiException(
      code="BLUETOOTH_ADAPTER_NOT_FOUND",
      message="The Bluetooth adapter does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"adapter_id": adapter_id},
    )

  await broker.publish(DiscoveryStoppedEvent(adapter_id=adapter_id))
  return {"stopped": True}
