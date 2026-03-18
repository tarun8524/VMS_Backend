"""
Email service — uses aiosmtplib for async SMTP.
Falls back gracefully if SMTP is not configured (logs instead of crashing).
"""
import logging
import random
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


def _configured() -> bool:
    return bool(settings.SMTP_USER and settings.SMTP_PASSWORD and settings.EMAIL_FROM)


async def _send(to: str, subject: str, html: str) -> None:
    if not _configured():
        logger.warning("SMTP not configured — skipping email to %s | Subject: %s", to, subject)
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("Email sent to %s | %s", to, subject)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, exc)


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


# ── Template helpers ──────────────────────────────────────────────────────────

def _maps_link(lat: str, lng: str, label: str) -> str:
    """Return a Google Maps URL for given coordinates."""
    return f"https://www.google.com/maps?q={lat},{lng}"


def _location_block(location: dict) -> str:
    maps_url = _maps_link(location["lat"], location["lng"], location["name"])
    return f"""
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px 18px;margin:12px 0;">
      <p style="margin:0 0 6px;font-weight:600;color:#166534;">📍 Meeting Location</p>
      <p style="margin:0 0 4px;font-size:15px;color:#15803d;font-weight:700;">{location['name']}</p>
      <p style="margin:0 0 8px;font-size:13px;color:#4b5563;">{location['address']}</p>
      <a href="{maps_url}" target="_blank"
         style="display:inline-block;background:#16a34a;color:#fff;padding:8px 18px;
                border-radius:7px;text-decoration:none;font-size:13px;font-weight:600;">
        🗺 Open in Google Maps
      </a>
    </div>
    """


def _otp_block(otp: str) -> str:
    return f"""
    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 18px;margin:12px 0;text-align:center;">
      <p style="margin:0 0 6px;font-weight:600;color:#1e40af;">🔐 Visitor OTP</p>
      <p style="font-size:32px;font-weight:800;letter-spacing:8px;color:#1d4ed8;margin:4px 0;">{otp}</p>
      <p style="font-size:12px;color:#6b7280;margin:6px 0 0;">Share this OTP with the visitor at reception</p>
    </div>
    """


_BASE = """
<!DOCTYPE html>
<html>
<body style="font-family:system-ui,-apple-system,sans-serif;background:#f9fafb;margin:0;padding:24px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;
              border:1px solid #e5e7eb;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
    <!-- Header -->
    <div style="background:#c0283c;padding:24px 28px;">
      <h1 style="color:#fff;margin:0;font-size:20px;">VisitorVault</h1>
      <p style="color:#fecaca;margin:4px 0 0;font-size:13px;">Visitor Management System</p>
    </div>
    <!-- Body -->
    <div style="padding:28px;">
      {body}
    </div>
    <!-- Footer -->
    <div style="background:#f3f4f6;padding:14px 28px;font-size:12px;color:#9ca3af;text-align:center;">
      This is an automated message from VisitorVault VMS. Please do not reply.
    </div>
  </div>
</body>
</html>
"""


# ── Public API ────────────────────────────────────────────────────────────────

async def send_new_visit_notification(
    employee_email: str,
    employee_name: str,
    visitor_name: str,
    visitor_phone: str,
    visitor_email: str,
    purpose: str,
    app_url: str,
) -> None:
    """Notify employee that a visitor is waiting for their approval."""
    body = f"""
    <h2 style="color:#111827;margin:0 0 4px;">New Visitor Request 🔔</h2>
    <p style="color:#6b7280;margin:0 0 20px;">Hi {employee_name}, someone is here to visit you.</p>

    <div style="background:#fafafa;border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin:0 0 16px;">
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr><td style="color:#6b7280;padding:4px 0;width:110px;">Name</td>
            <td style="color:#111827;font-weight:600;">{visitor_name}</td></tr>
        <tr><td style="color:#6b7280;padding:4px 0;">Phone</td>
            <td style="color:#111827;">{visitor_phone}</td></tr>
        <tr><td style="color:#6b7280;padding:4px 0;">Email</td>
            <td style="color:#111827;">{visitor_email}</td></tr>
        <tr><td style="color:#6b7280;padding:4px 0;">Purpose</td>
            <td style="color:#111827;">{purpose or '—'}</td></tr>
      </table>
    </div>

    <a href="{app_url}/dashboard/notifications"
       style="display:inline-block;background:#c0283c;color:#fff;padding:12px 24px;
              border-radius:9px;text-decoration:none;font-weight:600;font-size:14px;">
      Review &amp; Approve →
    </a>
    <p style="margin:20px 0 0;font-size:13px;color:#9ca3af;">
      Please approve or reject this visit request from your dashboard.
    </p>
    """
    await _send(
        to=employee_email,
        subject=f"[VMS] New visitor: {visitor_name} is waiting for you",
        html=_BASE.format(body=body),
    )


async def send_approval_to_visitor(
    visitor_email: str,
    visitor_name: str,
    employee_name: str,
    location: dict,
    otp: str | None,
) -> None:
    """Send approval confirmation + meeting location (+ optional OTP) to visitor."""
    otp_section = _otp_block(otp) if otp else """
    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
                padding:12px 18px;margin:12px 0;font-size:13px;color:#166534;font-weight:600;">
      ✅ No OTP required — please proceed directly to the meeting location.
    </div>
    """
    body = f"""
    <h2 style="color:#111827;margin:0 0 4px;">Your Visit is Approved! ✅</h2>
    <p style="color:#6b7280;margin:0 0 20px;">
      Hi {visitor_name}, <strong>{employee_name}</strong> has approved your visit.
    </p>

    {_location_block(location)}
    {otp_section}

    <p style="margin:20px 0 0;font-size:13px;color:#9ca3af;">
      Please show this email (or the OTP) at reception when you arrive.
    </p>
    """
    await _send(
        to=visitor_email,
        subject=f"[VMS] Visit Approved — Meeting with {employee_name}",
        html=_BASE.format(body=body),
    )


async def send_rejection_to_visitor(
    visitor_email: str,
    visitor_name: str,
    employee_name: str,
) -> None:
    """Notify visitor their request was rejected."""
    body = f"""
    <h2 style="color:#111827;margin:0 0 4px;">Visit Request Update</h2>
    <p style="color:#6b7280;margin:0 0 20px;">
      Hi {visitor_name}, unfortunately <strong>{employee_name}</strong>
      is unable to meet you at this time.
    </p>
    <p style="color:#6b7280;font-size:13px;">
      Please contact the employee directly to reschedule if needed.
    </p>
    """
    await _send(
        to=visitor_email,
        subject=f"[VMS] Visit Request — Update from {employee_name}",
        html=_BASE.format(body=body),
    )
