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
    return f"https://www.google.com/maps?q={lat},{lng}"


def _location_block(location: dict) -> str:
    maps_url = _maps_link(location["lat"], location["lng"], location["name"])
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
      <tr>
        <td style="background:#f8fffe;border:1px solid #d1fae5;border-left:4px solid #10b981;
                   border-radius:8px;padding:18px 20px;">
          <p style="margin:0 0 2px;font-size:11px;font-weight:700;letter-spacing:1.2px;
                    color:#6b7280;text-transform:uppercase;">Meeting Location</p>
          <p style="margin:4px 0 2px;font-size:16px;font-weight:700;color:#064e3b;">
            {location['name']}
          </p>
          <p style="margin:0 0 14px;font-size:13px;color:#6b7280;line-height:1.5;">
            {location['address']}
          </p>
          <a href="{maps_url}" target="_blank"
             style="display:inline-block;background:#10b981;color:#ffffff;
                    padding:9px 20px;border-radius:6px;text-decoration:none;
                    font-size:12px;font-weight:700;letter-spacing:0.5px;">
            ↗ Open in Google Maps
          </a>
        </td>
      </tr>
    </table>
    """


def _otp_block(otp: str) -> str:
    digits = "".join(
        f'<span class="otp-digit" style="display:inline-block;background:#1e40af;color:#fff;'
        f'font-size:20px;font-weight:800;width:36px;height:42px;line-height:42px;'
        f'text-align:center;border-radius:6px;margin:0 3px;">{d}</span>'
        for d in otp
    )
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0;">
      <tr>
        <td style="background:#eff6ff;border:1px solid #bfdbfe;border-left:4px solid #3b82f6;
                   border-radius:8px;padding:16px 12px;text-align:center;">
          <p style="margin:0 0 12px;font-size:10px;font-weight:700;letter-spacing:1.2px;
                    color:#6b7280;text-transform:uppercase;">Your One-Time Passcode</p>
          <div style="white-space:nowrap;margin:0 0 12px;">{digits}</div>
          <p style="margin:0;font-size:12px;color:#6b7280;">
            Present this code at reception upon arrival.
          </p>
        </td>
      </tr>
    </table>
    """


def _info_row(label: str, value: str) -> str:
    return f"""
    <tr class="info-row">
      <td class="info-label" style="padding:8px 0 4px;border-bottom:1px solid #f3f4f6;width:90px;
                 min-width:90px;font-size:10px;font-weight:700;letter-spacing:0.6px;
                 color:#9ca3af;text-transform:uppercase;vertical-align:top;">
        {label}
      </td>
      <td class="info-value" style="padding:8px 0 8px 8px;border-bottom:1px solid #f3f4f6;
                 font-size:13px;color:#111827;vertical-align:top;word-break:break-word;">
        {value or '—'}
      </td>
    </tr>
    """


