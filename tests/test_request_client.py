from types import SimpleNamespace

from utils.request_client import client_network_identifier


def _request(headers=None, host="10.0.0.8"):
    return SimpleNamespace(headers=headers or {}, client=SimpleNamespace(host=host))


def test_forwarded_header_is_ignored_without_explicit_proxy_trust(monkeypatch):
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)

    assert client_network_identifier(
        _request({"x-forwarded-for": "203.0.113.42"})
    ) == "10.0.0.8"


def test_first_valid_forwarded_address_is_used_for_trusted_proxy(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")

    assert client_network_identifier(
        _request({"x-forwarded-for": "203.0.113.42, 10.0.0.8"})
    ) == "203.0.113.42"


def test_invalid_forwarded_address_falls_back_to_direct_peer(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "true")

    assert client_network_identifier(
        _request({"x-forwarded-for": "not-an-ip"})
    ) == "10.0.0.8"
