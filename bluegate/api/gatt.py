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
from collections.abc import Awaitable
from collections.abc import Callable
from typing import TypeVar

from dbus_next import DBusError
from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from bluegate.api.dependencies import get_bluetooth_manager
from bluegate.api.dependencies import get_event_broker
from bluegate.api.errors import ApiException
from bluegate.bluetooth.events import BluetoothEventBroker
from bluegate.bluetooth.manager import BluetoothManager
from bluegate.models.events import CharacteristicChangedEvent
from bluegate.models.gatt import GattCharacteristic
from bluegate.models.gatt import GattDescriptor
from bluegate.models.gatt import GattService
from bluegate.models.gatt import GattValueWrite

API_TAG_METADATA = {
  "name": "BLE/GATT Explorer",
  "description": "Explore GATT services, characteristics and descriptors, and interact with their values.",
}

router = APIRouter(prefix="/devices", tags=[API_TAG_METADATA["name"]])

_T = TypeVar("_T")


async def _call_gatt(operation: Callable[[], Awaitable[_T]]) -> _T:
  try:
    return await operation()
  except DBusError as exc:
    raise ApiException(
      code="BLUETOOTH_GATT_OPERATION_FAILED",
      message="The GATT operation failed.",
      status_code=status.HTTP_502_BAD_GATEWAY,
      details={"dbus_error": exc.type, "dbus_message": str(exc)},
    ) from exc


def _service_not_found(device_id: str, service_id: str) -> ApiException:
  return ApiException(
    code="BLUETOOTH_GATT_SERVICE_NOT_FOUND",
    message="The GATT service does not exist.",
    status_code=status.HTTP_404_NOT_FOUND,
    details={"device_id": device_id, "service_id": service_id},
  )


def _characteristic_not_found(device_id: str, service_id: str, characteristic_id: str) -> ApiException:
  return ApiException(
    code="BLUETOOTH_GATT_CHARACTERISTIC_NOT_FOUND",
    message="The GATT characteristic does not exist.",
    status_code=status.HTTP_404_NOT_FOUND,
    details={"device_id": device_id, "service_id": service_id, "characteristic_id": characteristic_id},
  )


def _descriptor_not_found(device_id: str, service_id: str, characteristic_id: str, descriptor_id: str) -> ApiException:
  return ApiException(
    code="BLUETOOTH_GATT_DESCRIPTOR_NOT_FOUND",
    message="The GATT descriptor does not exist.",
    status_code=status.HTTP_404_NOT_FOUND,
    details={
      "device_id": device_id,
      "service_id": service_id,
      "characteristic_id": characteristic_id,
      "descriptor_id": descriptor_id,
    },
  )


@router.get("/{device_id}/services", summary="List GATT services")
async def list_services(device_id: str, manager: BluetoothManager = Depends(get_bluetooth_manager)) -> list[GattService]:
  return await manager.list_services(device_id)


@router.get("/{device_id}/services/{service_id}", summary="Get GATT service")
async def get_service(
  device_id: str, service_id: str, manager: BluetoothManager = Depends(get_bluetooth_manager)
) -> GattService:
  service = await manager.get_service(device_id, service_id)
  if service is None:
    raise _service_not_found(device_id, service_id)

  return service


@router.get(
  "/{device_id}/services/{service_id}/characteristics",
  summary="List GATT characteristics",
)
async def list_characteristics(
  device_id: str, service_id: str, manager: BluetoothManager = Depends(get_bluetooth_manager)
) -> list[GattCharacteristic]:
  return await manager.list_characteristics(device_id, service_id)


@router.get(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}",
  summary="Get GATT characteristic",
)
async def get_characteristic(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
) -> GattCharacteristic:
  characteristic = await manager.get_characteristic(device_id, service_id, characteristic_id)
  if characteristic is None:
    raise _characteristic_not_found(device_id, service_id, characteristic_id)

  return characteristic


