"""Verification email delivery for production and local development."""
import json
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def _get_brevo_config() -> dict | None:
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv("BREVO_FROM_EMAIL", "").strip()
    if not api_key or not sender_email:
        return None
    return {
        "api_key": api_key,
        "sender_email": sender_email,
        "sender_name": os.getenv("BREVO_FROM_NAME", "CampusMate").strip()
        or "CampusMate",
        "base_url": os.getenv(
            "BREVO_API_BASE_URL", "https://api.brevo.com/v3"
        ).strip().rstrip("/"),
    }


def _get_resend_config() -> dict | None:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    sender = os.getenv("RESEND_FROM_EMAIL", "").strip()
    if not api_key or not sender:
        return None
    return {
        "api_key": api_key,
        "sender": sender,
        "base_url": os.getenv(
            "RESEND_API_BASE_URL", "https://api.resend.com"
        ).strip().rstrip("/"),
    }


def _get_smtp_config() -> dict | None:
    """从环境变量读取 SMTP 配置"""
    host = os.getenv("SMTP_HOST", "").strip()
    port = os.getenv("SMTP_PORT", "465").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_SENDER", user).strip()

    if not host or not user or not password:
        return None

    return {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "sender": sender,
    }


def is_email(account: str) -> bool:
    """判断账号是否为邮箱"""
    return "@" in account


def _build_verification_content(code: str, purpose: str) -> tuple[str, str, str]:
    subject = f"CampusMate AI - {purpose}验证码"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4F46E5;">CampusMate AI</h2>
        <p>您好！</p>
        <p>您的{purpose}验证码为：</p>
        <div style="font-size: 32px; font-weight: bold; color: #4F46E5; text-align: center;
                    padding: 20px; background: #F3F4F6; border-radius: 8px; letter-spacing: 4px;">
            {code}
        </div>
        <p style="color: #6B7280; font-size: 14px;">验证码 10 分钟内有效，请勿泄露给他人。</p>
        <p style="color: #9CA3AF; font-size: 12px;">如非本人操作，请忽略此邮件。</p>
    </div>
    """
    text_body = f"CampusMate AI {purpose}验证码: {code} (10分钟内有效)"
    return subject, html_body, text_body


def _send_with_resend(
    config: dict,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> dict:
    payload = json.dumps(
        {
            "from": config["sender"],
            "to": [to_email],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"{config['base_url']}/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            response.read()
        logger.info("Verification email sent through Resend to %s", to_email)
        return {"sent": True, "message": f"验证码已发送至 {to_email}"}
    except Exception as error:
        logger.error("Resend verification email failed: %s", error)
        return {"sent": False, "message": "验证码邮件发送失败，请稍后重试"}


def _send_with_brevo(
    config: dict,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> dict:
    payload = json.dumps(
        {
            "sender": {
                "email": config["sender_email"],
                "name": config["sender_name"],
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_body,
            "textContent": text_body,
            "tags": ["campusmate-verification"],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"{config['base_url']}/smtp/email",
        data=payload,
        method="POST",
        headers={
            "api-key": config["api_key"],
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            response.read()
        logger.info("Verification email sent through Brevo to %s", to_email)
        return {"sent": True, "message": f"验证码已发送至 {to_email}"}
    except Exception as error:
        logger.error("Brevo verification email failed: %s", error)
        return {"sent": False, "message": "验证码邮件发送失败，请稍后重试"}


def send_verification_email(to_email: str, code: str, purpose: str = "注册") -> dict:
    """
    发送验证码邮件
    返回: {"sent": bool, "message": str, "code": str(仅未发送时返回)}
    """
    subject, html_body, text_body = _build_verification_content(code, purpose)
    brevo_config = _get_brevo_config()
    if brevo_config:
        return _send_with_brevo(
            brevo_config, to_email, subject, html_body, text_body
        )

    resend_config = _get_resend_config()
    if resend_config:
        return _send_with_resend(
            resend_config, to_email, subject, html_body, text_body
        )

    config = _get_smtp_config()
    if not config:
        # SMTP 未配置，降级返回验证码
        logger.info("SMTP not configured, returning code directly for testing")
        return {
            "sent": True,
            "message": f"验证码已发送至 {to_email}（SMTP未配置，测试模式直接返回）",
            "code": code,
        }

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["sender"]
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        port = config["port"]
        if port == 465:
            server = smtplib.SMTP_SSL(config["host"], port, timeout=15)
        else:
            server = smtplib.SMTP(config["host"], port, timeout=15)
            server.starttls()

        server.login(config["user"], config["password"])
        server.sendmail(config["sender"], [to_email], msg.as_string())
        server.quit()

        logger.info(f"Verification email sent to {to_email}")
        return {"sent": True, "message": f"验证码已发送至 {to_email}"}
    except Exception as e:
        logger.error(f"Send email failed: {e}")
        if os.getenv("AUTH_TEST_MODE", "true").strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return {"sent": False, "message": "验证码邮件发送失败，请稍后重试"}
        return {
            "sent": True,
            "message": f"邮件发送失败，验证码为: {code}（请手动告知用户）",
            "code": code,
        }
