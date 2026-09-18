from __future__ import annotations

import json
from pathlib import Path

import cloudinary.utils
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from services import uploads
from services.rate_limit import SlidingWindowLimiter
from storage.cloudinary.cloudinary_storage import CloudinaryUploadStorage
from storage.database.models import PlatformRoleGrant, UploadRecord, User
from storage.database.shared.model import Base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_API_SECRET = "test-api-secret"

FORMAT_FOR_MIME = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


class FakeCloudinaryStorage(CloudinaryUploadStorage):
    """Real signing and signature checks, with the network calls stubbed out."""

    def __init__(self) -> None:
        super().__init__(
            cloud_name="test-cloud",
            api_key="test-api-key",
            api_secret=TEST_API_SECRET,
            root_folder="campusmeet",
        )
        self.assets: dict[str, dict] = {}
        self.deleted: list[tuple[str, str, str]] = []

    def fetch_asset(self, *, public_id, resource_type, delivery_type):
        asset = self.assets.get(public_id)
        if asset is None:
            return None
        if asset["resource_type"] != resource_type or asset["type"] != delivery_type:
            return None
        return asset

    def presign_download(self, *, key, resource_type, delivery_type, format, expires_in=300):
        return (
            f"https://download.example/{key}"
            f"?resource={resource_type}&type={delivery_type}&expires={expires_in}"
        )

    def delete(self, *, key, resource_type="image", delivery_type="upload"):
        self.deleted.append((key, resource_type, delivery_type))
        self.assets.pop(key, None)
        return True


def _register_asset(storage, record, *, size=None, fmt=None, version=1700000000, asset_id="asset-1"):
    """Simulate a successful browser upload landing in Cloudinary."""
    asset = {
        "public_id": record.object_key,
        "asset_id": asset_id,
        "resource_type": record.cloudinary_resource_type,
        "type": record.cloudinary_delivery_type,
        "format": fmt or FORMAT_FOR_MIME[record.mime_type],
        "bytes": record.expected_size if size is None else size,
        "version": version,
    }
    storage.assets[record.object_key] = asset
    return asset


def _claimed(asset, storage, *, signed=True, **overrides):
    payload = {
        "public_id": asset["public_id"],
        "version": asset["version"],
        "asset_id": asset["asset_id"],
        "resource_type": asset["resource_type"],
        "type": asset["type"],
        "format": asset["format"],
        "bytes": asset["bytes"],
    }
    if signed:
        payload["signature"] = cloudinary.utils.api_sign_request(
            {"public_id": asset["public_id"], "version": asset["version"]},
            storage.api_secret,
            signature_version=1,
        )
    payload.update(overrides)
    return payload


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


def _cloudinary_upload(session, storage, owner, *, purpose, filename, mime_type, size):
    record, ticket = uploads.create_upload(
        session,
        storage,
        owner,
        purpose=purpose,
        filename=filename,
        mime_type=mime_type,
        size=size,
    )
    session.commit()
    return record, ticket


def test_cloudinary_public_and_private_uploads_pick_the_right_resource_and_delivery_types():
    session, owner, _, _ = _session()
    storage = FakeCloudinaryStorage()

    avatar, avatar_ticket = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="avatar",
        filename="avatar.png",
        mime_type="image/png",
        size=100,
    )
    assert avatar.provider == "cloudinary"
    assert avatar.object_key == f"campusmeet/public/avatars/{owner.id}/{avatar.id}"
    assert avatar.cloudinary_public_id == avatar.object_key
    assert "avatar.png" not in avatar.object_key
    assert avatar.cloudinary_resource_type == "image"
    assert avatar.cloudinary_delivery_type == "upload"
    assert avatar.private is False
    assert avatar_ticket["url"] == "https://api.cloudinary.com/v1_1/test-cloud/image/upload"

    evidence, evidence_ticket = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="organization_evidence",
        filename="evidence.pdf",
        mime_type="application/pdf",
        size=2048,
    )
    assert evidence.private is True
    assert evidence.object_key.startswith("campusmeet/private/organization-evidence/")
    assert evidence.cloudinary_resource_type == "raw"
    assert evidence.cloudinary_delivery_type == "authenticated"
    assert evidence_ticket["url"] == "https://api.cloudinary.com/v1_1/test-cloud/raw/upload"


