"""
Notification Service - Email, Webhook, and In-App notifications.

Supports:
- Email via Resend API
- Webhook HTTP POST
- In-app notification storage
"""
import hashlib
import hmac
import json
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """
    Multi-channel notification service.

    Channels:
    - Email: Uses Resend API for transactional emails
    - Webhook: HTTP POST with HMAC signature
    - In-App: Stores in database for UI display
    """

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self) -> None:
        self.resend_api_key = getattr(settings, 'resend_api_key', None)

    async def send_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send email via Resend API.

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text fallback

        Returns:
            True if sent successfully
        """
        if not self.resend_api_key:
            logger.warning("Resend API key not configured, skipping email")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": "EcomDash <notifications@ecomdash.dev>",
                        "to": [to],
                        "subject": subject,
                        "html": html_content,
                        "text": text_content or subject,
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    logger.info("Email sent", to=to, subject=subject)
                    return True
                else:
                    logger.error(
                        "Email send failed",
                        status=response.status_code,
                        response=response.text,
                    )
                    return False

        except Exception as e:
            logger.error("Email send error", error=str(e))
            return False

    async def send_webhook(
        self,
        url: str,
        payload: dict[str, Any],
        secret: Optional[str] = None,
    ) -> bool:
        """
        Send webhook HTTP POST with optional HMAC signature.

        Args:
            url: Webhook endpoint URL
            payload: JSON payload to send
            secret: Optional secret for HMAC signature

        Returns:
            True if delivered successfully
        """
        try:
            headers = {"Content-Type": "application/json"}
            body = json.dumps(payload)

            # Add HMAC signature if secret provided
            if secret:
                signature = hmac.new(
                    secret.encode(),
                    body.encode(),
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    content=body,
                    timeout=30.0,
                )

                success = 200 <= response.status_code < 300

                if success:
                    logger.info("Webhook delivered", url=url)
                else:
                    logger.warning(
                        "Webhook delivery failed",
                        url=url,
                        status=response.status_code,
                    )

                return success

        except Exception as e:
            logger.error("Webhook error", url=url, error=str(e))
            return False

    def format_analysis_email(
        self,
        submission_id: str,
        grade: str,
        summary: str,
        bugs_count: int,
        security_count: int,
        optimizations_count: int,
    ) -> tuple[str, str]:
        """
        Format analysis results as email content.

        Returns:
            Tuple of (html_content, text_content)
        """
        grade_colors = {
            "A": "#22c55e",
            "B": "#84cc16",
            "C": "#eab308",
            "D": "#f97316",
            "F": "#ef4444",
        }
        color = grade_colors.get(grade, "#6b7280")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: system-ui, sans-serif; line-height: 1.5; color: #1f2937; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px 12px 0 0; }}
        .grade {{ font-size: 48px; font-weight: bold; color: {color}; }}
        .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 12px 12px; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; }}
        .metric-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
        .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">Code Analysis Complete</h1>
            <p style="margin: 10px 0 0;">Your code has been analyzed by EcomDash AI</p>
        </div>
        <div class="content">
            <div style="text-align: center; margin-bottom: 20px;">
                <div class="grade">{grade}</div>
                <div>Overall Grade</div>
            </div>
            <p>{summary}</p>
            <div style="margin-top: 20px;">
                <div class="metric">
                    <div class="metric-value">{bugs_count}</div>
                    <div class="metric-label">Bugs Found</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{security_count}</div>
                    <div class="metric-label">Security Issues</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{optimizations_count}</div>
                    <div class="metric-label">Optimizations</div>
                </div>
            </div>
            <a href="{getattr(settings, 'app_url', '')}/analysis/{submission_id}"
               style="display: inline-block; margin-top: 20px; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 6px;">
                View Full Report
            </a>
        </div>
        <div class="footer">
            <p>EcomDash - AI-Powered Code Analysis</p>
        </div>
    </div>
</body>
</html>
"""

        text = f"""
Code Analysis Complete

Overall Grade: {grade}

{summary}

Findings:
- {bugs_count} bugs found
- {security_count} security issues
- {optimizations_count} optimization suggestions

View full report: {getattr(settings, 'app_url', '')}/analysis/{submission_id}
"""

        return html, text

    def format_webhook_payload(
        self,
        event_type: str,
        submission_id: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Format analysis result as webhook payload."""
        return {
            "event": event_type,
            "submission_id": submission_id,
            "grade": result.get("overall_grade", "F"),
            "summary": result.get("summary", ""),
            "scores": result.get("scores", {}),
            "findings": {
                "bugs": len(result.get("bugs", [])),
                "security_issues": len(result.get("security_issues", [])),
                "optimizations": len(result.get("optimizations", [])),
            },
            "metadata": result.get("_metadata", {}),
        }


# Singleton instance
notification_service = NotificationService()
