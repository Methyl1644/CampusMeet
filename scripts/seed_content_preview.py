"""Add idempotent topic/tag preview data without deleting registered users."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import select

from services.content import normalize_text, seed_content_catalog
from storage.database.db import get_session
from storage.database.models import Organization, OrganizationMember, Post, PostTag, Topic, TopicTag, User


def main() -> None:
    session = get_session()
    try:
        seed_content_catalog(session)
        publisher = session.execute(
            select(User).where(User.auth_status.in_(["verified", "organization", "campus_verified"])).order_by(User.id)
        ).scalars().first()
        if not publisher:
            print("[preview] No campus-verified user; skipped topic data.")
            session.commit()
            return

        organization = session.execute(
            select(Organization).where(Organization.name == "软件学院学生会")
        ).scalar_one_or_none()
        if not organization:
            organization = Organization(
                name="软件学院学生会",
                org_type="college",
                school_scope="南京大学软件学院",
                verification_status="approved",
            )
            session.add(organization)
            session.flush()
            session.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=publisher.id,
                    role="publisher",
                    status="active",
                )
            )

        topic_specs = [
            {
                "channel": "official",
                "title": "美国大学生数学建模竞赛（MCM/ICM）2026",
                "short_title": "美赛 2026",
                "organizer": "COMAP",
                "event_key": "mcmicm",
                "edition": "2026",
                "summary": "三人团队参赛的国际数学建模竞赛，面向建模、编程与论文写作协作。",
                "content": "这里集中展示赛事说明、报名时间、规则资料和来源更新。平台组队不等同于主办方正式报名。",
                "source_url": "https://www.comap.com/contests/mcm-icm",
                "tag_ids": ["activity_math_modeling", "level_international"],
            },
            {
                "channel": "official",
                "title": "挑战杯全国大学生课外学术科技作品竞赛",
                "short_title": "挑战杯",
                "organizer": "挑战杯竞赛组委会",
                "event_key": "挑战杯",
                "edition": "2026",
                "summary": "围绕科技发明、社会调查等方向开展的大学生创新竞赛。",
                "content": "话题收录校内通知、赛程节点与组队资料，具体资格与提交要求以学校通知为准。",
                "tag_ids": ["activity_innovation", "level_national"],
            },
            {
                "channel": "organization",
                "title": "软件学院秋季羽毛球交流赛",
                "short_title": "软院羽毛球赛",
                "organizer": "软件学院学生会",
                "event_key": "软件学院羽毛球交流赛",
                "edition": "2026秋",
                "summary": "面向学院同学的双打交流活动，可在话题下寻找队友。",
                "content": "活动由认证组织发布，报名时间与场地安排将在此更新。",
                "tag_ids": ["activity_badminton", "level_college"],
                "organization_id": organization.id,
            },
        ]

        topics: dict[str, Topic] = {}
        for spec in topic_specs:
            topic = session.execute(
                select(Topic).where(
                    Topic.organizer_key == normalize_text(spec["organizer"]),
                    Topic.canonical_event_key == spec["event_key"],
                    Topic.edition == spec["edition"],
                )
            ).scalar_one_or_none()
            if not topic:
                topic = Topic(
                    channel=spec["channel"],
                    title=spec["title"],
                    short_title=spec["short_title"],
                    organizer=spec["organizer"],
                    organizer_key=normalize_text(spec["organizer"]),
                    canonical_event_key=spec["event_key"],
                    edition=spec["edition"],
                    summary=spec["summary"],
                    content=spec["content"],
                    source_url=spec.get("source_url"),
                    organization_id=spec.get("organization_id"),
                    created_by=publisher.id,
                )
                session.add(topic)
                session.flush()
                session.add_all(TopicTag(topic_id=topic.id, tag_id=tag_id) for tag_id in spec["tag_ids"])
            topics[spec["event_key"]] = topic

        post_specs = [
            ("美赛招募英文写作队友", "topic_team", topics["mcmicm"].id, "activity_math_modeling", "美国大学生数学建模竞赛", ["英文写作"]),
            ("挑战杯项目招募数据分析同学", "topic_team", topics["挑战杯"].id, "activity_innovation", "挑战杯", ["数据分析"]),
            ("周五仙林羽毛球搭子", "casual_invitation", None, "activity_badminton", "羽毛球", ["球友"]),
        ]
        for title, kind, topic_id, tag_id, activity_name, roles in post_specs:
            existing = session.execute(select(Post).where(Post.title == title)).scalar_one_or_none()
            if existing:
                continue
            post = Post(
                title=title,
                description="希望找到时间合适、沟通及时的同学一起参与。",
                source_type="user",
                kind=kind,
                topic_id=topic_id,
                main_category="竞赛与项目" if kind == "topic_team" else "体育与健身",
                tags=[tag_id],
                activity_name=activity_name,
                target_members=3 if kind == "topic_team" else 2,
                needed_roles=roles,
                weekly_hours="每周 4 小时" if kind == "topic_team" else "周五晚",
                school_scope="南京大学仙林校区",
                status="recruiting",
                author_id=publisher.id,
            )
            session.add(post)
            session.flush()
            session.add(PostTag(post_id=post.id, tag_id=tag_id))

        session.commit()
        print("[preview] Content catalog ready: 3 topics and 3 posts (idempotent).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
