"""帖子工具：创建、列表、详情、我的帖子"""
import json
import logging
from langchain.tools import tool
from sqlalchemy import select, desc, asc, or_, func
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from storage.database.db import get_session
from storage.database.models.user import User
from storage.database.models.post import Post
from storage.database.models.content import PostTag, Topic
from services.content import validate_tag_ids
from services.abuse_monitoring import check_and_record
from services.collaboration_lifecycle import PUBLIC_POST_STATUSES
from services.moderation_cases import has_active_restriction
from services.participation import ParticipationError, validate_post_participation
from utils.security import screen_post_content
from tools.auth_tools import _user_brief

logger = logging.getLogger(__name__)


def _post_to_dict(post: Post, author: User | None = None, session=None) -> dict:
    """将 Post 对象转为字典"""
    data = {
        "id": str(post.id),
        "title": post.title,
        "description": post.description,
        "cover_url": post.cover_url,
        "source_type": post.source_type,
        "kind": post.kind,
        "purpose": post.purpose,
        "join_mode": post.join_mode,
        "topic_id": str(post.topic_id) if post.topic_id is not None else None,
        "main_category": post.main_category,
        "tags": post.tags or [],
        "activity_name": post.activity_name,
        "current_members": post.current_members,
        "target_members": post.target_members,
        "needed_roles": post.needed_roles or [],
        "weekly_hours": post.weekly_hours,
        "school_scope": post.school_scope,
        "deadline": post.deadline,
        "risk_level": post.risk_level,
        "status": post.status,
        "author_id": str(post.author_id),
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }
    if author:
        data["author"] = _user_brief(author)
    if session is not None:
        from services.identity import post_trust_projection

        data.update(post_trust_projection(session, post))
    return data


