"""AI orchestrator routes for Vercel AI SDK integration and GPU worker coordination."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])
logger = logging.getLogger(__name__)


class GPUWorkerCommand(BaseModel):
    """GPU worker command payload."""
    command_type: str = Field(..., description="Command type: swap_identity, update_voice_pitch, get_gpu_health")
    session_id: str
    target_asset_id: Optional[int] = None
    voice_pitch: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None


class GPUHealthResponse(BaseModel):
    """GPU health status response."""
    status: str
    gpu_temperature: float
    gpu_memory_used: float
    gpu_memory_total: float
    active_sessions: int
    average_latency_ms: float


class IdentitySwitchResponse(BaseModel):
    """Identity swap response."""
    success: bool
    session_id: str
    target_asset_id: int
    processing_latency_ms: float


class VoicePitchUpdateResponse(BaseModel):
    """Voice pitch update response."""
    success: bool
    session_id: str
    pitch_value: float
    applied_at: str


async def proxy_command_to_gpu_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send command to external GPU worker and return response."""
    headers = {
        "Authorization": f"Bearer {settings.gpu_worker_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.gpu_worker_base_url}/api/v1/command",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"GPU worker HTTP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GPU worker unavailable",
        )
    except Exception as e:
        logger.error(f"GPU worker proxy error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GPU worker communication failed: {str(e)}",
        )


@router.post("/swap-identity", response_model=IdentitySwitchResponse)
async def swap_identity(
    command: GPUWorkerCommand,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IdentitySwitchResponse:
    """
    Swap the target identity (face) during an active stream.
    Forwards the request to the GPU worker via proxy.
    """
    if not command.target_asset_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_asset_id is required for identity swap",
        )

    gpu_payload = {
        "command_type": "swap_identity",
        "session_id": command.session_id,
        "target_asset_id": command.target_asset_id,
        "user_id": current_user.id,
    }

    gpu_response = await proxy_command_to_gpu_worker(gpu_payload)

    if "error" in gpu_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gpu_response["error"],
        )

    return IdentitySwitchResponse(
        success=gpu_response.get("success", True),
        session_id=command.session_id,
        target_asset_id=command.target_asset_id,
        processing_latency_ms=gpu_response.get("processing_latency_ms", 0),
    )


@router.post("/update-voice-pitch", response_model=VoicePitchUpdateResponse)
async def update_voice_pitch(
    command: GPUWorkerCommand,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoicePitchUpdateResponse:
    """
    Update voice pitch parameter during an active stream.
    Forwards the request to the GPU worker via proxy.
    """
    if command.voice_pitch is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="voice_pitch is required for pitch update",
        )

    if not 0.5 <= command.voice_pitch <= 2.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="voice_pitch must be between 0.5 and 2.0",
        )

    gpu_payload = {
        "command_type": "update_voice_pitch",
        "session_id": command.session_id,
        "voice_pitch": command.voice_pitch,
        "user_id": current_user.id,
    }

    gpu_response = await proxy_command_to_gpu_worker(gpu_payload)

    if "error" in gpu_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gpu_response["error"],
        )

    return VoicePitchUpdateResponse(
        success=gpu_response.get("success", True),
        session_id=command.session_id,
        pitch_value=command.voice_pitch,
        applied_at=datetime.utcnow().isoformat(),
    )


@router.get("/gpu-health", response_model=GPUHealthResponse)
async def get_gpu_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GPUHealthResponse:
    """
    Retrieve current GPU health metrics from the GPU worker.
    """
    gpu_payload = {
        "command_type": "get_gpu_health",
        "user_id": current_user.id,
    }

    gpu_response = await proxy_command_to_gpu_worker(gpu_payload)

    if "error" in gpu_response:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=gpu_response["error"],
        )

    return GPUHealthResponse(
        status=gpu_response.get("status", "unknown"),
        gpu_temperature=gpu_response.get("gpu_temperature", 0),
        gpu_memory_used=gpu_response.get("gpu_memory_used", 0),
        gpu_memory_total=gpu_response.get("gpu_memory_total", 0),
        active_sessions=gpu_response.get("active_sessions", 0),
        average_latency_ms=gpu_response.get("average_latency_ms", 0),
    )


@router.post("/execute-command")
async def execute_command(
    command: GPUWorkerCommand,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generic command executor for dispatching arbitrary GPU worker commands.
    Validates command type and forwards to GPU worker proxy.
    """
    valid_commands = {"swap_identity", "update_voice_pitch", "get_gpu_health"}

    if command.command_type not in valid_commands:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid command_type. Must be one of: {', '.join(valid_commands)}",
        )

    gpu_payload = {
        "command_type": command.command_type,
        "session_id": command.session_id,
        "user_id": current_user.id,
        "parameters": command.parameters or {},
    }

    if command.target_asset_id:
        gpu_payload["target_asset_id"] = command.target_asset_id

    if command.voice_pitch is not None:
        gpu_payload["voice_pitch"] = command.voice_pitch

    gpu_response = await proxy_command_to_gpu_worker(gpu_payload)

    if "error" in gpu_response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gpu_response["error"],
        )

    return {
        "success": True,
        "command_type": command.command_type,
        "response": gpu_response,
        "executed_at": datetime.utcnow().isoformat(),
    }