def test_cloudinary_ticket_signs_the_issued_fields_without_exposing_the_api_secret():
    session, owner, _, _ = _session()
    storage = FakeCloudinaryStorage()
    record, ticket = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="avatar",
        filename="avatar.png",
        mime_type="image/png",
        size=100,
    )

    assert TEST_API_SECRET not in json.dumps(ticket)
    assert ticket["method"] == "POST"
    assert ticket["encoding"] == "multipart/form-data"
    assert ticket["file_field"] == "file"
    assert ticket["fields"]["api_key"] == "test-api-key"
    assert ticket["fields"]["public_id"] == record.object_key
    assert ticket["fields"]["type"] == "upload"
    assert ticket["fields"]["overwrite"] == "false"

    signed_fields = {
        key: value
        for key, value in ticket["fields"].items()
        if key not in {"signature", "api_key"}
    }
    assert ticket["fields"]["signature"] == cloudinary.utils.api_sign_request(
        signed_fields, TEST_API_SECRET
    )
    assert storage.verify_echoed_signature(
        public_id=record.object_key,
        timestamp=signed_fields["timestamp"],
        delivery_type="upload",
        signature=ticket["fields"]["signature"],
    )
    assert not storage.verify_echoed_signature(
        public_id=record.object_key,
        timestamp=signed_fields["timestamp"],
        delivery_type="authenticated",
        signature=ticket["fields"]["signature"],
    )


def test_cloudinary_completion_uses_admin_metadata_and_ignores_client_urls():
    session, owner, _, _ = _session()
    storage = FakeCloudinaryStorage()
    record, _ = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="avatar",
        filename="avatar.png",
        mime_type="image/png",
        size=100,
    )
    asset = _register_asset(storage, record)
    claimed = _claimed(asset, storage)
    claimed["secure_url"] = "https://attacker.example/stolen.png"

    completed = uploads.complete_upload(session, storage, owner, record.id, claimed=claimed)
    session.commit()

    assert completed.status == "completed"
    assert completed.actual_size == asset["bytes"]
    assert completed.cloudinary_asset_id == "asset-1"
    assert completed.cloudinary_format == "png"
    assert completed.cloudinary_version == asset["version"]
    assert completed.cloudinary_secure_url == (
        "https://res.cloudinary.com/test-cloud/image/upload"
        f"/v{asset['version']}/{record.object_key}.png"
    )
    assert "attacker.example" not in completed.cloudinary_secure_url
    assert uploads.public_url_for(completed) == completed.cloudinary_secure_url


@pytest.mark.parametrize(
    "overrides",
    [
        {"public_id": "campusmeet/public/avatars/1/attacker"},
        {"bytes": 101},
        {"format": "webp"},
    ],
)
def test_cloudinary_completion_rejects_tampered_claims_and_discards_the_asset(overrides):
    session, owner, _, _ = _session()
    storage = FakeCloudinaryStorage()
    record, _ = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="avatar",
        filename="avatar.png",
        mime_type="image/png",
        size=100,
    )
    asset = _register_asset(storage, record)

    with pytest.raises(ValueError):
        uploads.complete_upload(
            session, storage, owner, record.id, claimed=_claimed(asset, storage, **overrides)
        )

    assert storage.deleted == [(record.object_key, "image", "upload")]
    assert record.status == "pending"
    assert record.actual_size is None


def test_cloudinary_completion_rejects_a_forged_response_signature():
    session, owner, _, _ = _session()
    storage = FakeCloudinaryStorage()
    record, _ = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="avatar",
        filename="avatar.png",
        mime_type="image/png",
        size=100,
    )
    asset = _register_asset(storage, record)
    claimed = _claimed(asset, storage)
    claimed["signature"] = cloudinary.utils.api_sign_request(
        {"public_id": asset["public_id"], "version": asset["version"]},
        "some-other-secret",
        signature_version=1,
    )

    with pytest.raises(ValueError):
        uploads.complete_upload(session, storage, owner, record.id, claimed=claimed)

    assert record.status == "pending"


def test_cloudinary_private_evidence_keeps_no_public_url_and_download_is_operator_only():
    session, owner, reviewer, ordinary = _session()
    storage = FakeCloudinaryStorage()
    record, _ = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="organization_evidence",
        filename="evidence.pdf",
        mime_type="application/pdf",
        size=2048,
    )
    asset = _register_asset(storage, record, fmt="pdf")
    completed = uploads.complete_upload(
        session, storage, owner, record.id, claimed=_claimed(asset, storage)
    )
    session.commit()

    assert completed.status == "completed"
    assert completed.private is True
    assert completed.cloudinary_secure_url is None
    with pytest.raises(ValueError):
        uploads.public_url_for(completed)

    with pytest.raises(PermissionError):
        uploads.reviewer_download_url(session, storage, ordinary, record.id)

    url = uploads.reviewer_download_url(session, storage, reviewer, record.id)
    assert "expires=300" in url
    assert "resource=raw" in url
    assert "type=authenticated" in url


