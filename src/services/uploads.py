from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import cloudinary.utils
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.operators import has_platform_role
from services.permissions import can_manage_topic
from storage.cloudinary.cloudinary_storage import (
    MIME_TO_FORMATS,
    PRIVATE_DELIVERY_TYPE,
    PUBLIC_DELIVERY_TYPE,
    CloudinaryUploadStorage,
    resource_type_for,
)
from storage.database.models import Topic, UploadRecord, User
from storage.s3.s3_storage import S3SyncStorage


logger = logging.getLogger(__name__)

LEGACY_PROVIDER = "s3"
CLOUDINARY_PROVIDER = "cloudinary"
UPLOAD_TICKET_TTL_SECONDS = 600

UPLOAD_POLICIES = {
    "post_cover": {
        "mimes": {"image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/webp": {".webp"}},
        "max_size": 10 * 1024 * 1024,
        "prefix": "public/post-covers",
        "private": False,
    },
    "avatar": {
        "mimes": {"image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/webp": {".webp"}},
        "max_size": 5 * 1024 * 1024,
        "prefix": "public/avatars",
        "private": False,
    },
    "topic_cover": {
        "mimes": {"image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/webp": {".webp"}},
        "max_size": 10 * 1024 * 1024,
        "prefix": "public/topic-covers",
        "private": False,
    },
    "organization_evidence": {
        "mimes": {
            "application/pdf": {".pdf"},
            "image/jpeg": {".jpg", ".jpeg"},
            "image/png": {".png"},
        },
        "max_size": 15 * 1024 * 1024,
        "prefix": "private/organization-evidence",
        "private": True,
    },
}


class S3UploadStorage:
    provider = LEGACY_PROVIDER
    # A presigned PUT pins Content-Type but not the byte count, so the declared
    # size is re-checked from the object metadata at completion time.
    enforces_size_server_side = False

    def __init__(self) -> None:
        self.storage = S3SyncStorage(
            endpoint_url=os.getenv("OBJECT_STORAGE_ENDPOINT"),
            access_key=os.getenv("OBJECT_STORAGE_ACCESS_KEY", ""),
            secret_key=os.getenv("OBJECT_STORAGE_SECRET_KEY", ""),
            bucket_name=os.getenv("OBJECT_STORAGE_BUCKET", ""),
            region=os.getenv("OBJECT_STORAGE_REGION", "auto"),
        )

    def presign_upload(self, *, key: str, content_type: str, max_size: int, expires_in: int) -> dict[str, Any]:
        return {
            "provider": LEGACY_PROVIDER,
            "url": self.storage.create_presigned_put(
                key=key, content_type=content_type, expire_time=expires_in
            ),
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "max_size": max_size,
        }

    def head_metadata(self, *, key: str) -> dict[str, Any] | None:
        return self.storage.head_metadata(key=key)

    def presign_download(self, *, key: str, expires_in: int) -> str:
        return self.storage.create_presigned_get(key=key, expire_time=expires_in)

    def delete(self, *, key: str) -> None:
        self.storage.delete_file(file_key=key)


