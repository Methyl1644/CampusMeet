import datetime
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select

from api.common import api_ok, current_user_id
from services.content import (
    create_topic,
    seed_content_catalog,
    suggest_content,
    tag_suggestions,
    topic_to_dict,
    user_permissions,
    validate_tag_ids,
)
from services.tag_governance import review_tag_proposal, submit_tag_proposal
from storage.database.db import get_session
from storage.database.models import (
    OrganizationApplication,
    Organization,
    OrganizationMember,
    AuditLog,
    Post,
    Tag,
    TagAlias,
    TagProposal,
    Topic,
    TopicFollow,
    TopicTag,
    User,
)
from tools.post_tools import _post_to_dict

router = APIRouter(tags=["content"])


def _current_user(user_id: str) -> tuple[Any, User]:
    session = get_session()
    user = session.get(User, int(user_id))
    if not user:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return session, user


@router.get("/tags")
def list_tags(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, _ = _current_user(user_id)
    try:
        tags = session.execute(
            select(Tag).where(Tag.active.is_(True)).order_by(Tag.sort_order, Tag.canonical_name)
        ).scalars().all()
        aliases = session.execute(select(TagAlias).where(TagAlias.active.is_(True))).scalars().all()
        alias_map: dict[str, list[str]] = {}
        for alias in aliases:
            alias_map.setdefault(alias.tag_id, []).append(alias.normalized_alias)
        return api_ok(
            [
                {
                    "tag_id": tag.id,
                    "canonical_name": tag.canonical_name,
                    "category": tag.category,
                    "display_color": tag.display_color,
                    "aliases": alias_map.get(tag.id, []),
                }
                for tag in tags
            ]
        )
    finally:
        session.close()


@router.get("/tags/suggestions")
def tags_suggestions(
    q: str = Query(default="", max_length=40),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, _ = _current_user(user_id)
    try:
        return api_ok({"suggestions": tag_suggestions(session, q)})
    finally:
        session.close()


def _tag_proposal_to_dict(proposal: TagProposal) -> dict[str, Any]:
    return {
        "proposal_id": str(proposal.id),
        "name": proposal.proposed_name,
        "normalized_name": proposal.normalized_name,
        "category": proposal.category,
        "source_text": proposal.source_text,
        "suggested_tag_id": proposal.suggested_tag_id,
        "status": proposal.status,
        "occurrence_count": proposal.occurrence_count,
        "submitted_by": str(proposal.submitted_by),
        "reviewed_by": str(proposal.reviewed_by) if proposal.reviewed_by else None,
        "review_reason": proposal.review_reason,
    }


@router.post("/tags/proposals")
def create_tag_proposal(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        try:
            proposal = submit_tag_proposal(
                session,
                user,
                str(body.get("name") or ""),
                str(body.get("category") or ""),
                str(body.get("source_text") or ""),
                str(body.get("suggested_tag_id") or "") or None,
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return api_ok(_tag_proposal_to_dict(proposal), "候选标签已提交")
    finally:
        session.close()


@router.get("/tags/proposals")
def list_tag_proposals(
    status: str = Query(default="pending"),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        if user.site_role != "operator":
            raise HTTPException(status_code=403, detail="仅平台运营可以查看候选标签")
        if status not in {"pending", "approved", "merged", "rejected", "all"}:
            raise HTTPException(status_code=400, detail="候选标签状态不正确")
        query = select(TagProposal)
        if status != "all":
            query = query.where(TagProposal.status == status)
        proposals = session.execute(query.order_by(desc(TagProposal.updated_at))).scalars().all()
        return api_ok([_tag_proposal_to_dict(proposal) for proposal in proposals])
    finally:
        session.close()


@router.post("/tags/proposals/{proposal_id}/review")
def review_tag_candidate(
    proposal_id: int,
    body: dict[str, Any],
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, reviewer = _current_user(user_id)
    try:
        proposal = session.get(TagProposal, proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="候选标签不存在")
        try:
            result = review_tag_proposal(
                session,
                reviewer,
                proposal,
                str(body.get("decision") or ""),
                target_tag_id=str(body.get("target_tag_id") or "") or None,
                canonical_name=str(body.get("canonical_name") or "") or None,
                reason=str(body.get("reason") or ""),
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=409 if "已经处理" in str(exc) else 400, detail=str(exc)) from exc
        data = _tag_proposal_to_dict(proposal)
        data["tag_id"] = result.id if result else None
        return api_ok(data, "候选标签审核完成")
    finally:
        session.close()


@router.get("/search/suggestions")
def search_suggestions(
    q: str = Query(default="", max_length=80),
    channel: str = "",
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, _ = _current_user(user_id)
    try:
        return api_ok(suggest_content(session, q, channel))
    finally:
        session.close()


@router.get("/topics")
def list_topics(
    channel: str = "",
    q: str = Query(default="", max_length=80),
    tag_ids: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, _ = _current_user(user_id)
    try:
        query = select(Topic).where(Topic.status == "active")
        if channel in {"official", "organization"}:
            query = query.where(Topic.channel == channel)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.where(
                Topic.title.ilike(pattern) | Topic.short_title.ilike(pattern) | Topic.organizer.ilike(pattern)
            )
        selected_tags = [item for item in tag_ids.split(",") if item][:8]
        if selected_tags:
            query = query.join(TopicTag, TopicTag.topic_id == Topic.id).where(TopicTag.tag_id.in_(selected_tags))
        query = query.distinct().order_by(desc(Topic.updated_at))
        total = len(session.execute(query).scalars().all())
        topics = session.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        return api_ok(
            {
                "list": [topic_to_dict(session, topic, int(user_id)) for topic in topics],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
    finally:
        session.close()


@router.get("/topics/{topic_id}")
def topic_detail(topic_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, _ = _current_user(user_id)
    try:
        topic = session.get(Topic, topic_id)
        if not topic or topic.status != "active":
            raise HTTPException(status_code=404, detail="话题不存在")
        return api_ok(topic_to_dict(session, topic, int(user_id)))
    finally:
        session.close()


@router.get("/topics/{topic_id}/posts")
def topic_posts(topic_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, _ = _current_user(user_id)
    try:
        if not session.get(Topic, topic_id):
            raise HTTPException(status_code=404, detail="话题不存在")
        posts = session.execute(
            select(Post)
            .where(Post.kind == "topic_team", Post.topic_id == topic_id)
            .order_by(Post.created_at.desc())
        ).scalars().all()
        authors = {
            author.id: author
            for author in session.execute(
                select(User).where(User.id.in_({post.author_id for post in posts}))
            ).scalars().all()
        } if posts else {}
        return api_ok([_post_to_dict(post, authors.get(post.author_id)) for post in posts])
    finally:
        session.close()


@router.post("/topics")
def publish_topic(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        try:
            topic = create_topic(session, user, body)
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            status = 409 if "已存在" in str(exc) else 400
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return api_ok(topic_to_dict(session, topic, int(user_id)), "话题发布成功")
    finally:
        session.close()


def _can_manage_topic(session, user: User, topic: Topic) -> bool:
    if topic.channel == "official":
        return user.site_role == "operator"
    if topic.organization_id is None:
        return False
    permissions = user_permissions(session, user)
    return str(topic.organization_id) in permissions["publisher_organization_ids"]


@router.patch("/topics/{topic_id}")
def update_topic(topic_id: int, body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        topic = session.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="话题不存在")
        if not _can_manage_topic(session, user, topic):
            raise HTTPException(status_code=403, detail="你没有编辑该话题的权限")
        field_limits = {
            "title": 120,
            "short_title": 60,
            "summary": 600,
            "content": 8000,
            "source_url": 500,
            "cover_url": 500,
        }
        changed: dict[str, Any] = {}
        for field, limit in field_limits.items():
            if field in body:
                value = str(body.get(field) or "").strip()[:limit]
                if field in {"title", "short_title", "summary", "content"} and not value:
                    raise HTTPException(status_code=400, detail=f"{field} 不能为空")
                setattr(topic, field, value or None)
                changed[field] = value
        if "tag_ids" in body:
            tag_ids = [str(item) for item in body.get("tag_ids") or []][:8]
            invalid = validate_tag_ids(session, tag_ids)
            if invalid:
                raise HTTPException(status_code=400, detail=f"包含未收录的标签：{', '.join(invalid)}")
            if not tag_ids:
                raise HTTPException(status_code=400, detail="请至少保留一个标准标签")
            session.query(TopicTag).filter(TopicTag.topic_id == topic.id).delete()
            session.add_all(TopicTag(topic_id=topic.id, tag_id=tag_id) for tag_id in tag_ids)
            changed["tag_ids"] = tag_ids
        if not changed:
            raise HTTPException(status_code=400, detail="没有需要更新的内容")
        session.add(
            AuditLog(
                user_id=user.id,
                action="topic.update",
                target_type="topic",
                target_id=str(topic.id),
                detail=json.dumps({"fields": sorted(changed)}, ensure_ascii=False),
            )
        )
        session.commit()
        return api_ok(topic_to_dict(session, topic, user.id), "话题已更新")
    finally:
        session.close()


@router.post("/topics/{topic_id}/follow")
def toggle_follow(topic_id: int, user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, _ = _current_user(user_id)
    try:
        if not session.get(Topic, topic_id):
            raise HTTPException(status_code=404, detail="话题不存在")
        key = {"topic_id": topic_id, "user_id": int(user_id)}
        existing = session.get(TopicFollow, key)
        if existing:
            session.delete(existing)
            followed = False
        else:
            session.add(TopicFollow(**key))
            followed = True
        session.commit()
        count = session.query(TopicFollow).filter(TopicFollow.topic_id == topic_id).count()
        return api_ok({"followed": followed, "follower_count": count})
    finally:
        session.close()


@router.get("/me/permissions")
def permissions(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        return api_ok(user_permissions(session, user))
    finally:
        session.close()


@router.post("/organizations/applications")
def apply_organization(body: dict[str, Any], user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session, user = _current_user(user_id)
    try:
        if user.auth_status not in {"verified", "organization", "campus_verified"}:
            raise HTTPException(status_code=403, detail="请先完成校园认证")
        name = str(body.get("organization_name") or "").strip()
        org_type = str(body.get("org_type") or "").strip()
        evidence = str(body.get("evidence") or "").strip()
        if not all((name, org_type, evidence)):
            raise HTTPException(status_code=400, detail="请填写组织名称、类型和证明说明")
        application = OrganizationApplication(
            applicant_id=user.id,
            organization_name=name[:100],
            org_type=org_type[:40],
            official_email=str(body.get("official_email") or "").strip()[:120] or None,
            evidence=evidence[:2000],
        )
        session.add(application)
        session.add(
            AuditLog(
                user_id=user.id,
                action="organization.apply",
                target_type="organization_application",
                detail=json.dumps({"organization_name": name}, ensure_ascii=False),
            )
        )
        session.commit()
        return api_ok({"application_id": str(application.id), "status": application.status}, "申请已提交")
    finally:
        session.close()


@router.post("/organizations/applications/{application_id}/review")
def review_organization(
    application_id: int,
    body: dict[str, Any],
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, reviewer = _current_user(user_id)
    try:
        if reviewer.site_role != "operator":
            raise HTTPException(status_code=403, detail="仅平台运营可以审核组织")
        application = session.get(OrganizationApplication, application_id)
        if not application:
            raise HTTPException(status_code=404, detail="组织申请不存在")
        if application.status != "pending":
            raise HTTPException(status_code=409, detail="该申请已经处理")
        decision = str(body.get("decision") or "")
        if decision not in {"approve", "reject"}:
            raise HTTPException(status_code=400, detail="decision 必须是 approve 或 reject")
        now = datetime.datetime.now(datetime.timezone.utc)
        application.status = "approved" if decision == "approve" else "rejected"
        application.reviewed_by = reviewer.id
        application.reviewed_at = now
        organization = None
        if decision == "approve":
            organization = session.execute(
                select(Organization).where(Organization.name == application.organization_name)
            ).scalar_one_or_none()
            if not organization:
                organization = Organization(
                    name=application.organization_name,
                    org_type=application.org_type,
                    verification_status="approved",
                    verified_at=now,
                    expires_at=now + datetime.timedelta(days=365),
                )
                session.add(organization)
                session.flush()
            membership = session.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == organization.id,
                    OrganizationMember.user_id == application.applicant_id,
                )
            ).scalar_one_or_none()
            if not membership:
                session.add(
                    OrganizationMember(
                        organization_id=organization.id,
                        user_id=application.applicant_id,
                        role="owner",
                        status="active",
                        invited_by=reviewer.id,
                        expires_at=organization.expires_at,
                    )
                )
        session.add(
            AuditLog(
                user_id=reviewer.id,
                action=f"organization.{decision}",
                target_type="organization_application",
                target_id=str(application.id),
                detail=json.dumps({"reason": str(body.get("reason") or "")[:500]}, ensure_ascii=False),
            )
        )
        session.commit()
        return api_ok(
            {
                "application_id": str(application.id),
                "status": application.status,
                "organization_id": str(organization.id) if organization else None,
            },
            "审核已完成",
        )
    finally:
        session.close()


@router.post("/organizations/{organization_id}/members")
def grant_organization_role(
    organization_id: int,
    body: dict[str, Any],
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, actor = _current_user(user_id)
    try:
        organization = session.get(Organization, organization_id)
        if not organization or organization.verification_status != "approved":
            raise HTTPException(status_code=404, detail="已认证组织不存在")
        owner = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == actor.id,
                OrganizationMember.role == "owner",
                OrganizationMember.status == "active",
            )
        ).scalar_one_or_none()
        if not owner:
            raise HTTPException(status_code=403, detail="仅组织负责人可以管理成员角色")
        target_user_id = int(body.get("user_id") or 0)
        target = session.get(User, target_user_id)
        if not target:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        role = str(body.get("role") or "member")
        if role not in {"member", "publisher"}:
            raise HTTPException(status_code=400, detail="角色只能是 member 或 publisher")
        status = str(body.get("status") or "active")
        if status not in {"active", "revoked"}:
            raise HTTPException(status_code=400, detail="状态只能是 active 或 revoked")
        membership = session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == target_user_id,
            )
        ).scalar_one_or_none()
        if membership:
            membership.role = role
            membership.status = status
            membership.invited_by = actor.id
            membership.expires_at = organization.expires_at
        else:
            membership = OrganizationMember(
                organization_id=organization_id,
                user_id=target_user_id,
                role=role,
                status=status,
                invited_by=actor.id,
                expires_at=organization.expires_at,
            )
            session.add(membership)
        session.add(
            AuditLog(
                user_id=actor.id,
                action="organization.member_role",
                target_type="user",
                target_id=str(target_user_id),
                detail=json.dumps({"organization_id": organization_id, "role": role, "status": status}),
            )
        )
        session.commit()
        return api_ok({"user_id": str(target_user_id), "role": role, "status": status}, "成员角色已更新")
    finally:
        session.close()
