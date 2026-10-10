"""WebRTC signaling via WebSocket with telemetry inspection and privacy filtering."""
import json
import logging
from datetime import datetime
from typing import Any, Dict

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
from sqlalchemy import select

from app.config import settings

router = APIRouter(tags=["signaling"])
logger = logging.getLogger(__name__)

connections: Dict[str, WebSocket] = {}

# Known tracker/analytics domains blocklist for telemetry inspection
TELEMETRY_BLOCKLIST = [
    "google-analytics.com",
    "analytics.google.com",
    "telemetry.browser",
    "segment.io",
    "crashlytics.com",
    "firebase.google.com",
    "metrics.backend",
    "tracking.service",
    "telemetry.service",
    "mixpanel.com",
    "amplitude.com",
    "intercom.io",
    "sentry.io",
    "rollbar.com",
    "datadog.com",
    "newrelic.com",
]


def inspect_and_filter_telemetry(payload: Dict[str, Any]) -> bool:
    """
    Screens outbound signaling and telemetry payloads against known tracker domains.
    Implements privacy protection by dropping unauthorized telemetry streams.
    Inspired by FF-Shield inspection rules.

    Args:
        payload: Dictionary containing potential telemetry data

    Returns:
        True if payload passes inspection, False if it should be dropped
    """
    # Convert payload to string for domain scanning
    payload_str = json.dumps(payload).lower()

    # Check for blocklisted domains
    for domain in TELEMETRY_BLOCKLIST:
        if domain.lower() in payload_str:
            logger.warning(f"Telemetry inspection: Blocked payload containing {domain}")
            return False

    # Check for suspicious URL patterns
    suspicious_patterns = [
        r"https?://.*analytics",
        r"https?://.*telemetry",
        r"https?://.*tracking",
        r"https?://.*metrics",
        r"beacon:",
    ]

    import re

    for pattern in suspicious_patterns:
        if re.search(pattern, payload_str, re.IGNORECASE):
            logger.warning(f"Telemetry inspection: Blocked payload matching pattern {pattern}")
            return False

    return True


async def proxy_to_gpu_worker(payload: dict) -> dict:
    """Proxy request to external GPU worker and return response."""
    headers = {
        "Authorization": f"Bearer {settings.gpu_worker_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.gpu_worker_base_url}/api/v1/proxy",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"GPU worker proxy error: {e}")
        return {"error": str(e)}


@router.websocket("/ws/stream/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for WebRTC signaling and GPU stream coordination.
    Includes telemetry inspection and privacy filtering.
    """
    await websocket.accept()
    connections[session_id] = websocket
    logger.info(f"WebSocket stream connection established: {session_id}")

    try:
        while True:
            # Receive message from client
            raw = await websocket.receive_text()
            message = json.loads(raw)

            message_type = message.get("type")
            logger.debug(f"Received signaling message type: {message_type}")

            # Inspect payload for telemetry/tracking before processing
            if not inspect_and_filter_telemetry(message):
                logger.warning(f"Dropping message due to telemetry inspection: {message_type}")
                await websocket.send_json(
                    {
                        "type": "inspection_rejected",
                        "session_id": session_id,
                        "reason": "Payload contained blocked telemetry",
                    }
                )
                continue

            if message_type == "sdp_offer":
                # Handle SDP offer
                payload = {
                    "type": "sdp_offer",
                    "session_id": session_id,
                    "sdp": message.get("sdp"),
                    "target_asset_id": message.get("target_asset_id"),
                }

                gpu_response = await proxy_to_gpu_worker(payload)

                if "error" not in gpu_response:
                    # Forward GPU response back to client (after inspection)
                    response = {
                        "type": "sdp_answer",
                        "sdp": gpu_response.get("sdp"),
                        "session_id": session_id,
                    }

                    if inspect_and_filter_telemetry(response):
                        await websocket.send_json(response)
                    else:
                        logger.warning("GPU response failed telemetry inspection")

            elif message_type == "ice_candidate":
                # Handle ICE candidate (with privacy protection)
                candidate_str = message.get("candidate", "")

                # Additional privacy check: filter local IP leaks at backend
                if any(
                    pattern in candidate_str.lower()
                    for pattern in ["192.168", "10.0", "172.16", "127.0"]
                ):
                    logger.debug("PrivacyShield: Dropped local IP leak in ICE candidate")
                    continue

                payload = {
                    "type": "ice_candidate",
                    "session_id": session_id,
                    "candidate": candidate_str,
                    "sdpMLineIndex": message.get("sdpMLineIndex"),
                    "sdpMid": message.get("sdpMid"),
                }

                await proxy_to_gpu_worker(payload)

            elif message_type == "asset_switch":
                # Handle dynamic asset switching
                target_asset_id = message.get("target_asset_id")

                payload = {
                    "type": "asset_switch",
                    "session_id": session_id,
                    "target_asset_id": target_asset_id,
                }

                gpu_response = await proxy_to_gpu_worker(payload)

                # Confirm asset switch
                await websocket.send_json(
                    {
                        "type": "asset_switched",
                        "target_asset_id": target_asset_id,
                        "success": "error" not in gpu_response,
                    }
                )

            elif message_type == "diagnostics_request":
                # Return diagnostics (mock data for local iteration)
                await websocket.send_json(
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
        connections.pop(session_id, None)
        logger.info(f"WebSocket stream disconnected: {session_id}")
    except Exception as exc:
        logger.error(f"WebSocket error: {exc}")
        connections.pop(session_id, None)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
