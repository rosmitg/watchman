"""Transactional email delivery for daily portfolio briefs (via Resend).

Sending is best-effort / fire-and-forget: ``send_brief_email_for_user`` never
raises, so a failed email can never roll back or block a brief that has already
been generated and saved.
"""
import logging
from html import escape
from typing import Optional

import httpx

from app.core.config import settings
from app.models.state import Brief

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
# Resend's shared sandbox sender — works without a verified custom domain.
EMAIL_SENDER = "Watchman <onboarding@resend.dev>"
# Where the email's CTA sends the user (the STK frontend).
STK_FRONTEND_URL = "https://stk-frontend-512165788990.australia-southeast1.run.app"

# STK dark theme palette (frontend-react/src/index.css).
_BG = "#0A0A0F"
_CARD = "#1E1E2E"
_BORDER = "#2A2A3E"
_GREEN = "#00D084"
_GREEN_LIGHT = "#00E896"
_TEXT = "#E0E6F0"
_MUTED = "#8B8FA8"
_RED = "#FF4757"
_AMBER = "#FBBF24"

# Max characters of a section body shown in the email summary.
_SECTION_BODY_LIMIT = 320


def _health_color(score: int) -> str:
    """Traffic-light colour for the portfolio health score."""
    if score >= 66:
        return _GREEN
    if score >= 33:
        return _AMBER
    return _RED


def _truncate(text: str, limit: int = _SECTION_BODY_LIMIT) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip() + "…"


async def get_user_email(user_id: str) -> Optional[str]:
    """Look up a user's email from STK's Supabase auth via the admin API.

    Brief recipients are STK users, whose auth records live in STK's Supabase
    project (separate from Watchman's own Supabase), so this uses
    STK_SUPABASE_URL + STK_SUPABASE_SERVICE_ROLE_KEY (service role required for
    the admin endpoint). Returns None if unconfigured, the user is unknown, or
    the lookup fails — callers treat that as "skip email".
    """
    if not settings.STK_SUPABASE_URL or not settings.STK_SUPABASE_SERVICE_ROLE_KEY:
        logger.warning(
            "STK Supabase admin not configured; cannot resolve email for %s", user_id
        )
        return None

    url = f"{settings.STK_SUPABASE_URL}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": settings.STK_SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.STK_SUPABASE_SERVICE_ROLE_KEY}",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        logger.warning(
            "Supabase user lookup failed for %s: HTTP %s", user_id, resp.status_code
        )
        return None

    email = resp.json().get("email")
    if not email:
        logger.info("Supabase user %s has no email on record", user_id)
        return None
    return email


def _render_section(section) -> str:
    """Render one brief section card. Accepts a BriefSection or a plain dict."""
    title = section["title"] if isinstance(section, dict) else section.title
    body = section["body"] if isinstance(section, dict) else section.body
    return f"""
      <tr><td style="padding:0 0 12px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:{_CARD};border:1px solid {_BORDER};border-radius:10px;">
          <tr><td style="padding:16px 18px;">
            <div style="color:{_GREEN_LIGHT};font-size:13px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;margin:0 0 8px 0;">{escape(title)}</div>
            <div style="color:{_TEXT};font-size:14px;line-height:1.55;margin:0;">{escape(_truncate(body))}</div>
          </td></tr>
        </table>
      </td></tr>"""


def _render_alert(alert) -> str:
    title = alert["title"] if isinstance(alert, dict) else alert.title
    body = alert["body"] if isinstance(alert, dict) else alert.body
    ticker = alert["ticker"] if isinstance(alert, dict) else alert.ticker
    return f"""
      <tr><td style="padding:0 0 10px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(251,191,36,0.08);border:1px solid {_AMBER};border-radius:10px;">
          <tr><td style="padding:12px 16px;">
            <div style="color:{_AMBER};font-size:12px;font-weight:700;margin:0 0 4px 0;">📅 {escape(ticker)} · {escape(title)}</div>
            <div style="color:{_TEXT};font-size:13px;line-height:1.5;margin:0;">{escape(_truncate(body, 200))}</div>
          </td></tr>
        </table>
      </td></tr>"""


