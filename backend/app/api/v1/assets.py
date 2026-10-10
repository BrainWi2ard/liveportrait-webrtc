"""Asset management routes."""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import boto3
from botocore.config import Config
import uuid
from app.database import get_session
from app.models import User, MediaAsset, AssetTypeEnum as ModelAssetTypeEnum
from app.schemas import (
    AssetUploadRequest, PresignedURLResponse, MediaAssetResponse,
    PresetLibraryResponse, AssetTypeEnum
)
from app.api.v1.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/assets", tags=["assets"])

# S3 client configuration
s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name=settings.s3_region,
    config=Config(s3={"addressing_style": "path"}) if settings.s3_use_path_style else None,
)


def get_s3_key(user_id: int, asset_type: str, filename: str) -> str:
    """Generate S3 object key."""
    unique_id = str(uuid.uuid4())[:8]
    return f"users/{user_id}/{asset_type}/{unique_id}_{filename}"


@router.post("/upload-presigned", response_model=PresignedURLResponse)
async def get_upload_presigned_url(
    req: AssetUploadRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PresignedURLResponse:
    """Generate presigned S3 URL for uploading asset."""
    s3_key = get_s3_key(current_user.id, req.asset_type.value, req.filename)
    
    try:
        url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.s3_bucket, "Key": s3_key},
            ExpiresIn=3600,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )
    
    # Create MediaAsset record
    asset = MediaAsset(
        user_id=current_user.id,
        title=req.title,
        asset_type=ModelAssetTypeEnum(req.asset_type.value),
        s3_key=s3_key,
        is_preset=False,
    )
    session.add(asset)
    await session.commit()
    
    return PresignedURLResponse(
        url=url,
        s3_key=s3_key,
        expires_in=3600,
    )


@router.get("/presets", response_model=PresetLibraryResponse)
async def get_presets(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PresetLibraryResponse:
    """Fetch preset library (face and voice presets)."""
    # Query preset faces
    faces_result = await session.execute(
        select(MediaAsset).where(
            (MediaAsset.is_preset == True) &
            (MediaAsset.asset_type == ModelAssetTypeEnum.FACE)
        )
    )
    faces = faces_result.scalars().all()
    
    # Query preset voices
    voices_result = await session.execute(
        select(MediaAsset).where(
            (MediaAsset.is_preset == True) &
            (MediaAsset.asset_type == ModelAssetTypeEnum.VOICE)
        )
    )
    voices = voices_result.scalars().all()
    
    return PresetLibraryResponse(
        faces=[MediaAssetResponse.from_orm(f) for f in faces],
        voices=[MediaAssetResponse.from_orm(v) for v in voices],
    )


@router.get("/my-assets", response_model=list[MediaAssetResponse])
async def get_my_assets(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[MediaAssetResponse]:
    """Fetch user's uploaded assets."""
    result = await session.execute(
        select(MediaAsset).where(MediaAsset.user_id == current_user.id)
    )
    assets = result.scalars().all()
    return [MediaAssetResponse.from_orm(a) for a in assets]
