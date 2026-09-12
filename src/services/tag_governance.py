import datetime
import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.content import normalize_text
from storage.database.models import AuditLog, Tag, TagAlias, TagProposal, User


TAG_CATEGORIES = frozenset({"activity", "skill", "role", "level", "audience"})
VERIFIED_STATUSES = frozenset({"verified", "organization", "campus_verified"})


def sanitize_unknown_concepts(value) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    clean: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        category = str(item.get("category") or "").strip().lower()
        reason = str(item.get("reason") or "").strip()[:200]
        normalized = normalize_text(name)
        if category not in TAG_CATEGORIES or not 2 <= len(name) <= 30 or not 2 <= len(normalized) <= 40:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        clean.append({"name": name, "category": category, "reason": reason})
    return clean


def _matching_active_tag(session: Session, normalized_name: str) -> Tag | None:
    for tag in session.execute(select(Tag).where(Tag.active.is_(True))).scalars():
        if normalize_text(tag.canonical_name) == normalized_name:
            return tag
    alias = session.execute(
        select(TagAlias).where(
            TagAlias.normalized_alias == normalized_name,
            TagAlias.active.is_(True),
        )
    ).scalar_one_or_none()
    return session.get(Tag, alias.tag_id) if alias else None


def _validate_proposal(name: str, category: str, source_text: str) -> tuple[str, str, str]:
    clean_name = name.strip()
    clean_category = category.strip().lower()
    clean_source = source_text.strip()
    normalized = normalize_text(clean_name)
    if clean_category not in TAG_CATEGORIES:
        raise ValueError("标签分类不正确")
    if not 2 <= len(clean_name) <= 30 or not 2 <= len(normalized) <= 40:
        raise ValueError("候选标签名称应为 2 至 30 个字符")
    if re.search(r"https?://|www\.", clean_name, re.IGNORECASE):
        raise ValueError("候选标签不能是网址")
    if not clean_source:
        raise ValueError("请提供产生该候选标签的原始需求")
    return clean_name, clean_category, clean_source[:500]


def submit_tag_proposal(
    session: Session,
    user: User,
    name: str,
    category: str,
    source_text: str,
    suggested_tag_id: str | None = None,
) -> TagProposal:
    if user.auth_status not in VERIFIED_STATUSES:
        raise PermissionError("请先完成校园认证")
    clean_name, clean_category, clean_source = _validate_proposal(name, category, source_text)
    normalized = normalize_text(clean_name)
    if _matching_active_tag(session, normalized):
        raise ValueError("该概念已有标准标签或别名")
    suggested = session.get(Tag, suggested_tag_id) if suggested_tag_id else None
    if suggested_tag_id and (not suggested or not suggested.active):
        raise ValueError("建议合并的标准标签不存在")

    proposal = session.execute(
        select(TagProposal).where(TagProposal.normalized_name == normalized)
    ).scalar_one_or_none()
    if proposal:
        proposal.occurrence_count += 1
        proposal.source_text = clean_source
        if suggested:
            proposal.suggested_tag_id = suggested.id
        session.flush()
        return proposal

    proposal = TagProposal(
        normalized_name=normalized,
        proposed_name=clean_name,
        category=clean_category,
        source_text=clean_source,
        suggested_tag_id=suggested.id if suggested else None,
        submitted_by=user.id,
    )
    session.add(proposal)
    session.flush()
    session.add(
        AuditLog(
            user_id=user.id,
            action="tag_proposal.submit",
            target_type="tag_proposal",
            target_id=str(proposal.id),
            detail=json.dumps({"name": clean_name, "category": clean_category}, ensure_ascii=False),
        )
    )
    return proposal


def review_tag_proposal(
    session: Session,
    reviewer: User,
    proposal: TagProposal,
    decision: str,
    target_tag_id: str | None = None,
    canonical_name: str | None = None,
    reason: str = "",
) -> Tag | None:
    from services.operators import has_platform_role

    if not has_platform_role(session, reviewer):
        raise PermissionError("仅平台运营可以审核候选标签")
    if proposal.status != "pending":
        raise ValueError("该候选标签已经处理")
    if decision not in {"approve", "merge", "reject"}:
        raise ValueError("审核决定不正确")

    result: Tag | None = None
    if decision == "approve":
        clean_name, clean_category, _ = _validate_proposal(
            canonical_name or proposal.proposed_name,
            proposal.category,
            proposal.source_text,
        )
        normalized = normalize_text(clean_name)
        if _matching_active_tag(session, normalized):
            raise ValueError("标准标签或别名已经存在，请选择合并")
        result = Tag(
            id=f"{clean_category}_{uuid.uuid4().hex[:12]}",
            canonical_name=clean_name,
            category=clean_category,
            display_color="gray",
            active=True,
            sort_order=9000,
        )
        session.add(result)
        session.flush()
        if normalized != proposal.normalized_name:
            session.add(
                TagAlias(
                    tag_id=result.id,
                    normalized_alias=proposal.normalized_name,
                    source="proposal",
                )
            )
        proposal.suggested_tag_id = result.id
    elif decision == "merge":
        result = session.get(Tag, target_tag_id) if target_tag_id else None
        if not result or not result.active:
            raise ValueError("合并目标标签不存在或已停用")
        alias = session.execute(
            select(TagAlias).where(TagAlias.normalized_alias == proposal.normalized_name)
        ).scalar_one_or_none()
        if alias:
            alias.tag_id = result.id
            alias.active = True
            alias.source = "proposal"
        else:
            session.add(
                TagAlias(
                    tag_id=result.id,
                    normalized_alias=proposal.normalized_name,
                    source="proposal",
                )
            )
        proposal.suggested_tag_id = result.id

    now = datetime.datetime.now(datetime.timezone.utc)
    proposal.status = {"approve": "approved", "merge": "merged", "reject": "rejected"}[decision]
    proposal.reviewed_by = reviewer.id
    proposal.reviewed_at = now
    proposal.review_reason = reason.strip()[:500] or None
    session.add(
        AuditLog(
            user_id=reviewer.id,
            action=f"tag_proposal.{decision}",
            target_type="tag_proposal",
            target_id=str(proposal.id),
            detail=json.dumps(
                {"target_tag_id": result.id if result else None, "reason": proposal.review_reason},
                ensure_ascii=False,
            ),
        )
    )
    session.flush()
    return result