def cloudinary_settings() -> dict[str, str] | None:
    """Return Cloudinary credentials when all three secrets are present."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.getenv("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "").strip()
    if not (cloud_name and api_key and api_secret):
        return None
    return {
        "cloud_name": cloud_name,
        "api_key": api_key,
        "api_secret": api_secret,
        "root_folder": os.getenv("CLOUDINARY_ROOT_FOLDER", "campusmeet").strip() or "campusmeet",
    }


def s3_settings() -> dict[str, str] | None:
    required = (
        "OBJECT_STORAGE_ENDPOINT",
        "OBJECT_STORAGE_BUCKET",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
    )
    if not all(os.getenv(key, "").strip() for key in required):
        return None
    return {"endpoint": os.getenv("OBJECT_STORAGE_ENDPOINT", "")}


def get_upload_storage() -> CloudinaryUploadStorage | S3UploadStorage:
    """Cloudinary wins when configured; S3 stays as the legacy fallback."""
    settings = cloudinary_settings()
    if settings is not None:
        return CloudinaryUploadStorage(**settings)
    if s3_settings() is not None:
        return S3UploadStorage()
    raise RuntimeError("对象存储未完整配置")


def storage_provider(storage: Any) -> str:
    return str(getattr(storage, "provider", LEGACY_PROVIDER) or LEGACY_PROVIDER)


def _policy(purpose: str) -> dict[str, Any] | None:
    return UPLOAD_POLICIES.get(purpose)


def _delivery_type_for(policy: dict[str, Any]) -> str:
    return PRIVATE_DELIVERY_TYPE if policy["private"] else PUBLIC_DELIVERY_TYPE


def _object_identifier(
    *, provider: str, storage: Any, policy: dict[str, Any], owner_id: int, upload_id: str, suffix: str
) -> str:
    prefix = policy["prefix"]
    if provider == CLOUDINARY_PROVIDER:
        # Cloudinary infers the format from the bytes, so the extension is
        # deliberately absent and the root folder becomes part of the path.
        root = str(getattr(storage, "root_folder", "campusmeet")).strip("/")
        return f"{root}/{prefix}/{owner_id}/{upload_id}"
    return f"{prefix}/{owner_id}/{upload_id}{suffix}"


def create_upload(
    session: Session,
    storage: Any,
    owner: User,
    *,
    purpose: str,
    filename: str,
    mime_type: str,
    size: int,
) -> tuple[UploadRecord, dict[str, Any]]:
    policy = _policy(purpose)
    normalized_mime = str(mime_type or "").split(";", 1)[0].strip().lower()
    suffix = Path(filename).suffix.lower()
    if policy is None:
        raise ValueError("上传用途不受支持")
    if normalized_mime not in policy["mimes"] or suffix not in policy["mimes"][normalized_mime]:
        raise ValueError("文件类型与扩展名不匹配")
    if size <= 0 or size > int(policy["max_size"]):
        raise ValueError("文件大小超出允许范围")

    upload_id = uuid4().hex
    provider = storage_provider(storage)
    object_key = _object_identifier(
        provider=provider,
        storage=storage,
        policy=policy,
        owner_id=owner.id,
        upload_id=upload_id,
        suffix=suffix,
    )
    expires_in = UPLOAD_TICKET_TTL_SECONDS
    record = UploadRecord(
        id=upload_id,
        owner_id=owner.id,
        purpose=purpose,
        object_key=object_key,
        original_filename=Path(filename).name[:255],
        mime_type=normalized_mime,
        expected_size=size,
        private=bool(policy["private"]),
        status="pending",
        provider=provider,
        expires_at=_utcnow() + datetime.timedelta(seconds=expires_in),
    )
    if provider == CLOUDINARY_PROVIDER:
        record.cloudinary_public_id = object_key
        record.cloudinary_resource_type = resource_type_for(
            normalized_mime, private=bool(policy["private"])
        )
        record.cloudinary_delivery_type = _delivery_type_for(policy)

    session.add(record)
    instruction = _build_instruction(
        storage=storage,
        record=record,
        policy=policy,
        mime_type=normalized_mime,
        size=size,
        expires_in=expires_in,
    )
    return record, instruction


def _build_instruction(
    *,
    storage: Any,
    record: UploadRecord,
    policy: dict[str, Any],
    mime_type: str,
    size: int,
    expires_in: int,
) -> dict[str, Any]:
    if storage_provider(storage) == CLOUDINARY_PROVIDER:
        return storage.build_upload_ticket(
            public_id=record.object_key,
            resource_type=record.cloudinary_resource_type
            or resource_type_for(mime_type, private=bool(policy["private"])),
            delivery_type=record.cloudinary_delivery_type or _delivery_type_for(policy),
            max_size=size,
            expires_in=expires_in,
        )
    return storage.presign_upload(
        key=record.object_key,
        content_type=mime_type,
        max_size=size,
        expires_in=expires_in,
    )


def complete_upload(
    session: Session,
    storage: Any,
    owner: User,
    upload_id: str,
    *,
    claimed: dict[str, Any] | None = None,
) -> UploadRecord:
    record = session.get(UploadRecord, upload_id)
    if record is None:
        raise ValueError("上传记录不存在")
    if record.owner_id != owner.id:
        raise PermissionError("无权完成该上传")
    if record.status == "completed":
        return record
    if record.status != "pending":
        raise ValueError("上传状态不可完成")
    if _is_expired(record.expires_at):
        raise ValueError("上传凭证已过期，请重新获取")

    if _record_provider(record) == CLOUDINARY_PROVIDER:
        metadata = _verify_cloudinary_upload(storage, record, claimed or {})
    else:
        metadata = _verify_legacy_upload(storage, record)

    record.actual_size = int(metadata["bytes"])
    if _record_provider(record) == CLOUDINARY_PROVIDER:
        record.cloudinary_asset_id = metadata.get("asset_id") or None
        record.cloudinary_public_id = metadata["public_id"]
        record.cloudinary_resource_type = metadata["resource_type"]
        record.cloudinary_delivery_type = metadata["delivery_type"]
        record.cloudinary_format = metadata.get("format") or None
        record.cloudinary_version = metadata.get("version")
        # Private assets never keep a stored URL; reviewers get a signed one.
        record.cloudinary_secure_url = None if record.private else metadata.get("url") or None
    record.status = "completed"
    record.completed_at = _utcnow()
    return record


def _verify_legacy_upload(storage: Any, record: UploadRecord) -> dict[str, Any]:
    metadata = storage.head_metadata(key=record.object_key)
    if not metadata:
        raise ValueError("未找到已上传文件")
    actual_mime = str(metadata.get("content_type") or "").split(";", 1)[0].lower()
    actual_size = int(metadata.get("size") or 0)
    if actual_mime != record.mime_type or actual_size != record.expected_size:
        raise ValueError("上传文件与预申报的类型或大小不一致")
    return {"bytes": actual_size, "public_id": record.object_key}


def _verify_cloudinary_upload(
    storage: Any, record: UploadRecord, claimed: dict[str, Any]
) -> dict[str, Any]:
    if storage_provider(storage) != CLOUDINARY_PROVIDER:
        raise RuntimeError("当前对象存储无法校验 Cloudinary 上传")

    public_id = str(claimed.get("public_id") or "")
    if not public_id or public_id != record.object_key:
        _discard_cloudinary_asset(storage, record)
        raise ValueError("上传资源与凭证不匹配")

    signature = str(claimed.get("signature") or "")
    if signature:
        version = claimed.get("version")
        if not _response_signature_matches(public_id, version, signature):
            _discard_cloudinary_asset(storage, record)
            raise ValueError("上传凭据校验失败")

    resource_type = record.cloudinary_resource_type or "image"
    delivery_type = record.cloudinary_delivery_type or PUBLIC_DELIVERY_TYPE
    asset = storage.verified_asset(
        key=record.object_key, resource_type=resource_type, delivery_type=delivery_type
    )
    if asset is None:
        # Nothing trustworthy to delete: we never got a confirmed asset id.
        raise ValueError("未找到已上传文件")

    claimed_asset_id = str(claimed.get("asset_id") or "")
    if claimed_asset_id and asset["asset_id"] and claimed_asset_id != asset["asset_id"]:
        _discard_cloudinary_asset(storage, record)
        raise ValueError("上传资源与凭证不匹配")

    allowed_formats = MIME_TO_FORMATS.get(record.mime_type, set())
    if not asset["format"] or asset["format"] not in allowed_formats:
        _discard_cloudinary_asset(storage, record)
        raise ValueError("上传文件格式与预申报的类型不一致")
    if int(asset["bytes"]) != int(record.expected_size):
        _discard_cloudinary_asset(storage, record)
        raise ValueError("上传文件与预申报的类型或大小不一致")

    # The Admin API result stays authoritative; the client's claims only have to
    # agree with it, so a tampered payload cannot talk us into a wrong asset.
    claimed_bytes = claimed.get("bytes")
    if claimed_bytes is not None and int(claimed_bytes) != int(asset["bytes"]):
        _discard_cloudinary_asset(storage, record)
        raise ValueError("上传文件与预申报的类型或大小不一致")
    claimed_format = str(claimed.get("format") or "").lower()
    if claimed_format and claimed_format != asset["format"]:
        _discard_cloudinary_asset(storage, record)
        raise ValueError("上传文件格式与预申报的类型不一致")
    return asset


def _response_signature_matches(public_id: str, version: Any, signature: str) -> bool:
    """Verify the signature Cloudinary returns on the asset itself."""
    try:
        return bool(
            cloudinary.utils.verify_api_response_signature(public_id, version, signature)
        )
    except Exception:
        logger.warning("Cloudinary response signature verification failed")
        return False


def _discard_cloudinary_asset(storage: Any, record: UploadRecord) -> None:
    """Best-effort removal of a rejected asset; never masks the real error."""
    delete_upload_asset(storage, record)


def delete_upload_asset(storage: Any, record: UploadRecord) -> bool:
    """Remove the backing object for a record, whichever provider stored it."""
    try:
        if _record_provider(record) == CLOUDINARY_PROVIDER:
            return bool(
                storage.delete(
                    key=record.cloudinary_public_id or record.object_key,
                    resource_type=record.cloudinary_resource_type or "image",
                    delivery_type=record.cloudinary_delivery_type or PUBLIC_DELIVERY_TYPE,
                )
            )
        storage.delete(key=record.object_key)
        return True
    except Exception:
        logger.warning("Failed to delete stored upload object")
        return False


def public_url_for(record: UploadRecord) -> str:
    """Resolve the reader-facing URL from stored, server-verified metadata."""
    if _record_provider(record) == CLOUDINARY_PROVIDER:
        if record.private:
            raise ValueError("私密材料不能作为公开媒体")
        if not record.cloudinary_secure_url:
            raise ValueError("封面存储服务尚未配置，请暂时移除封面后发布")
        return record.cloudinary_secure_url
    base = os.getenv("OBJECT_STORAGE_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not base.startswith("https://"):
        raise ValueError("封面存储服务尚未配置，请暂时移除封面后发布")
    return f"{base}/{record.object_key}"


def attach_new_post_cover(session, actor, post, upload_id: str) -> None:
    record = session.scalar(select(UploadRecord).where(UploadRecord.id == upload_id).with_for_update())
    if record is None or record.owner_id != actor.id or record.purpose != "post_cover" or record.private:
        raise ValueError("请使用自己上传的帖子封面")
    if record.status != "completed":
        raise ValueError("封面未完成上传或已用于其他帖子")
    post.cover_url = public_url_for(record)
    record.status = "attached"
    record.attached_to_type = "post_cover"
    record.attached_to_id = str(post.id)


def attach_public_upload(
    session: Session,
    storage: Any,
    actor: User,
    upload_id: str,
    *,
    target_id: int | None,
    public_base_url: str | None = None,
) -> UploadRecord:
    record = session.get(UploadRecord, upload_id)
    if record is None:
        raise ValueError("上传记录不存在")
    if record.owner_id != actor.id:
        raise PermissionError("无权使用该上传")
    if record.private or record.purpose not in {"avatar", "topic_cover"}:
        raise ValueError("该上传不能作为公开媒体")
    if record.status == "attached":
        return record
    if record.status != "completed":
        raise ValueError("上传尚未完成校验")

    if public_base_url is not None and _record_provider(record) != CLOUDINARY_PROVIDER:
        base_url = public_base_url.strip().rstrip("/")
        if not base_url:
            raise RuntimeError("对象存储公开访问地址未配置")
        resolved_url = f"{base_url}/{record.object_key}"
    else:
        resolved_url = public_url_for(record)

    if record.purpose == "avatar":
        if target_id not in {None, actor.id}:
            raise PermissionError("头像只能绑定到当前账号")
        attached_to_type = "user_avatar"
        attached_to_id = str(actor.id)
        actor.avatar = resolved_url
    else:
        if target_id is None:
            raise ValueError("话题封面必须指定话题")
        topic = session.get(Topic, target_id)
        if topic is None:
            raise ValueError("话题不存在")
        if not can_manage_topic(session, actor, topic, "edit_topic"):
            raise PermissionError("无权修改该话题封面")
        attached_to_type = "topic_cover"
        attached_to_id = str(topic.id)
        topic.cover_url = resolved_url

    previous = session.scalars(
        select(UploadRecord).where(
            UploadRecord.attached_to_type == attached_to_type,
            UploadRecord.attached_to_id == attached_to_id,
            UploadRecord.status == "attached",
            UploadRecord.id != record.id,
        )
    ).all()
    for old_record in previous:
        # Cloudinary destroy runs with invalidate=True so the CDN entry goes too.
        delete_upload_asset(storage, old_record)
        old_record.status = "replaced"

    record.status = "attached"
    record.attached_to_type = attached_to_type
    record.attached_to_id = attached_to_id
    return record


def reviewer_download_url(
    session: Session,
    storage: Any,
    reviewer: User,
    upload_id: str,
) -> str:
    if not has_platform_role(session, reviewer):
        raise PermissionError("仅平台运营可查看私有认证材料")
    record = session.get(UploadRecord, upload_id)
    if record is None or not record.private or record.status not in {"completed", "attached"}:
        raise ValueError("私有材料不存在或不可用")
    if _record_provider(record) == CLOUDINARY_PROVIDER:
        resource_type = record.cloudinary_resource_type or resource_type_for(
            record.mime_type, private=True
        )
        delivery_type = record.cloudinary_delivery_type or PRIVATE_DELIVERY_TYPE
        fmt = record.cloudinary_format or _default_format(record.mime_type)
        try:
            return storage.presign_download(
                key=record.cloudinary_public_id or record.object_key,
                resource_type=resource_type,
                delivery_type=delivery_type,
                format=fmt,
                expires_in=300,
            )
        except Exception:
            logger.warning("Failed to build a private download URL")
            raise RuntimeError("证明材料暂时无法下载，请稍后重试")
    return storage.presign_download(key=record.object_key, expires_in=300)


def _record_provider(record: UploadRecord) -> str:
    return str(getattr(record, "provider", None) or LEGACY_PROVIDER)


def _default_format(mime_type: str) -> str:
    formats = MIME_TO_FORMATS.get(mime_type) or {"pdf"}
    return sorted(formats)[0]


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _is_expired(value: datetime.datetime | None) -> bool:
    if value is None:
        return False
    moment = value if value.tzinfo is not None else value.replace(tzinfo=datetime.timezone.utc)
    return _utcnow() > moment
