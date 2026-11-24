from __future__ import annotations

import io
import uuid
from dataclasses import dataclass

import boto3
from botocore.client import Config
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import get_settings


@dataclass
class UploadedPhoto:
    object_key: str
    url: str
    thumb_url: str
    width: int
    height: int
    size_bytes: int


def _client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def _public_url(key: str) -> str:
    settings = get_settings()
    return f"{settings.s3_public_url.rstrip('/')}/{settings.s3_bucket}/{key}"


async def upload_property_photo(file: UploadFile, property_id: int) -> UploadedPhoto:
    settings = get_settings()
    content = await file.read()
    if len(content) > settings.max_photo_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Photo too large")
    content_type = file.content_type or ""
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported image type")

    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid image") from exc

    width, height = image.size
    thumb = image.copy()
    thumb.thumbnail((640, 640))
    thumb_buf = io.BytesIO()
    fmt = "JPEG" if content_type != "image/png" else "PNG"
    thumb.convert("RGB").save(thumb_buf, format="JPEG", quality=82)
    thumb_bytes = thumb_buf.getvalue()

    uid = uuid.uuid4().hex
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    key = f"properties/{property_id}/{uid}.{ext}"
    thumb_key = f"properties/{property_id}/{uid}_thumb.jpg"

    client = _client()
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=thumb_key,
        Body=thumb_bytes,
        ContentType="image/jpeg",
    )
    return UploadedPhoto(
        object_key=key,
        url=_public_url(key),
        thumb_url=_public_url(thumb_key),
        width=width,
        height=height,
        size_bytes=len(content),
    )
