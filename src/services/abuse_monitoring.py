from __future__ import annotations

import datetime
import hashlib
import hmac
import os
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from storage.database.models.abuse import AbuseEvent


@dataclass(frozen=True)
class AbuseDecision:
    action: str
    reason_code: str | None = None
    retry_after_seconds: int = 0


def _digest(namespace: str, value: str) -> str | None:
    normalized = " ".join(str(value or "").casefold().split())
    if not normalized:
        return None
    secret = os.getenv("ABUSE_HASH_SECRET") or os.getenv("JWT_SECRET") or "campusmate-local-abuse"
    payload = f"{namespace}:{normalized}".encode("utf-8")
    return "sha256$" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _count(
    session: Session,
    *,
    event_type: str,
    since: datetime.datetime,
    user_id: int | None = None,
    network_hash: str | None = None,
    fingerprint: str | None = None,
) -> int:
    filters = [AbuseEvent.event_type == event_type, AbuseEvent.created_at >= since]
    if user_id is not None:
        filters.append(AbuseEvent.user_id == user_id)
    if network_hash is not None:
        filters.append(AbuseEvent.network_hash == network_hash)
    if fingerprint is not None:
        filters.append(AbuseEvent.content_fingerprint == fingerprint)
    return int(session.scalar(select(func.count()).select_from(AbuseEvent).where(*filters)) or 0)


def _decision(
    session: Session,
    *,
    user_id: int | None,
    event_type: str,
    fingerprint: str | None,
    network_hash: str | None,
    now: datetime.datetime,
) -> AbuseDecision:
    if event_type == "contact_bypass":
        count = _count(
            session,
            event_type=event_type,
            user_id=user_id,
            since=now - datetime.timedelta(minutes=30),
        )
        if count >= 2:
            return AbuseDecision("review", "contact_bypass_repeated")
        if count == 1:
            return AbuseDecision("cooldown", "contact_bypass_repeated", 300)
        return AbuseDecision("warn", "contact_bypass")

    if event_type == "application":
        count = _count(
            session,
            event_type=event_type,
            user_id=user_id,
            since=now - datetime.timedelta(minutes=10),
        )
        if count >= 8:
            return AbuseDecision("cooldown", "rapid_applications", 600)
        if count == 7:
            return AbuseDecision("warn", "rapid_applications")

    if event_type in {"message", "post"} and fingerprint:
        count = _count(
            session,
            event_type=event_type,
            user_id=user_id,
            fingerprint=fingerprint,
            since=now - datetime.timedelta(minutes=5),
        )
        if count >= 3:
            return AbuseDecision("cooldown", f"repeated_{event_type}", 300)
        if count == 2:
            return AbuseDecision("warn", f"repeated_{event_type}")

    if event_type == "verification_code":
        counts = []
        if network_hash:
            counts.append(
                _count(
                    session,
                    event_type=event_type,
                    network_hash=network_hash,
                    since=now - datetime.timedelta(minutes=10),
                )
            )
        if fingerprint:
            counts.append(
                _count(
                    session,
                    event_type=event_type,
                    fingerprint=fingerprint,
                    since=now - datetime.timedelta(minutes=10),
                )
            )
        if counts and max(counts) >= 5:
            return AbuseDecision("cooldown", "verification_burst", 600)

    if event_type == "registration" and network_hash:
        count = _count(
            session,
            event_type=event_type,
            network_hash=network_hash,
            since=now - datetime.timedelta(minutes=10),
        )
        if count >= 5:
            return AbuseDecision("cooldown", "registration_burst", 600)

    return AbuseDecision("allow")


def check_and_record(
    session: Session,
    *,
    user_id: int | None,
    event_type: str,
    target_id: str | None = None,
    content: str = "",
    network_identifier: str = "",
    now: datetime.datetime | None = None,
) -> AbuseDecision:
    current = now or datetime.datetime.now(datetime.timezone.utc)
    fingerprint = _digest("content", content)
    network_hash = _digest("network", network_identifier)
    decision = _decision(
        session,
        user_id=user_id,
        event_type=event_type,
        fingerprint=fingerprint,
        network_hash=network_hash,
        now=current,
    )
    session.add(
        AbuseEvent(
            user_id=user_id,
            event_type=event_type,
            target_id=str(target_id)[:120] if target_id else None,
            content_fingerprint=fingerprint,
            network_hash=network_hash,
            outcome=decision.action,
            created_at=current,
        )
    )
    return decision