_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>VisitorVault</title>
  <style>
    @media only screen and (max-width:480px) {{
      .email-outer-pad {{ padding: 12px 8px !important; }}
      .email-body-pad  {{ padding: 22px 16px !important; }}
      .email-footer-pad {{ padding: 12px 16px !important; }}
      .header-right {{ display: none !important; }}
      .info-row td {{ display: block !important; width: 100% !important; }}
      .info-label {{ padding-bottom: 1px !important; border-bottom: none !important; }}
      .info-value {{ padding-top: 0 !important; padding-left: 0 !important; }}
      .otp-digit {{ width:28px !important; height:34px !important; line-height:34px !important; font-size:16px !important; margin:0 2px !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" class="email-outer-pad"
         style="background:#f1f5f9;padding:32px 16px;">
    <tr>
      <td align="center">
        <table cellpadding="0" cellspacing="0"
               style="max-width:560px;width:100%;background:#ffffff;
                      border-radius:12px;overflow:hidden;
                      border:1px solid #e2e8f0;
                      box-shadow:0 4px 24px rgba(0,0,0,0.06);">

          <!-- Header -->
          <tr>
            <td style="background:#0f172a;padding:0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:20px 24px;">
                    <table cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="background:#c0283c;width:4px;border-radius:2px;">&nbsp;</td>
                        <td style="padding-left:12px;">
                          <p style="margin:0;font-size:17px;font-weight:800;
                                    letter-spacing:-0.3px;color:#f8fafc;">VisitorVault</p>
                          <p style="margin:2px 0 0;font-size:10px;font-weight:500;
                                    letter-spacing:1.5px;color:#64748b;text-transform:uppercase;">
                            Visitor Management System
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td class="header-right" style="padding:20px 24px;text-align:right;">
                    <p style="margin:0;font-size:11px;color:#334155;
                               letter-spacing:0.4px;white-space:nowrap;">Automated Notification</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Accent bar -->
          <tr>
            <td style="background:linear-gradient(90deg,#c0283c 0%,#9b1c2e 100%);
                       height:3px;font-size:0;line-height:0;">&nbsp;</td>
          </tr>

          <!-- Body -->
          <tr>
            <td class="email-body-pad" style="padding:28px 24px;">
              {body}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td class="email-footer-pad"
                style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:14px 24px;">
              <p style="margin:0;font-size:11px;color:#94a3b8;line-height:1.6;">
                Automated message from <strong style="color:#64748b;">VisitorVault VMS</strong>.
                Please do not reply. &nbsp;&copy; VisitorVault
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


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
    <!-- Badge -->
    <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td style="background:#fef3c7;border:1px solid #fde68a;border-radius:20px;
                   padding:5px 14px;font-size:11px;font-weight:700;
                   color:#92400e;letter-spacing:0.8px;text-transform:uppercase;">
          ● Awaiting Your Approval
        </td>
      </tr>
    </table>

    <h2 style="margin:0 0 6px;font-size:22px;font-weight:800;
               color:#0f172a;letter-spacing:-0.5px;">
      New Visitor Request
    </h2>
    <p style="margin:0 0 28px;font-size:14px;color:#64748b;line-height:1.6;">
      Hi <strong style="color:#0f172a;">{employee_name}</strong>,
      someone has arrived and is waiting for your approval.
    </p>

    <!-- Visitor card -->
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:#f8fafc;border:1px solid #e2e8f0;
                  border-radius:10px;margin-bottom:28px;">
      <tr>
        <td style="padding:20px 24px;">
          <p style="margin:0 0 14px;font-size:11px;font-weight:700;
                    letter-spacing:1.2px;color:#94a3b8;text-transform:uppercase;">
            Visitor Details
          </p>
          <table width="100%" cellpadding="0" cellspacing="0">
            {_info_row("Name", visitor_name)}
            {_info_row("Phone", visitor_phone)}
            {_info_row("Email", visitor_email)}
            {_info_row("Purpose", purpose)}
          </table>
        </td>
      </tr>
    </table>

    <!-- CTA -->
    <table cellpadding="0" cellspacing="0">
      <tr>
        <td style="background:#c0283c;border-radius:8px;">
          <a href="{app_url}/dashboard/notifications"
             style="display:inline-block;padding:13px 28px;color:#ffffff;
                    text-decoration:none;font-size:14px;font-weight:700;
                    letter-spacing:0.3px;">
            Review &amp; Approve Visit →
          </a>
        </td>
      </tr>
    </table>

    <p style="margin:24px 0 0;font-size:12px;color:#94a3b8;line-height:1.6;">
      Or log in to your dashboard at
      <a href="{app_url}" style="color:#c0283c;text-decoration:none;">{app_url}</a>
      to manage this request.
    </p>
    """
    await _send(
        to=employee_email,
        subject=f"[VMS] Visitor Waiting: {visitor_name} is here to see you",
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
    otp_section = _otp_block(otp) if otp else f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0;">
      <tr>
        <td style="background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #22c55e;
                   border-radius:8px;padding:14px 20px;">
          <p style="margin:0;font-size:13px;font-weight:600;color:#166534;">
            ✓ &nbsp;No OTP required — proceed directly to the meeting location.
          </p>
        </td>
      </tr>
    </table>
    """

    body = f"""
    <!-- Badge -->
    <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td style="background:#dcfce7;border:1px solid #bbf7d0;border-radius:20px;
                   padding:5px 14px;font-size:11px;font-weight:700;
                   color:#166534;letter-spacing:0.8px;text-transform:uppercase;">
          ✓ Visit Approved
        </td>
      </tr>
    </table>

    <h2 style="margin:0 0 6px;font-size:22px;font-weight:800;
               color:#0f172a;letter-spacing:-0.5px;">
      You're all set!
    </h2>
    <p style="margin:0 0 6px;font-size:14px;color:#64748b;line-height:1.6;">
      Hi <strong style="color:#0f172a;">{visitor_name}</strong>,
      your visit has been confirmed by
      <strong style="color:#0f172a;">{employee_name}</strong>.
    </p>
    <p style="margin:0 0 4px;font-size:13px;color:#94a3b8;">
      Please find your meeting details below.
    </p>

    {_location_block(location)}
    {otp_section}

    <p style="margin:8px 0 0;font-size:12px;color:#94a3b8;line-height:1.6;">
      Please present this email or your OTP at the front desk upon arrival.
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
    <!-- Badge -->
    <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td style="background:#fef2f2;border:1px solid #fecaca;border-radius:20px;
                   padding:5px 14px;font-size:11px;font-weight:700;
                   color:#991b1b;letter-spacing:0.8px;text-transform:uppercase;">
          Visit Unavailable
        </td>
      </tr>
    </table>

    <h2 style="margin:0 0 6px;font-size:22px;font-weight:800;
               color:#0f172a;letter-spacing:-0.5px;">
      Visit Request Update
    </h2>
    <p style="margin:0 0 20px;font-size:14px;color:#64748b;line-height:1.6;">
      Hi <strong style="color:#0f172a;">{visitor_name}</strong>,
      unfortunately <strong style="color:#0f172a;">{employee_name}</strong>
      is unavailable to meet at this time.
    </p>

    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="background:#fef2f2;border:1px solid #fecaca;border-left:4px solid #ef4444;
                   border-radius:8px;padding:16px 20px;">
          <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#991b1b;">
            What you can do next
          </p>
          <p style="margin:0;font-size:13px;color:#64748b;line-height:1.6;">
            Please reach out to <strong>{employee_name}</strong> directly to reschedule
            your visit at a more suitable time.
          </p>
        </td>
      </tr>
    </table>

    <p style="margin:28px 0 0;font-size:12px;color:#94a3b8;line-height:1.6;">
      We apologize for any inconvenience. Thank you for using VisitorVault.
    </p>
    """
    await _send(
        to=visitor_email,
        subject=f"[VMS] Visit Request — Update from {employee_name}",
        html=_BASE.format(body=body),
    )