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
from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from bluegate.api.dependencies import get_pairing_agent
from bluegate.api.errors import ApiException
from bluegate.bluetooth.agent import PairingAgent
from bluegate.models.pairing import PairingRequest
from bluegate.models.pairing import PasskeySubmission
from bluegate.models.pairing import PinCodeSubmission

API_TAG_METADATA = {
  "name": "Pairing Agent",
  "description": "Respond to BlueZ pairing prompts (PIN codes, passkeys, confirmations, authorizations).",
}

router = APIRouter(prefix="/pairing", tags=[API_TAG_METADATA["name"]])


def _not_found(request_id: str) -> ApiException:
  return ApiException(
    code="PAIRING_REQUEST_NOT_FOUND",
    message="The pairing request does not exist or has already been resolved.",
    status_code=status.HTTP_404_NOT_FOUND,
    details={"request_id": request_id},
  )


@router.get("/", summary="List pending pairing requests")
async def list_pairing_requests(agent: PairingAgent = Depends(get_pairing_agent)) -> list[PairingRequest]:
  return agent.list_pending()


@router.get("/{request_id}", summary="Get a pending pairing request")
async def get_pairing_request(request_id: str, agent: PairingAgent = Depends(get_pairing_agent)) -> PairingRequest:
  request = agent.get_request(request_id)
  if request is None:
    raise _not_found(request_id)

  return request


@router.post("/{request_id}/confirm", summary="Confirm a pairing request", status_code=status.HTTP_202_ACCEPTED)
async def confirm_pairing_request(request_id: str, agent: PairingAgent = Depends(get_pairing_agent)) -> dict[str, bool]:
  if not agent.confirm(request_id, True):
    raise _not_found(request_id)

  return {"confirmed": True}


@router.post("/{request_id}/cancel", summary="Cancel a pairing request", status_code=status.HTTP_202_ACCEPTED)
async def cancel_pairing_request(request_id: str, agent: PairingAgent = Depends(get_pairing_agent)) -> dict[str, bool]:
  if not agent.cancel(request_id):
    raise _not_found(request_id)

  return {"cancelled": True}


@router.post("/{request_id}/pin", summary="Submit a PIN code", status_code=status.HTTP_202_ACCEPTED)
async def submit_pin_code(
  request_id: str,
  submission: PinCodeSubmission,
  agent: PairingAgent = Depends(get_pairing_agent),
) -> dict[str, bool]:
  if not agent.submit_pin(request_id, submission.pin_code):
    raise _not_found(request_id)

  return {"submitted": True}


@router.post("/{request_id}/passkey", summary="Submit a passkey", status_code=status.HTTP_202_ACCEPTED)
async def submit_passkey(
  request_id: str,
  submission: PasskeySubmission,
  agent: PairingAgent = Depends(get_pairing_agent),
) -> dict[str, bool]:
  if not agent.submit_passkey(request_id, submission.passkey):
    raise _not_found(request_id)

  return {"submitted": True}
