from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.operators import has_platform_role
from services.permissions import can_manage_topic
from storage.database.models import Topic, UploadRecord, User
from storage.s3.s3_storage import S3SyncStorage


UPLOAD_POLICIES = {
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


def get_upload_storage() -> S3UploadStorage:
    required = (
        "OBJECT_STORAGE_ENDPOINT",
        "OBJECT_STORAGE_BUCKET",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
    )
    if not all(os.getenv(key, "").strip() for key in required):
        raise RuntimeError("对象存储未完整配置")
    return S3UploadStorage()


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
    policy = UPLOAD_POLICIES.get(purpose)
    normalized_mime = str(mime_type or "").split(";", 1)[0].strip().lower()
    suffix = Path(filename).suffix.lower()
    if policy is None:
        raise ValueError("上传用途不受支持")
    if normalized_mime not in policy["mimes"] or suffix not in policy["mimes"][normalized_mime]:
        raise ValueError("文件类型与扩展名不匹配")
    if size <= 0 or size > int(policy["max_size"]):
        raise ValueError("文件大小超出允许范围")
    upload_id = uuid4().hex
    object_key = f"{policy['prefix']}/{owner.id}/{upload_id}{suffix}"
    expires_in = 600
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
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in),
    )
    session.add(record)
    instruction = storage.presign_upload(
        key=object_key,
        content_type=normalized_mime,
        max_size=size,
        expires_in=expires_in,
    )
    return record, instruction


def complete_upload(session: Session, storage: Any, owner: User, upload_id: str) -> UploadRecord:
    record = session.get(UploadRecord, upload_id)
    if record is None:
        raise ValueError("上传记录不存在")
    if record.owner_id != owner.id:
        raise PermissionError("无权完成该上传")
    if record.status == "completed":
        return record
    if record.status != "pending":
        raise ValueError("上传状态不可完成")
    metadata = storage.head_metadata(key=record.object_key)
    if not metadata:
        raise ValueError("未找到已上传文件")
    actual_mime = str(metadata.get("content_type") or "").split(";", 1)[0].lower()
    actual_size = int(metadata.get("size") or 0)
    if actual_mime != record.mime_type or actual_size != record.expected_size:
        raise ValueError("上传文件与预申报的类型或大小不一致")
    record.actual_size = actual_size
    record.status = "completed"
    record.completed_at = datetime.datetime.now(datetime.timezone.utc)
    return record


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

    base_url = (public_base_url or os.getenv("OBJECT_STORAGE_PUBLIC_BASE_URL", "")).strip().rstrip("/")
    if not base_url:
        raise RuntimeError("对象存储公开访问地址未配置")

    if record.purpose == "avatar":
        if target_id not in {None, actor.id}:
            raise PermissionError("头像只能绑定到当前账号")
        attached_to_type = "user_avatar"
        attached_to_id = str(actor.id)
        actor.avatar = f"{base_url}/{record.object_key}"
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
        topic.cover_url = f"{base_url}/{record.object_key}"

    previous = session.scalars(
        select(UploadRecord).where(
            UploadRecord.attached_to_type == attached_to_type,
            UploadRecord.attached_to_id == attached_to_id,
            UploadRecord.status == "attached",
            UploadRecord.id != record.id,
        )
    ).all()
    for old_record in previous:
        storage.delete(key=old_record.object_key)
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
    return storage.presign_download(key=record.object_key, expires_in=300)
