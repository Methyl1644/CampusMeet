"""演示数据灌入脚本

用法：
    python scripts/seed.py

会清空现有数据后重新灌入演示数据。演示账号见 docs/e2e-checklist.md。

数据对应 config/agent_llm_config.json 里的演示数据说明：
- 用户：小王(ID=1, wang@nju.edu.cn)、小李(ID=2)、小张(ID=3)、小陈(ID=4)
- 帖子：挑战杯(ID=1)、数据结构(ID=2)、篮球(ID=3)、美赛(ID=4, 作者小王)
- 申请：小李申请美赛(ID=1, 已接受)
- 会话：小王和小李的美赛会话(ID=1, 已确认组队)
- 团队：美赛团队(ID=1, 含分工/议程/任务/风险)

运行前提：
- .env 已配 DATABASE_URL
- 表已建好（后端首次启动自动建表，或手动执行 Base.metadata.create_all）
"""
import os
import sys
import datetime

# 让 src 包可被导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from storage.database.db import ensure_compatibility_columns, get_db_url
from storage.database.shared.model import Base
from storage.database.models import (
    User, Post, Application, Conversation, Message, Team, TeamMember, VerificationCode,
    Organization, OrganizationMember, PostTag, Tag, TagAlias, Topic, TopicFollow, TopicTag,
)
from utils.auth import hash_password
from services.content import normalize_text, seed_content_catalog


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _build_users() -> list[User]:
    return [
        User(
            id=1,
            email="wang@nju.edu.cn",
            phone=None,
            wechat="wang_wechat",
            password_hash=hash_password("wang123456"),
            nickname="小王",
            major="计算机科学与技术",
            grade="大三",
            skills=["Python", "数学建模", "数据分析"],
            auth_status="verified",
            site_role="operator",
            verified_email="wang@nju.edu.cn",
            post_count=1,
            team_count=1,
        ),
        User(
            id=2,
            email="li@nju.edu.cn",
            phone=None,
            wechat="li_wechat",
            password_hash=hash_password("li123456"),
            nickname="小李",
            major="数学",
            grade="研一",
            skills=["数学建模", "论文写作", "R"],
            auth_status="verified",
            verified_email="li@nju.edu.cn",
            post_count=0,
            team_count=1,
        ),
        User(
            id=3,
            email="zhang@nju.edu.cn",
            phone="13800000003",
            wechat=None,
            password_hash=hash_password("zhang123456"),
            nickname="小张",
            major="统计学",
            grade="大二",
            skills=["数据分析", "Python"],
            auth_status="verified",
            verified_email="zhang@nju.edu.cn",
            post_count=0,
            team_count=0,
        ),
        User(
            id=4,
            email="chen@nju.edu.cn",
            phone="13800000004",
            wechat=None,
            password_hash=hash_password("chen123456"),
            nickname="小陈",
            major="金融学",
            grade="大一",
            skills=["PPT设计", "英语写作"],
            auth_status="verified",
            verified_email="chen@nju.edu.cn",
            post_count=0,
            team_count=0,
        ),
    ]


def _build_posts() -> list[Post]:
    return [
        Post(
            id=1,
            title="挑战杯项目组队",
            description="挑战杯备赛，已有2人，缺1名负责数据分析和1名负责PPT制作的同学。",
            source_type="user",
            kind="topic_team",
            topic_id=2,
            main_category="竞赛与项目",
            tags=["挑战杯", "数据分析"],
            activity_name="挑战杯",
            current_members=2,
            target_members=4,
            needed_roles=["数据分析", "PPT制作"],
            weekly_hours="每周8小时",
            school_scope="南京大学",
            deadline="2026-10-15",
            risk_level="low",
            status="recruiting",
            author_id=1,
        ),
        Post(
            id=2,
            title="数据结构课程学习小组",
            description="每周一起刷数据结构题，备战期末。",
            source_type="user",
            kind="casual_invitation",
            main_category="学习与科研",
            tags=["数据结构", "期末复习"],
            activity_name="数据结构学习",
            current_members=3,
            target_members=5,
            needed_roles=["学习搭子"],
            weekly_hours="每周4小时",
            school_scope="南京大学",
            deadline="2026-12-20",
            risk_level="low",
            status="recruiting",
            author_id=3,
        ),
        Post(
            id=3,
            title="篮球搭子长期招募",
            description="每周三晚7点四组团球场，缺2人。",
            source_type="user",
            kind="casual_invitation",
            main_category="体育与健身",
            tags=["篮球"],
            activity_name="院系篮球活动",
            current_members=3,
            target_members=5,
            needed_roles=["篮球搭子"],
            weekly_hours="每周2小时",
            school_scope="南京大学",
            deadline=None,
            risk_level="low",
            status="recruiting",
            author_id=4,
        ),
        Post(
            id=4,
            title="美赛队伍招募建模和写作队友",
            description="2026年美赛，我负责编程，需要1名建模和1名写作队友，目标M奖及以上。",
            source_type="user",
            kind="topic_team",
            topic_id=1,
            main_category="竞赛与项目",
            tags=["美赛", "数学建模"],
            activity_name="美国大学生数学建模竞赛",
            current_members=1,
            target_members=3,
            needed_roles=["建模", "写作"],
            weekly_hours="每周10小时",
            school_scope="南京大学",
            deadline="2026-01-20",
            risk_level="low",
            status="full",
            author_id=1,
        ),
    ]


