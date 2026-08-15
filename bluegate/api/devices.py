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
from bluegate.models.device import Device
from bluegate.models.device import DevicePatch
from bluegate.models.events import DeviceChangedEvent
from bluegate.models.events import DeviceConnectedEvent
from bluegate.models.events import DeviceDisconnectedEvent
from bluegate.models.events import DevicePairedEvent
from bluegate.models.events import DeviceRemovedEvent

API_TAG_METADATA = {
  "name": "Bluetooth Devices",
  "description": "Discover and manage Bluetooth devices exposed by BlueZ.",
}

router = APIRouter(prefix="/devices", tags=[API_TAG_METADATA["name"]])


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
      "hint": "The device or adapter does not support this operation.",
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


async def _call_device_action(action: str, device_id: str, operation: Callable[[], Awaitable[bool]]) -> bool:
  try:
    return await operation()
  except DBusError as exc:
    diagnostics = _dbus_diagnostics(exc)
    raise ApiException(
      code="BLUETOOTH_DEVICE_OPERATION_FAILED",
      message="The Bluetooth device operation failed.",
      status_code=status.HTTP_502_BAD_GATEWAY,
      details={
        "device_id": device_id,
        "action": action,
        "dbus_error": exc.type,
        "dbus_message": str(exc),
        "reason": diagnostics["reason"],
        "retryable": diagnostics["retryable"],
        "hint": diagnostics["hint"],
      },
    ) from exc


@router.get("/", summary="List devices")
async def list_devices(manager: BluetoothManager = Depends(get_bluetooth_manager)) -> list[Device]:
  return await manager.list_devices()


@router.get("/{device_id}", summary="Get device")
async def get_device(device_id: str, manager: BluetoothManager = Depends(get_bluetooth_manager)) -> Device:
  device = await manager.get_device(device_id)
  if device is None:
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  return device


@router.patch("/{device_id}", summary="Update device")
async def patch_device(
  device_id: str,
  patch: DevicePatch,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> Device:
  device = await manager.patch_device(device_id, patch)
  if device is None:
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  await broker.publish(DeviceChangedEvent(device=device))
  return device


@router.post("/{device_id}/pair", summary="Pair device", status_code=status.HTTP_202_ACCEPTED)
async def pair_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await _call_device_action("pair", device_id, lambda: manager.pair_device(device_id)):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  await broker.publish(DevicePairedEvent(device_id=device_id))
  device = await manager.get_device(device_id)
  if device is not None:
    await broker.publish(DeviceChangedEvent(device=device))

  return {"paired": True}


@router.post("/{device_id}/unpair", summary="Unpair device", status_code=status.HTTP_202_ACCEPTED)
async def unpair_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await _call_device_action("unpair", device_id, lambda: manager.unpair_device(device_id)):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  await broker.publish(DeviceRemovedEvent(device_id=device_id))
  return {"unpaired": True}


@router.post("/{device_id}/connect", summary="Connect device", status_code=status.HTTP_202_ACCEPTED)
async def connect_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await _call_device_action("connect", device_id, lambda: manager.connect_device(device_id)):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  await broker.publish(DeviceConnectedEvent(device_id=device_id))
  device = await manager.get_device(device_id)
  if device is not None:
    await broker.publish(DeviceChangedEvent(device=device))

  return {"connected": True}


@router.post("/{device_id}/disconnect", summary="Disconnect device", status_code=status.HTTP_202_ACCEPTED)
async def disconnect_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await _call_device_action("disconnect", device_id, lambda: manager.disconnect_device(device_id)):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  await broker.publish(DeviceDisconnectedEvent(device_id=device_id))
  device = await manager.get_device(device_id)
  if device is not None:
    await broker.publish(DeviceChangedEvent(device=device))

  return {"disconnected": True}


@router.post("/{device_id}/trust", summary="Trust device", status_code=status.HTTP_202_ACCEPTED)
async def trust_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await _call_device_action("trust", device_id, lambda: manager.trust_device(device_id, trusted=True)):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  device = await manager.get_device(device_id)
  if device is not None:
    await broker.publish(DeviceChangedEvent(device=device))

  return {"trusted": True}


@router.post("/{device_id}/untrust", summary="Untrust device", status_code=status.HTTP_202_ACCEPTED)
async def untrust_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await _call_device_action("untrust", device_id, lambda: manager.trust_device(device_id, trusted=False)):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  device = await manager.get_device(device_id)
  if device is not None:
    await broker.publish(DeviceChangedEvent(device=device))

  return {"trusted": False}


@router.delete("/{device_id}", summary="Remove device")
async def remove_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await _call_device_action("remove", device_id, lambda: manager.remove_device(device_id)):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  await broker.publish(DeviceRemovedEvent(device_id=device_id))
  return {"removed": True}