def _is_earnings_alert(alert) -> bool:
    type_ = alert["type"] if isinstance(alert, dict) else alert.type
    title = alert["title"] if isinstance(alert, dict) else alert.title
    return "earning" in f"{type_} {title}".lower()


def render_brief_html(brief: Brief) -> str:
    """Build the dark-themed HTML email body for a brief (matches STK's theme)."""
    score = brief.portfolio_health
    score_color = _health_color(score)
    date_str = brief.date.strftime("%A, %B %-d, %Y")

    # Top 3 sections, summarised.
    sections_html = "".join(_render_section(s) for s in brief.sections[:3])

    # Earnings alerts only.
    earnings = [a for a in brief.alerts if _is_earnings_alert(a)]
    if earnings:
        alerts_html = (
            f'<div style="color:{_MUTED};font-size:13px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.4px;margin:18px 0 10px 0;">'
            f"Earnings Alerts</div>"
            + "".join(_render_alert(a) for a in earnings)
        )
    else:
        alerts_html = ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{_BG};">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:28px 12px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

        <!-- Header -->
        <tr><td style="padding:0 0 20px 0;">
          <div style="color:{_GREEN};font-size:22px;font-weight:800;letter-spacing:-.3px;">STK <span style="color:{_MUTED};font-weight:600;">· Daily Brief</span></div>
          <div style="color:{_MUTED};font-size:13px;margin-top:4px;">{escape(date_str)}</div>
        </td></tr>

        <!-- Health score -->
        <tr><td style="padding:0 0 18px 0;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:{_CARD};border:1px solid {_BORDER};border-radius:12px;">
            <tr><td style="padding:20px 22px;">
              <div style="color:{_MUTED};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Portfolio Health</div>
              <div style="color:{score_color};font-size:40px;font-weight:800;line-height:1;">{score}<span style="color:{_MUTED};font-size:18px;font-weight:600;">/100</span></div>
              <div style="color:{_TEXT};font-size:15px;line-height:1.5;margin-top:12px;">{escape(brief.headline)}</div>
            </td></tr>
          </table>
        </td></tr>

        <!-- Sections -->
        <tr><td>
          <div style="color:{_MUTED};font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;margin:0 0 10px 0;">Today's Highlights</div>
          <table width="100%" cellpadding="0" cellspacing="0">{sections_html}</table>
        </td></tr>

        <!-- Earnings alerts -->
        <tr><td>{alerts_html}</td></tr>

        <!-- CTA -->
        <tr><td style="padding:22px 0 8px 0;" align="center">
          <a href="{STK_FRONTEND_URL}" style="display:inline-block;background:{_GREEN};color:{_BG};font-size:15px;font-weight:700;text-decoration:none;padding:13px 30px;border-radius:10px;">View full brief on STK →</a>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:18px 0 0 0;" align="center">
          <div style="color:{_MUTED};font-size:11px;line-height:1.5;">You're receiving this because you have a portfolio on STK.<br>Generated by Watchman · proactive portfolio intelligence.</div>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body></html>"""


async def send_brief_email(to_email: str, brief: Brief) -> bool:
    """Send a single brief email via Resend. Returns True on success."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set; skipping brief email to %s", to_email)
        return False

    payload = {
        "from": EMAIL_SENDER,
        "to": [to_email],
        "subject": f"📊 Your portfolio brief — {brief.date:%b %-d}",
        "html": render_brief_html(brief),
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json=payload,
        )

    if resp.status_code >= 400:
        logger.warning("Resend send failed (HTTP %s): %s", resp.status_code, resp.text[:300])
        return False
    return True


async def send_brief_email_for_user(user_id: str, brief: Brief) -> bool:
    """Fire-and-forget: resolve the user's email and send their brief.

    Never raises — any failure (lookup, network, Resend error) is logged and
    swallowed so brief generation is unaffected.
    """
    try:
        email = await get_user_email(user_id)
        if not email:
            logger.info("No email for user %s; skipping brief email", user_id)
            return False
        sent = await send_brief_email(email, brief)
        if sent:
            logger.info("Brief email sent to user %s", user_id)
        return sent
    except Exception as exc:  # noqa: BLE001 — fire-and-forget by design
        logger.warning("Brief email failed for user %s: %s", user_id, exc)
        return False
