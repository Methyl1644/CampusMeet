from __future__ import annotations

import datetime
import re


_DATE_ONLY = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_ZONED_DATETIME = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ][0-9]{2}:[0-9]{2}"
    r"(?::[0-9]{2}(?:\.[0-9]{1,6})?)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)


def parse_deadline_at(value: object) -> datetime.datetime | None:
    raw = str(value or "").strip()
    try:
        if _DATE_ONLY.fullmatch(raw):
            parsed_date = datetime.date.fromisoformat(raw)
            return datetime.datetime.combine(
                parsed_date,
                datetime.time.max,
                tzinfo=datetime.timezone.utc,
            )
        if not _ZONED_DATETIME.fullmatch(raw):
            return None
        parsed = datetime.datetime.fromisoformat(
            raw.replace("Z", "+00:00").replace("z", "+00:00")
        )
    except ValueError:
        return None
    return parsed.astimezone(datetime.timezone.utc)


def ensure_deadline_utc(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)
