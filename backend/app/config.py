"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Core app
    app_name: str = "LivePortrait-WebRTC"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/liveportrait"
    
    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    
    # S3
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "liveportrait-assets"
    s3_region: str = "us-east-1"
    s3_use_path_style: bool = True
    
    # GPU Worker
    gpu_worker_base_url: str = "http://localhost:9001"
    gpu_worker_api_key: str = "replace-with-gpu-token"
    
    # CORS
    allowed_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
