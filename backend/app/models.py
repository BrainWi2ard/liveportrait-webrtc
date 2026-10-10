"""SQLAlchemy ORM models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from app.database import Base


class AssetTypeEnum(PyEnum):
    """Asset type enumeration."""
    FACE = "face"
    VOICE = "voice"


class CallStatusEnum(PyEnum):
    """Call session status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    media_assets = relationship("MediaAsset", back_populates="user", cascade="all, delete-orphan")
    call_sessions = relationship("CallSession", back_populates="user", cascade="all, delete-orphan")


class MediaAsset(Base):
    """Media asset model for uploaded or preset face/voice files."""
    __tablename__ = "media_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    asset_type = Column(Enum(AssetTypeEnum), nullable=False)
    s3_key = Column(String(512), nullable=False, unique=True)
    is_preset = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="media_assets")
    call_sessions = relationship("CallSession", back_populates="target_asset")


class CallSession(Base):
    """Call session model for tracking active and completed calls."""
    __tablename__ = "call_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(CallStatusEnum), default=CallStatusEnum.PENDING, nullable=False)
    target_asset_id = Column(Integer, ForeignKey("media_assets.id"), nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="call_sessions")
    target_asset = relationship("MediaAsset", back_populates="call_sessions")
