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
import asyncio

from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from bluegate.api.dependencies import get_event_broker

API_TAG_METADATA = {
  "name": "Bluetooth Events",
  "description": "Receive Bluetooth events over WebSocket.",
}

router = APIRouter(prefix="/ws", tags=[API_TAG_METADATA["name"]])


@router.websocket("/")
async def websocket_events(websocket: WebSocket) -> None:
  await websocket.accept()

  broker = get_event_broker(websocket)
  heartbeat = int(getattr(websocket.app.state, "websocket_heartbeat", 30))

  try:
    async for queue in broker.subscribe():
      while True:
        try:
          event = await asyncio.wait_for(queue.get(), timeout=heartbeat)
          await websocket.send_json(event.model_dump(mode="json"))
        except TimeoutError:
          await websocket.send_json({"type": "ping"})
  except WebSocketDisconnect:
    return
