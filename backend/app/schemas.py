"""Pydantic request/response schemas."""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from enum import Enum


# ============ AUTH SCHEMAS ============

class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response model."""
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ ASSET SCHEMAS ============

class AssetTypeEnum(str, Enum):
    """Asset type enumeration."""
    FACE = "face"
    VOICE = "voice"


class AssetUploadRequest(BaseModel):
    """Asset upload request with presigned URL."""
    title: str = Field(..., min_length=1, max_length=255)
    asset_type: AssetTypeEnum
    filename: str = Field(..., min_length=1)


class PresignedURLResponse(BaseModel):
    """Presigned S3 URL response."""
    url: str
    s3_key: str
    expires_in: int = 3600


class MediaAssetResponse(BaseModel):
    """Media asset response model."""
    id: int
    title: str
    asset_type: AssetTypeEnum
    s3_key: str
    is_preset: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PresetLibraryResponse(BaseModel):
    """Preset library response containing faces and voices."""
    faces: list[MediaAssetResponse]
    voices: list[MediaAssetResponse]


# ============ WEBRTC SCHEMAS ============

class SDPOfferPayload(BaseModel):
    """WebRTC SDP offer payload."""
    sdp: str
    type: str = "offer"
    session_id: str
    target_asset_id: Optional[int] = None


class SDPAnswerPayload(BaseModel):
    """WebRTC SDP answer payload."""
    sdp: str
    type: str = "answer"
    session_id: str


class ICECandidatePayload(BaseModel):
    """WebRTC ICE candidate payload."""
    candidate: str
    sdpMLineIndex: Optional[int] = None
    sdpMid: Optional[str] = None
    session_id: str


# ============ DIAGNOSTICS SCHEMAS ============

class DiagnosticsSnapshot(BaseModel):
    """Real-time diagnostics metrics."""
    fps: float
    render_latency_ms: float
    audio_video_sync_drift_ms: float
    packet_jitter_ms: float
    timestamp: datetime


class CallStatsResponse(BaseModel):
    """Call session statistics response."""
    session_id: str
    status: str
    duration_seconds: float
    latest_diagnostics: Optional[DiagnosticsSnapshot]
    
    class Config:
        from_attributes = True
