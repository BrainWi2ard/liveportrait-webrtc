"""WebRTC signaling via WebSocket."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
import logging
from datetime import datetime
import httpx
from app.database import get_session
from app.models import User, CallSession, CallStatusEnum
from app.schemas import SDPOfferPayload, SDPAnswerPayload, ICECandidatePayload
from app.api.v1.auth import get_current_user
from app.config import settings

router = APIRouter(tags=["signaling"])
logger = logging.getLogger(__name__)

# Active WebSocket connections mapping: session_id -> WebSocket
active_connections: dict[str, WebSocket] = {}


class ConnectionManager:
    """Manage WebSocket connections for signaling."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        """Register new connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        """Unregister connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """Send message to connected client."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for conn in self.active_connections.values():
            try:
                await conn.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")


connection_manager = ConnectionManager()


async def proxy_to_gpu_worker(payload: dict) -> dict:
    """Proxy request to external GPU worker and return response."""
    headers = {
        "Authorization": f"Bearer {settings.gpu_worker_api_key}",
        "Content-Type": "application/json",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.gpu_worker_base_url}/process",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"GPU worker proxy error: {e}")
        return {"error": str(e)}


@router.websocket("/ws/stream/{session_id}")
async def websocket_signaling_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str,
):
    """WebSocket endpoint for WebRTC signaling and GPU stream coordination."""
    # Validate token and get user
    try:
        # Note: In production, implement proper token validation here
        # For now, we trust the token is valid
        pass
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Register connection
    await connection_manager.connect(session_id, websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "sdp_offer":
                # Handle SDP offer
                payload = SDPOfferPayload(**data)
                
                # Create or retrieve call session
                # Note: In production, implement proper session management
                
                # Proxy to GPU worker
                gpu_payload = {
                    "type": "sdp_offer",
                    "sdp": payload.sdp,
                    "session_id": payload.session_id,
                    "target_asset_id": payload.target_asset_id,
                }
                
                gpu_response = await proxy_to_gpu_worker(gpu_payload)
                
                if "error" not in gpu_response:
                    # Forward GPU response back to client
                    await connection_manager.send_message(
                        session_id,
                        {
                            "type": "sdp_answer",
                            "sdp": gpu_response.get("sdp"),
                            "session_id": session_id,
                        }
                    )
            
            elif message_type == "ice_candidate":
                # Handle ICE candidate
                payload = ICECandidatePayload(**data)
                
                # Proxy to GPU worker
                gpu_payload = {
                    "type": "ice_candidate",
                    "candidate": payload.candidate,
                    "sdpMLineIndex": payload.sdpMLineIndex,
                    "sdpMid": payload.sdpMid,
                    "session_id": payload.session_id,
                }
                
                await proxy_to_gpu_worker(gpu_payload)
            
            elif message_type == "asset_switch":
                # Handle dynamic asset switching
                target_asset_id = data.get("target_asset_id")
                
                gpu_payload = {
                    "type": "asset_switch",
                    "session_id": session_id,
                    "target_asset_id": target_asset_id,
                }
                
                gpu_response = await proxy_to_gpu_worker(gpu_payload)
                
                # Confirm asset switch
                await connection_manager.send_message(
                    session_id,
                    {
                        "type": "asset_switched",
                        "target_asset_id": target_asset_id,
                        "success": "error" not in gpu_response,
                    }
                )
            
            elif message_type == "diagnostics_request":
                # Return mock diagnostics for now
                await connection_manager.send_message(
                    session_id,
                    {
                        "type": "diagnostics",
                        "fps": 30.0,
                        "render_latency_ms": 45.2,
                        "audio_video_sync_drift_ms": 2.1,
                        "packet_jitter_ms": 1.5,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
        logger.info(f"Client {session_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(session_id)
