from __future__ import annotations

import ipaddress
import os

from fastapi import Request


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def client_network_identifier(request: Request) -> str:
    direct_peer = request.client.host if request.client else ""
    if not _enabled("TRUST_PROXY_HEADERS"):
        return direct_peer

    forwarded = request.headers.get("x-forwarded-for", "")
    candidate = forwarded.split(",", 1)[0].strip()
    if not candidate:
        return direct_peer
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return direct_peer
