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
  success = await manager.start_discovery(adapter_id)
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
  success = await manager.stop_discovery(adapter_id)
  if not success:
    raise ApiException(
      code="BLUETOOTH_ADAPTER_NOT_FOUND",
      message="The Bluetooth adapter does not exist.",
      status_code=status.HTTP_404_NOT_FOUND,
      details={"adapter_id": adapter_id},
    )

  await broker.publish(DiscoveryStoppedEvent(adapter_id=adapter_id))
  return {"stopped": True}