def _build_organization() -> tuple[Organization, OrganizationMember]:
    organization = Organization(
        id=1,
        name="软件学院学生会",
        org_type="college",
        school_scope="南京大学软件学院",
        verification_status="approved",
        verified_at=_now(),
    )
    member = OrganizationMember(
        id=1,
        organization_id=1,
        user_id=3,
        role="publisher",
        status="active",
    )
    return organization, member


def _build_topics() -> list[Topic]:
    return [
        Topic(
            id=1,
            channel="official",
            title="美国大学生数学建模竞赛（MCM/ICM）2026",
            short_title="美赛 2026",
            organizer="COMAP",
            organizer_key=normalize_text("COMAP"),
            canonical_event_key="mcmicm",
            edition="2026",
            summary="三人团队参赛的国际数学建模竞赛，面向建模、编程与论文写作协作。",
            content="这里集中展示赛事说明、报名时间、规则资料和来源更新。平台组队不等同于主办方正式报名。",
            source_url="https://www.comap.com/contests/mcm-icm",
            created_by=1,
        ),
        Topic(
            id=2,
            channel="official",
            title="挑战杯全国大学生课外学术科技作品竞赛",
            short_title="挑战杯",
            organizer="挑战杯竞赛组委会",
            organizer_key=normalize_text("挑战杯竞赛组委会"),
            canonical_event_key="挑战杯",
            edition="2026",
            summary="围绕科技发明、社会调查等方向开展的大学生创新竞赛。",
            content="话题收录校内通知、赛程节点与组队资料，具体资格与提交要求以学校通知为准。",
            created_by=1,
        ),
        Topic(
            id=3,
            channel="organization",
            title="软件学院秋季羽毛球交流赛",
            short_title="软院羽毛球赛",
            organizer="软件学院学生会",
            organizer_key=normalize_text("软件学院学生会"),
            canonical_event_key="软件学院羽毛球交流赛",
            edition="2026秋",
            summary="面向学院同学的双打交流活动，可在话题下寻找队友。",
            content="活动由认证组织发布，报名时间与场地安排将在此更新。",
            organization_id=1,
            created_by=3,
        ),
    ]


def _build_topic_tags() -> list[TopicTag]:
    return [
        TopicTag(topic_id=1, tag_id="activity_math_modeling"),
        TopicTag(topic_id=1, tag_id="level_international"),
        TopicTag(topic_id=2, tag_id="activity_innovation"),
        TopicTag(topic_id=2, tag_id="level_national"),
        TopicTag(topic_id=3, tag_id="activity_badminton"),
        TopicTag(topic_id=3, tag_id="level_college"),
    ]


def _build_application() -> Application:
    return Application(
        id=1,
        post_id=4,
        applicant_id=2,
        role_wanted="建模",
        experience="参加过校数学建模竞赛获一等奖，擅长优化模型。",
        available_time="每周10小时",
        reason="对美赛很感兴趣，想和有编程能力的同学组队冲M奖。",
        questions=["你们之前有美赛经验吗？"],
        status="accepted",
    )


def _build_conversation_and_messages() -> tuple[Conversation, list[Message]]:
    conv = Conversation(
        id=1,
        post_id=4,
        post_author_id=1,
        applicant_id=2,
        application_id=1,
        status="team_confirmed",
        contact_unlocked=True,
        last_message="好的，我们今晚开个首次会议吧",
        last_message_at=_now(),
    )
    msgs = [
        Message(id=1, conversation_id=1, sender_id=2, content="你好，我申请了美赛建模，想了解下你们的编程方案"),
        Message(id=2, conversation_id=1, sender_id=1, content="我用Python，主要用numpy和scipy，建模部分你打算用什么思路？"),
        Message(id=3, conversation_id=1, sender_id=2, content="优化类问题我比较熟，评价类也能做"),
        Message(id=4, conversation_id=1, sender_id=1, content="好的，我们今晚开个首次会议吧"),
    ]
    return conv, msgs