@tool
def create_post(
    user_id: str,
    title: str,
    description: str,
    main_category: str,
    activity_name: str,
    target_members: int,
    needed_roles: str,
    weekly_hours: str = "",
    school_scope: str = "",
    deadline: str = "",
    kind: str = "casual_invitation",
    topic_id: str = "",
    tag_ids: str = "",
    suggested_tag_ids: str = "",
    review_risk_level: str = "low",
    cover_url: str = "",
    purpose: str = "team_recruitment",
    join_mode: str = "application",
) -> str:
    """创建组队帖。user_id 为用户ID，title 为标题，description 为描述，main_category 为主分类，activity_name 为活动名称，target_members 为目标人数，needed_roles 为所需角色(逗号分隔)，weekly_hours 为每周时长，school_scope 为学校范围，deadline 为截止日期。"""
    ctx = request_context.get() or new_context(method="create_post")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            user = session.execute(select(User).where(User.id == uid)).scalar_one_or_none()
            if not user:
                return json.dumps({"success": False, "message": "用户不存在"}, ensure_ascii=False)
            if user.auth_status == "unverified":
                return json.dumps({"success": False, "message": "请先完成校园邮箱认证"}, ensure_ascii=False)
            if has_active_restriction(session, uid, "posting"):
                return json.dumps(
                    {"success": False, "message": "当前账号处于发布限制期，暂时不能发布帖子"},
                    ensure_ascii=False,
                )

            abuse = check_and_record(
                session,
                user_id=uid,
                event_type="post",
                target_id=None,
                content=f"{title} {description}",
            )
            if abuse.action in {"cooldown", "review"}:
                session.commit()
                return json.dumps(
                    {
                        "success": False,
                        "message": "发布过于频繁，请稍后再试",
                        "retry_after_seconds": abuse.retry_after_seconds,
                    },
                    ensure_ascii=False,
                )

            # 安全规则引擎: 内容审核初筛
            screen = screen_post_content(title, description)
            if screen.has_violations:
                return json.dumps({
                    "success": False,
                    "message": "内容审核未通过",
                    "violations": screen.violations,
                    "suggestions": screen.suggestions,
                }, ensure_ascii=False)

            if kind not in {"topic_team", "casual_invitation"}:
                return json.dumps({"success": False, "message": "帖子类型不正确"}, ensure_ascii=False)
            resolved_topic_id = int(topic_id) if topic_id else None
            if kind == "topic_team":
                if resolved_topic_id is None:
                    return json.dumps({"success": False, "message": "正规赛事组队帖必须关联话题"}, ensure_ascii=False)
                topic = session.get(Topic, resolved_topic_id)
                if not topic or topic.status != "active":
                    return json.dumps({"success": False, "message": "关联话题不存在或不可用"}, ensure_ascii=False)
            elif resolved_topic_id is not None:
                return json.dumps({"success": False, "message": "日常邀约不能关联正式话题"}, ensure_ascii=False)

            try:
                participation = validate_post_participation(
                    session,
                    user,
                    {
                        "topic_id": resolved_topic_id,
                        "purpose": purpose,
                        "join_mode": join_mode,
                    },
                )
            except ParticipationError as exc:
                return json.dumps(
                    {"success": False, "error_code": exc.code, "message": exc.message},
                    ensure_ascii=False,
                )

            user_tag_ids = list(dict.fromkeys(item.strip() for item in tag_ids.split(",") if item.strip()))[:8]
            user_tag_id_set = set(user_tag_ids)
            ai_tag_ids = list(
                dict.fromkeys(
                    item.strip()
                    for item in suggested_tag_ids.split(",")
                    if item.strip() and item.strip() not in user_tag_id_set
                )
            )
            selected_tag_ids = (user_tag_ids + ai_tag_ids)[:8]
            invalid_tag_ids = validate_tag_ids(session, selected_tag_ids)
            if invalid_tag_ids:
                return json.dumps(
                    {"success": False, "message": f"包含未收录的标签：{', '.join(invalid_tag_ids)}"},
                    ensure_ascii=False,
                )

            roles = [r.strip() for r in needed_roles.split(",") if r.strip()] if needed_roles else []
            risk_levels = {"low": 0, "medium": 1, "high": 2}
            normalized_review_risk = review_risk_level if review_risk_level in risk_levels else "medium"
            resolved_risk_level = max(
                (screen.risk_level, normalized_review_risk),
                key=lambda value: risk_levels[value],
            )
            if resolved_risk_level == "high":
                return json.dumps(
                    {"success": False, "message": "内容风险过高，请根据审核建议修改后再发布"},
                    ensure_ascii=False,
                )
            post = Post(
                title=title,
                description=description,
                cover_url=cover_url.strip()[:500] or None,
                source_type="user",
                kind=kind,
                purpose=participation.purpose,
                join_mode=participation.join_mode,
                topic_id=resolved_topic_id,
                main_category=main_category,
                activity_name=activity_name,
                target_members=target_members,
                needed_roles=roles,
                weekly_hours=weekly_hours or None,
                school_scope=school_scope or None,
                deadline=deadline or None,
                risk_level=resolved_risk_level,
                status="recruiting",
                author_id=uid,
            )
            session.add(post)
            session.flush()
            session.add_all(
                PostTag(
                    post_id=post.id,
                    tag_id=tag_id,
                    source="user" if tag_id in user_tag_id_set else "ai",
                )
                for tag_id in selected_tag_ids
            )
            post.tags = selected_tag_ids

            # 更新用户发帖数
            user.post_count = (user.post_count or 0) + 1
            session.commit()

            return json.dumps({
                "success": True,
                "post": _post_to_dict(post, user, session),
                "risk_level": resolved_risk_level,
                "risk_factors": screen.risk_factors,
                "message": "帖子发布成功" + (f"，风险等级: {resolved_risk_level}" if resolved_risk_level != "low" else ""),
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"create_post error: {e}")
        return json.dumps({"success": False, "message": f"发布失败: {str(e)}"}, ensure_ascii=False)


@tool
def list_posts(
    tab: str = "recommend",
    page: int = 1,
    page_size: int = 10,
    category: str = "",
    tags: str = "",
    keyword: str = "",
    sort: str = "latest",
    kind: str = "",
    topic_id: str = "",
) -> str:
    """浏览帖子列表。tab 为标签页(recommend/recruiting/official/hot)，page 为页码，page_size 为每页数量，category 为主分类筛选，tags 为标签筛选(逗号分隔)，keyword 为搜索关键词，sort 为排序方式(latest/hot/deadline)。"""
    ctx = request_context.get() or new_context(method="list_posts")
    try:
        session = get_session()
        try:
            query = select(Post).where(Post.status.in_(PUBLIC_POST_STATUSES))

            if kind in {"topic_team", "casual_invitation"}:
                query = query.where(Post.kind == kind)
            if topic_id:
                query = query.where(Post.topic_id == int(topic_id))

            # Tab 筛选
            if tab == "recruiting":
                query = query.where(Post.status == "recruiting")
            elif tab == "official":
                query = query.where(Post.source_type == "official")
            elif tab == "hot":
                query = query.where(Post.status == "recruiting")

            # 分类筛选
            if category:
                query = query.where(Post.main_category == category)

            # 关键词搜索
            if keyword:
                kw = f"%{keyword}%"
                query = query.where(
                    or_(Post.title.ilike(kw), Post.description.ilike(kw), Post.activity_name.ilike(kw))
                )

            # 标签筛选
            if tags:
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                for tag in tag_list:
                    query = query.where(
                        Post.id.in_(select(PostTag.post_id).where(PostTag.tag_id == tag))
                    )

            total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0

            # 排序
            if sort == "deadline":
                query = query.order_by(asc(Post.deadline))
            else:
                query = query.order_by(desc(Post.created_at))

            # 分页
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            results = session.execute(query).scalars().all()

            # 获取作者信息
            author_ids = list({p.author_id for p in results})
            authors = {}
            if author_ids:
                author_results = session.execute(select(User).where(User.id.in_(author_ids))).scalars().all()
                authors = {a.id: a for a in author_results}

            posts = [_post_to_dict(p, authors.get(p.author_id), session) for p in results]
            return json.dumps({
                "success": True,
                "list": posts,
                "total": total,
                "page": page,
                "page_size": page_size,
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"list_posts error: {e}")
        return json.dumps({"success": False, "message": f"获取帖子列表失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_post_detail(post_id: str) -> str:
    """获取帖子详情。post_id 为帖子ID。"""
    ctx = request_context.get() or new_context(method="get_post_detail")
    try:
        session = get_session()
        try:
            pid = int(post_id)
            post = session.execute(
                select(Post).where(
                    Post.id == pid,
                    Post.status.in_(PUBLIC_POST_STATUSES),
                )
            ).scalar_one_or_none()
            if not post:
                return json.dumps({"success": False, "message": "帖子不存在"}, ensure_ascii=False)

            author = session.execute(select(User).where(User.id == post.author_id)).scalar_one_or_none()
            return json.dumps({
                "success": True,
                "post": _post_to_dict(post, author, session),
            }, ensure_ascii=False)
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_post_detail error: {e}")
        return json.dumps({"success": False, "message": f"获取详情失败: {str(e)}"}, ensure_ascii=False)


@tool
def get_my_posts(user_id: str, page: int = 1, page_size: int = 20) -> str:
    """获取我发布的帖子。user_id 为用户ID。"""
    ctx = request_context.get() or new_context(method="get_my_posts")
    try:
        session = get_session()
        try:
            uid = int(user_id)
            page = max(1, int(page))
            page_size = min(100, max(1, int(page_size)))
            filters = (Post.author_id == uid,)
            total = int(session.scalar(select(func.count()).select_from(Post).where(*filters)) or 0)
            results = session.execute(
                select(Post)
                .where(*filters)
                .order_by(desc(Post.created_at), desc(Post.id))
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars().all()
            posts = [_post_to_dict(p, session=session) for p in results]
            return json.dumps(
                {
                    "success": True,
                    "list": posts,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
                ensure_ascii=False,
            )
        finally:
            session.close()
    except Exception as e:
        logger.error(f"get_my_posts error: {e}")
        return json.dumps({"success": False, "message": f"获取我的帖子失败: {str(e)}"}, ensure_ascii=False)
