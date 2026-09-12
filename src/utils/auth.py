"""认证工具：密码哈希与 JWT 令牌管理"""
import hashlib
import os
import time
import json
import secrets
import logging

logger = logging.getLogger(__name__)

# JWT 简易实现（不依赖外部 JWT 库的复杂配置）
# 使用 HMAC-SHA256 签名

def _get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "campusmate_default_secret_2026")


def _b64encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64decode(s: str) -> bytes:
    import base64
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 哈希密码"""
    salt = secrets.token_hex(16)
    iterations = 100000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """验证密码"""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4:
            return False
        algorithm, iterations, salt, hash_val = parts
        if algorithm != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return dk.hex() == hash_val
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_token(
    user_id: int,
    expire_seconds: int = 86400,
    token_id: str | None = None,
) -> str:
    """生成带唯一会话标识的短期 JWT token。"""
    import hmac
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expire_seconds,
        "jti": token_id or secrets.token_urlsafe(24),
    }
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        _get_jwt_secret().encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_token(token: str) -> dict | None:
    """验证 JWT token，返回 payload 或 None"""
    import hmac
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            _get_jwt_secret().encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_sig = _b64decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64decode(payload_b64))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def generate_verification_code() -> str:
    """生成6位验证码"""
    return f"{secrets.randbelow(1000000):06d}"