def _build_team_and_members() -> tuple[Team, list[TeamMember]]:
    team = Team(
        id=1,
        post_id=4,
        activity_name="美国大学生数学建模竞赛",
        division_of_labor=[
            {"role": "编程", "responsibilities": "数据处理、算法实现、代码调试", "member_id": "1"},
            {"role": "建模", "responsibilities": "数学模型构建、求解方案设计", "member_id": "2"},
            {"role": "写作", "responsibilities": "论文撰写、图表制作、摘要打磨", "member_id": "1"},
        ],
        meeting_agenda=[
            {"id": "a1", "content": "自我介绍与分工确认", "done": True},
            {"id": "a2", "content": "讨论备赛时间表", "done": False},
            {"id": "a3", "content": "确定练习赛题目", "done": False},
            {"id": "a4", "content": "约定每周固定讨论时间", "done": False},
            {"id": "a5", "content": "建立共享文档和代码仓库", "done": False},
        ],
        task_list=[
            {"id": "t1", "title": "完成第一套练习赛题", "done": False},
            {"id": "t2", "title": "整理常用建模算法清单", "done": False},
            {"id": "t3", "title": "搭建Python代码框架", "done": False},
            {"id": "t4", "title": "准备论文模板", "done": False},
        ],
        risk_reminders=[
            "美赛时间紧，建议提前做2套完整练习赛",
            "三人分工要明确，避免建模和写作脱节",
            "注意时差，比赛期间合理安排作息",
        ],
        contact_info=[
            {"user_id": "1", "nickname": "小王", "phone": None, "wechat": "wang_wechat"},
            {"user_id": "2", "nickname": "小李", "phone": None, "wechat": "li_wechat"},
        ],
    )
    members = [
        TeamMember(team_id=1, user_id=1, suggested_role="编程"),
        TeamMember(team_id=1, user_id=2, suggested_role="建模"),
    ]
    return team, members


def main():
    db_url = get_db_url()
    if not db_url:
        print("[seed] 错误：DATABASE_URL 未配置，请检查 .env")
        sys.exit(1)

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    ensure_compatibility_columns(engine)

    with Session(engine) as session:
        # 清空（按外键依赖顺序）
        for table in ["audit_logs", "topic_follows", "post_tags", "topic_tags", "organization_members",
                      "organization_applications", "messages", "team_members", "teams",
                      "conversations", "applications", "posts", "topics", "organizations",
                      "tag_aliases", "tags", "verification_codes", "users"]:
            session.execute(text(f"DELETE FROM {table}"))
        # 重置自增序列，保证 ID 固定
        if engine.dialect.name == "postgresql":
            for sequence in ["users_id_seq", "posts_id_seq", "applications_id_seq", "conversations_id_seq",
                             "messages_id_seq", "teams_id_seq", "team_members_id_seq"]:
                session.execute(text(f"ALTER SEQUENCE IF EXISTS {sequence} RESTART WITH 1"))
        session.commit()

        # 灌入
        for u in _build_users():
            session.add(u)
        seed_content_catalog(session)
        organization, organization_member = _build_organization()
        session.add(organization)
        session.add(organization_member)
        for topic in _build_topics():
            session.add(topic)
        for topic_tag in _build_topic_tags():
            session.add(topic_tag)
        for p in _build_posts():
            session.add(p)
        session.add_all(
            [
                PostTag(post_id=1, tag_id="activity_innovation"),
                PostTag(post_id=3, tag_id="activity_basketball"),
                PostTag(post_id=4, tag_id="activity_math_modeling"),
            ]
        )
        session.add(_build_application())
        conv, msgs = _build_conversation_and_messages()
        session.add(conv)
        for m in msgs:
            session.add(m)
        team, members = _build_team_and_members()
        session.add(team)
        for m in members:
            session.add(m)
        session.commit()

    print("[seed] 演示数据灌入完成")
    print("  用户：小王(wang@nju.edu.cn/wang123456)、小李、小张、小陈")
    print("  帖子：4 条（美赛 ID=4 已满员，其余招募中）")
    print("  话题：3 条（官方 2 条、认证组织 1 条）")
    print("  申请：小李申请美赛（已接受）")
    print("  会话：小王-小李美赛会话（已确认组队）")
    print("  团队：美赛团队（含分工/议程/任务/风险）")


if __name__ == "__main__":
    main()
