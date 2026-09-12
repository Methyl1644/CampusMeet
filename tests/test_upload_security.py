from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services import uploads
from storage.database.models import PlatformRoleGrant, UploadRecord, User
from storage.database.shared.model import Base


class FakeStorage:
    def __init__(self):
        self.metadata = {}
        self.deleted = []

    def presign_upload(self, *, key, content_type, max_size, expires_in):
        return {"url": f"https://upload.example/{key}", "method": "PUT", "headers": {"Content-Type": content_type}}

    def head_metadata(self, *, key):
        return self.metadata.get(key)

    def presign_download(self, *, key, expires_in):
        return f"https://download.example/{key}?expires={expires_in}"

    def delete(self, *, key):
        self.deleted.append(key)
        self.metadata.pop(key, None)


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    owner = User(id=1, email="owner@nju.edu.cn", password_hash="x", nickname="owner", auth_status="verified")
    reviewer = User(id=2, email="reviewer@nju.edu.cn", password_hash="x", nickname="reviewer", auth_status="verified")
    ordinary = User(id=3, email="ordinary@nju.edu.cn", password_hash="x", nickname="ordinary", auth_status="verified")
    session.add_all([owner, reviewer, ordinary])
    session.flush()
    session.add(
        PlatformRoleGrant(
            user_id=reviewer.id,
            role="operator",
            status="active",
            granted_by=reviewer.id,
        )
    )
    session.commit()
    return session, owner, reviewer, ordinary


@pytest.mark.parametrize(
    ("purpose", "filename", "mime_type", "size"),
    [
        ("avatar", "avatar.exe", "image/png", 100),
        ("avatar", "avatar.png", "application/pdf", 100),
        ("organization_evidence", "evidence.pdf", "application/pdf", 20 * 1024 * 1024),
        ("unknown", "file.png", "image/png", 100),
    ],
)
def test_upload_creation_rejects_unsafe_type_extension_or_size(purpose, filename, mime_type, size):
    session, owner, _, _ = _session()

    with pytest.raises(ValueError):
        uploads.create_upload(
            session,
            FakeStorage(),
            owner,
            purpose=purpose,
            filename=filename,
            mime_type=mime_type,
            size=size,
        )


def test_private_evidence_uses_owned_random_key_and_must_match_uploaded_metadata():
    session, owner, _, _ = _session()
    storage = FakeStorage()

    record, instruction = uploads.create_upload(
        session,
        storage,
        owner,
        purpose="organization_evidence",
        filename="evidence.pdf",
        mime_type="application/pdf",
        size=1024,
    )
    session.commit()

    assert record.object_key.startswith("private/organization-evidence/1/")
    assert "evidence.pdf" not in record.object_key
    assert instruction["method"] == "PUT"
    storage.metadata[record.object_key] = {"size": 1024, "content_type": "application/pdf"}
    completed = uploads.complete_upload(session, storage, owner, record.id)
    session.commit()
    assert completed.status == "completed"


def test_completion_rejects_wrong_owner_or_changed_object_metadata():
    session, owner, _, ordinary = _session()
    storage = FakeStorage()
    record, _ = uploads.create_upload(
        session,
        storage,
        owner,
        purpose="avatar",
        filename="avatar.png",
        mime_type="image/png",
        size=100,
    )
    session.commit()
    storage.metadata[record.object_key] = {"size": 101, "content_type": "image/png"}

    with pytest.raises(PermissionError):
        uploads.complete_upload(session, storage, ordinary, record.id)
    with pytest.raises(ValueError):
        uploads.complete_upload(session, storage, owner, record.id)


def test_private_evidence_download_requires_operator_and_is_short_lived():
    session, owner, reviewer, ordinary = _session()
    storage = FakeStorage()
    record = UploadRecord(
        id="upload-1",
        owner_id=owner.id,
        purpose="organization_evidence",
        object_key="private/organization-evidence/1/file.pdf",
        original_filename="evidence.pdf",
        mime_type="application/pdf",
        expected_size=100,
        actual_size=100,
        private=True,
        status="completed",
    )
    session.add(record)
    session.commit()

    with pytest.raises(PermissionError):
        uploads.reviewer_download_url(session, storage, ordinary, record.id)
    url = uploads.reviewer_download_url(session, storage, reviewer, record.id)
    assert "expires=300" in url


def test_completed_avatar_can_be_attached_and_replaces_the_previous_object():
    session, owner, _, _ = _session()
    storage = FakeStorage()
    previous = UploadRecord(
        id="old-avatar",
        owner_id=owner.id,
        purpose="avatar",
        object_key="public/avatars/1/old.png",
        original_filename="old.png",
        mime_type="image/png",
        expected_size=100,
        actual_size=100,
        private=False,
        status="attached",
        attached_to_type="user_avatar",
        attached_to_id=str(owner.id),
    )
    current = UploadRecord(
        id="new-avatar",
        owner_id=owner.id,
        purpose="avatar",
        object_key="public/avatars/1/new.png",
        original_filename="new.png",
        mime_type="image/png",
        expected_size=120,
        actual_size=120,
        private=False,
        status="completed",
    )
    session.add_all([previous, current])
    session.commit()

    attached = uploads.attach_public_upload(
        session,
        storage,
        owner,
        current.id,
        target_id=None,
        public_base_url="https://media.example",
    )
    session.commit()

    assert attached.status == "attached"
    assert owner.avatar == "https://media.example/public/avatars/1/new.png"
    assert previous.status == "replaced"
    assert storage.deleted == ["public/avatars/1/old.png"]


def test_private_evidence_cannot_be_attached_as_public_media():
    session, owner, _, _ = _session()
    record = UploadRecord(
        id="private-evidence",
        owner_id=owner.id,
        purpose="organization_evidence",
        object_key="private/organization-evidence/1/file.pdf",
        original_filename="file.pdf",
        mime_type="application/pdf",
        expected_size=100,
        actual_size=100,
        private=True,
        status="completed",
    )
    session.add(record)
    session.commit()

    with pytest.raises(ValueError):
        uploads.attach_public_upload(
            session,
            FakeStorage(),
            owner,
            record.id,
            target_id=None,
            public_base_url="https://media.example",
        )