def test_cloudinary_avatar_replacement_destroys_the_previous_asset():
    session, owner, _, _ = _session()
    storage = FakeCloudinaryStorage()
    previous_key = f"campusmeet/public/avatars/{owner.id}/previous"
    session.add(
        UploadRecord(
            id="old-cloudinary-avatar",
            owner_id=owner.id,
            purpose="avatar",
            object_key=previous_key,
            original_filename="old.png",
            mime_type="image/png",
            expected_size=100,
            actual_size=100,
            private=False,
            status="attached",
            attached_to_type="user_avatar",
            attached_to_id=str(owner.id),
            provider="cloudinary",
            cloudinary_public_id=previous_key,
            cloudinary_resource_type="image",
            cloudinary_delivery_type="upload",
            cloudinary_format="png",
            cloudinary_secure_url=f"https://res.cloudinary.com/test-cloud/image/upload/{previous_key}.png",
        )
    )
    session.commit()

    current, _ = _cloudinary_upload(
        session,
        storage,
        owner,
        purpose="avatar",
        filename="new.png",
        mime_type="image/png",
        size=120,
    )
    asset = _register_asset(storage, current, size=120)
    uploads.complete_upload(session, storage, owner, current.id, claimed=_claimed(asset, storage))
    session.commit()

    attached = uploads.attach_public_upload(session, storage, owner, current.id, target_id=None)
    session.commit()

    assert attached.status == "attached"
    assert owner.avatar == attached.cloudinary_secure_url
    assert session.get(UploadRecord, "old-cloudinary-avatar").status == "replaced"
    assert storage.deleted == [(previous_key, "image", "upload")]


def test_cloudinary_migration_keeps_legacy_s3_rows_intact(tmp_path, monkeypatch):
    db_path = tmp_path / "uploads-migration.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", "")

    command.upgrade(config, "20260914_19")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO uploads (id, owner_id, purpose, object_key, original_filename,"
                " mime_type, expected_size, private, status)"
                " VALUES ('legacy-1', 1, 'avatar', 'public/avatars/1/legacy.png',"
                " 'legacy.png', 'image/png', 100, 0, 'completed')"
            )
        )
    engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT provider, cloudinary_public_id FROM uploads WHERE id = 'legacy-1'")
        ).one()
        columns = {
            column["name"] for column in inspect(engine).get_columns("uploads")
        }
    engine.dispose()

    assert row.provider == "s3"
    assert row.cloudinary_public_id is None
    assert {
        "cloudinary_asset_id",
        "cloudinary_public_id",
        "cloudinary_resource_type",
        "cloudinary_delivery_type",
        "cloudinary_format",
        "cloudinary_version",
        "cloudinary_secure_url",
    } <= columns


def test_cloudinary_wins_over_the_legacy_s3_backend(monkeypatch):
    for key in (
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
        "OBJECT_STORAGE_ENDPOINT",
        "OBJECT_STORAGE_BUCKET",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError):
        uploads.get_upload_storage()

    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT", "https://s3.example")
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "campusmeet")
    monkeypatch.setenv("OBJECT_STORAGE_ACCESS_KEY", "access")
    monkeypatch.setenv("OBJECT_STORAGE_SECRET_KEY", "secret")
    assert uploads.storage_provider(uploads.get_upload_storage()) == "s3"

    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test-api-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", TEST_API_SECRET)
    storage = uploads.get_upload_storage()

    assert isinstance(storage, CloudinaryUploadStorage)
    assert uploads.storage_provider(storage) == "cloudinary"


def test_partial_cloudinary_config_fails_loudly_instead_of_using_s3(monkeypatch):
    for key in (
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
        "OBJECT_STORAGE_ENDPOINT",
        "OBJECT_STORAGE_BUCKET",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("OBJECT_STORAGE_ENDPOINT", "https://s3.example")
    monkeypatch.setenv("OBJECT_STORAGE_BUCKET", "campusmeet")
    monkeypatch.setenv("OBJECT_STORAGE_ACCESS_KEY", "access")
    monkeypatch.setenv("OBJECT_STORAGE_SECRET_KEY", "secret")
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")

    with pytest.raises(RuntimeError, match="CLOUDINARY_API_KEY"):
        uploads.get_upload_storage()


def test_upload_ticket_limiter_enforces_a_sliding_window():
    limiter = SlidingWindowLimiter(limit=3, window_seconds=100)

    assert [limiter.allow("user-1", now=moment) for moment in (0, 1, 2)] == [True, True, True]
    assert limiter.allow("user-1", now=3) is False
    assert limiter.retry_after_seconds("user-1", now=3) >= 1
    assert limiter.allow("user-2", now=3) is True
    assert limiter.retry_after_seconds("user-2", now=3) == 0
    assert limiter.allow("user-1", now=101) is True
