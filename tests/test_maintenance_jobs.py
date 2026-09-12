from __future__ import annotations

import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from jobs.maintenance import run_maintenance
from storage.database.models import (
    Notification,
    Organization,
    OrganizationApplication,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationOwnershipTransfer,
    PlatformRoleGrant,
    Post,
    PostCollaborator,
    Topic,
    TopicCollaborator,
    UploadRecord,
    User,
)
from storage.database.shared.model import Base


def test_maintenance_expires_records_closes_posts_and_retains_unread_notifications():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime.datetime.now(datetime.timezone.utc)
    expired = now - datetime.timedelta(days=1)
    old = now - datetime.timedelta(days=200)

    with factory() as session:
        session.add_all(
            [
                User(id=1, email="owner@nju.edu.cn", password_hash="x", nickname="owner"),
                User(id=2, email="member@nju.edu.cn", password_hash="x", nickname="member"),
            ]
        )
        organization = Organization(
            id=1,
            name="过期组织",
            org_type="student_org",
            verification_status="approved",
            verified_at=old,
            expires_at=expired,
        )
        post = Post(
            id=1,
            title="已过期招募",
            description="测试",
            main_category="体育",
            activity_name="羽毛球",
            target_members=3,
            author_id=1,
            status="recruiting",
            deadline=expired.isoformat(),
        )
        topic = Topic(
            id=1,
            channel="organization",
            title="测试活动",
            short_title="测试",
            organizer="测试组织",
            organizer_key="test-org",
            canonical_event_key="test-event",
            edition="2026",
            summary="摘要",
            content="内容",
            created_by=1,
        )
        session.add_all([organization, post, topic])
        session.flush()
        session.add_all(
            [
                OrganizationMember(
                    organization_id=1,
                    user_id=1,
                    role="owner",
                    status="active",
                    expires_at=expired,
                ),
                OrganizationInvitation(
                    organization_id=1,
                    inviter_id=1,
                    invitee_id=2,
                    requested_role="member",
                    status="pending",
                    expires_at=expired,
                ),
                OrganizationOwnershipTransfer(
                    organization_id=1,
                    from_owner_id=1,
                    to_owner_id=2,
                    initiated_by=1,
                    status="pending",
                    expires_at=expired,
                ),
                PlatformRoleGrant(
                    user_id=2,
                    role="operator",
                    status="active",
                    granted_by=1,
                    effective_at=old,
                    expires_at=expired,
                ),
                TopicCollaborator(
                    topic_id=1,
                    user_id=2,
                    role="editor",
                    status="pending",
                    granted_by=1,
                    expires_at=expired,
                ),
                PostCollaborator(
                    post_id=1,
                    user_id=2,
                    role="editor",
                    status="active",
                    granted_by=1,
                    expires_at=expired,
                ),
                UploadRecord(
                    id="expired-upload",
                    owner_id=1,
                    purpose="avatar",
                    object_key="users/1/avatar/expired.jpg",
                    original_filename="expired.jpg",
                    mime_type="image/jpeg",
                    expected_size=100,
                    private=False,
                    status="pending",
                    expires_at=expired,
                ),
                Notification(
                    user_id=1,
                    event_type="old.read",
                    title="旧已读",
                    body="可清理",
                    dedupe_key="old-read",
                    read_at=old,
                    created_at=old,
                ),
                Notification(
                    user_id=1,
                    event_type="old.unread",
                    title="旧未读",
                    body="必须保留",
                    dedupe_key="old-unread",
                    created_at=old,
                ),
            ]
        )
        session.commit()

        first = run_maintenance(session, now=now, notification_retention_days=180)
        session.commit()

        assert first == {
            "organizations_expired": 1,
            "memberships_expired": 1,
            "invitations_expired": 1,
            "ownership_transfers_expired": 1,
            "platform_grants_expired": 1,
            "topic_grants_expired": 1,
            "post_grants_expired": 1,
            "posts_closed": 1,
            "uploads_abandoned": 1,
            "rejected_evidence_deleted": 0,
            "notifications_deleted": 1,
            "expiry_reminders_created": 0,
        }
        assert session.get(Organization, 1).verification_status == "expired"
        assert session.get(Post, 1).status == "closed"
        assert session.get(UploadRecord, "expired-upload").status == "abandoned"
        assert session.query(Notification).filter_by(dedupe_key="old-unread").one()

        second = run_maintenance(session, now=now, notification_retention_days=180)
        session.commit()
        assert all(value == 0 for value in second.values())


def test_maintenance_creates_one_expiry_reminder_per_grant():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime.datetime.now(datetime.timezone.utc)

    with factory() as session:
        session.add_all(
            [
                User(id=1, email="admin@nju.edu.cn", password_hash="x", nickname="admin"),
                User(id=2, email="operator@nju.edu.cn", password_hash="x", nickname="operator"),
                PlatformRoleGrant(
                    id=1,
                    user_id=2,
                    role="operator",
                    status="active",
                    granted_by=1,
                    effective_at=now,
                    expires_at=now + datetime.timedelta(days=3),
                ),
            ]
        )
        session.commit()

        first = run_maintenance(session, now=now)
        second = run_maintenance(session, now=now)
        session.commit()

        assert first["expiry_reminders_created"] == 1
        assert second["expiry_reminders_created"] == 0
        reminder = session.query(Notification).one()
        assert reminder.user_id == 2
        assert reminder.event_type == "permission.expiring"


def test_maintenance_deletes_rejected_private_evidence_after_retention_period():
    class Storage:
        def __init__(self):
            self.deleted = []

        def delete(self, *, key):
            self.deleted.append(key)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime.datetime.now(datetime.timezone.utc)
    storage = Storage()

    with factory() as session:
        session.add(User(id=1, email="owner@nju.edu.cn", password_hash="x", nickname="owner"))
        application = OrganizationApplication(
            id=1,
            applicant_id=1,
            organization_name="Rejected Org",
            org_type="student_org",
            school_scope="NJU",
            evidence="private/organization-evidence/1/file.pdf",
            evidence_reference="private/organization-evidence/1/file.pdf",
            responsible_person_statement="test",
            status="rejected",
            reviewed_at=now - datetime.timedelta(days=31),
        )
        upload = UploadRecord(
            id="rejected-evidence",
            owner_id=1,
            purpose="organization_evidence",
            object_key="private/organization-evidence/1/file.pdf",
            original_filename="file.pdf",
            mime_type="application/pdf",
            expected_size=100,
            actual_size=100,
            private=True,
            status="attached",
            attached_to_type="organization_application",
            attached_to_id="1",
        )
        session.add_all([application, upload])
        session.commit()

        result = run_maintenance(
            session,
            now=now,
            storage=storage,
            rejected_evidence_retention_days=30,
        )
        session.commit()

        assert result["rejected_evidence_deleted"] == 1
        assert upload.status == "deleted"
        assert storage.deleted == [upload.object_key]