@router.post(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/read",
  summary="Read GATT characteristic value",
)
async def read_characteristic(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> GattCharacteristic:
  characteristic = await _call_gatt(lambda: manager.read_characteristic(device_id, service_id, characteristic_id))
  if characteristic is None:
    raise _characteristic_not_found(device_id, service_id, characteristic_id)

  await broker.publish(CharacteristicChangedEvent(characteristic=characteristic))
  return characteristic


@router.post(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/write",
  summary="Write GATT characteristic value",
)
async def write_characteristic(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  body: GattValueWrite,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> GattCharacteristic:
  try:
    value = bytes.fromhex(body.value)
  except ValueError as exc:
    raise ApiException(
      code="BLUETOOTH_GATT_INVALID_VALUE",
      message="The value must be a valid hex-encoded string.",
      status_code=status.HTTP_400_BAD_REQUEST,
      details={"value": body.value},
    ) from exc

  characteristic = await _call_gatt(lambda: manager.write_characteristic(device_id, service_id, characteristic_id, value))
  if characteristic is None:
    raise _characteristic_not_found(device_id, service_id, characteristic_id)

  await broker.publish(CharacteristicChangedEvent(characteristic=characteristic))
  return characteristic


@router.post(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/notify/start",
  summary="Start GATT characteristic notifications",
)
async def start_characteristic_notify(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> GattCharacteristic:
  characteristic = await _call_gatt(lambda: manager.start_notify(device_id, service_id, characteristic_id))
  if characteristic is None:
    raise _characteristic_not_found(device_id, service_id, characteristic_id)

  await broker.publish(CharacteristicChangedEvent(characteristic=characteristic))
  return characteristic


@router.post(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/notify/stop",
  summary="Stop GATT characteristic notifications",
)
async def stop_characteristic_notify(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
  broker: BluetoothEventBroker = Depends(get_event_broker),
) -> GattCharacteristic:
  characteristic = await _call_gatt(lambda: manager.stop_notify(device_id, service_id, characteristic_id))
  if characteristic is None:
    raise _characteristic_not_found(device_id, service_id, characteristic_id)

  await broker.publish(CharacteristicChangedEvent(characteristic=characteristic))
  return characteristic


@router.get(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/descriptors",
  summary="List GATT descriptors",
)
async def list_descriptors(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
) -> list[GattDescriptor]:
  return await manager.list_descriptors(device_id, service_id, characteristic_id)


@router.get(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/descriptors/{descriptor_id}",
  summary="Get GATT descriptor",
)
async def get_descriptor(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  descriptor_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
) -> GattDescriptor:
  descriptor = await manager.get_descriptor(device_id, service_id, characteristic_id, descriptor_id)
  if descriptor is None:
    raise _descriptor_not_found(device_id, service_id, characteristic_id, descriptor_id)

  return descriptor


@router.post(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/descriptors/{descriptor_id}/read",
  summary="Read GATT descriptor value",
)
async def read_descriptor(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  descriptor_id: str,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
) -> GattDescriptor:
  descriptor = await _call_gatt(lambda: manager.read_descriptor(device_id, service_id, characteristic_id, descriptor_id))
  if descriptor is None:
    raise _descriptor_not_found(device_id, service_id, characteristic_id, descriptor_id)

  return descriptor


@router.post(
  "/{device_id}/services/{service_id}/characteristics/{characteristic_id}/descriptors/{descriptor_id}/write",
  summary="Write GATT descriptor value",
)
async def write_descriptor(
  device_id: str,
  service_id: str,
  characteristic_id: str,
  descriptor_id: str,
  body: GattValueWrite,
  manager: BluetoothManager = Depends(get_bluetooth_manager),
) -> GattDescriptor:
  try:
    value = bytes.fromhex(body.value)
  except ValueError as exc:
    raise ApiException(
      code="BLUETOOTH_GATT_INVALID_VALUE",
      message="The value must be a valid hex-encoded string.",
      status_code=status.HTTP_400_BAD_REQUEST,
      details={"value": body.value},
    ) from exc

  descriptor = await _call_gatt(
    lambda: manager.write_descriptor(device_id, service_id, characteristic_id, descriptor_id, value)
  )
  if descriptor is None:
    raise _descriptor_not_found(device_id, service_id, characteristic_id, descriptor_id)

  return descriptor
