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
from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from bluegate.api.dependencies import get_bluetooth_manager
from bluegate.api.dependencies import get_event_broker
from bluegate.api.errors import ApiException
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.bluetooth.manager import BluetoothManager
from bluegate.models.device import Device
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


@router.post("/{device_id}/pair", summary="Pair device", status_code=status.HTTP_202_ACCEPTED)
async def pair_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await manager.pair_device(device_id):
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


@router.post("/{device_id}/connect", summary="Connect device", status_code=status.HTTP_202_ACCEPTED)
async def connect_device(
  device_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> dict[str, bool]:
  if not await manager.connect_device(device_id):
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
  if not await manager.disconnect_device(device_id):
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
  if not await manager.trust_device(device_id, trusted=True):
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
  if not await manager.trust_device(device_id, trusted=False):
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
  if not await manager.remove_device(device_id):
    raise ApiException(
      code="BLUETOOTH_DEVICE_NOT_FOUND",
      message="The Bluetooth device does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"device_id": device_id},
    )

  await broker.publish(DeviceRemovedEvent(device_id=device_id))
  return {"removed": True}
