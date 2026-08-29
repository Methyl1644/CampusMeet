"""邮件发送工具

通过 SMTP 发送验证码邮件。
未配置 SMTP 时自动降级（返回验证码供测试）。
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


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


def send_verification_email(to_email: str, code: str, purpose: str = "注册") -> dict:
    """
    发送验证码邮件
    返回: {"sent": bool, "message": str, "code": str(仅未发送时返回)}
    """
    config = _get_smtp_config()
    if not config:
        # SMTP 未配置，降级返回验证码
        logger.info("SMTP not configured, returning code directly for testing")
        return {
            "sent": True,
            "message": f"验证码已发送至 {to_email}（SMTP未配置，测试模式直接返回）",
            "code": code,
        }

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
        # 发送失败，降级返回验证码
        return {
            "sent": True,
            "message": f"邮件发送失败，验证码为: {code}（请手动告知用户）",
            "code": code,
        }
