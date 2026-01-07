"""
Tests for service layer components.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_analyzer import AICodeAnalyzer
from app.services.notification_service import NotificationService


class TestAICodeAnalyzer:
    """Tests for AICodeAnalyzer service."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer with mocked OpenAI client."""
        with patch("app.services.ai_analyzer.AsyncOpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            analyzer = AICodeAnalyzer()
            analyzer.client = mock_client
            return analyzer

    @pytest.fixture
    def mock_analysis_response(self):
        """Mock OpenAI response for code analysis."""
        return {
            "bugs": [
                {
                    "type": "potential_bug",
                    "line": 5,
                    "severity": "medium",
                    "message": "Potential division by zero",
                    "fix": "Add zero check before division",
                }
            ],
            "security_issues": [],
            "optimizations": [
                {
                    "type": "performance",
                    "line": 3,
                    "suggestion": "Use list comprehension for better performance",
                    "impact": "minor",
                }
            ],
            "performance_suggestions": [],
            "scores": {
                "performance": 85,
                "security": 95,
                "quality": 80,
            },
            "overall_grade": "B",
            "summary": "Code is generally well-structured with minor improvements suggested.",
        }

    async def test_analyze_code_success(
        self,
        analyzer: AICodeAnalyzer,
        mock_analysis_response: dict,
    ):
        """Test successful code analysis."""
        # Mock OpenAI response
        mock_message = MagicMock()
        mock_message.content = json.dumps(mock_analysis_response)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage.total_tokens = 500

        analyzer.client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        result = await analyzer.analyze_code(
            code="def test(): pass",
            language="python",
        )

        assert result["overall_grade"] == "B"
        assert len(result["bugs"]) == 1
        assert result["scores"]["performance"] == 85
        assert result["tokens_used"] == 500

    async def test_analyze_code_retry_on_failure(
        self,
        analyzer: AICodeAnalyzer,
        mock_analysis_response: dict,
    ):
        """Test retry mechanism on API failure."""
        mock_message = MagicMock()
        mock_message.content = json.dumps(mock_analysis_response)

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage.total_tokens = 500

        # First call fails, second succeeds
        analyzer.client.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("API Error"),
                mock_completion,
            ]
        )

        result = await analyzer.analyze_code(
            code="def test(): pass",
            language="python",
            max_retries=2,
        )

        assert result["overall_grade"] == "B"
        assert analyzer.client.chat.completions.create.call_count == 2

    async def test_analyze_code_all_retries_fail(
        self,
        analyzer: AICodeAnalyzer,
    ):
        """Test handling when all retries fail."""
        analyzer.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Persistent API Error")
        )

        with pytest.raises(Exception, match="Persistent API Error"):
            await analyzer.analyze_code(
                code="def test(): pass",
                language="python",
                max_retries=2,
            )

    async def test_analyze_code_invalid_json_response(
        self,
        analyzer: AICodeAnalyzer,
    ):
        """Test handling of invalid JSON response."""
        mock_message = MagicMock()
        mock_message.content = "Not valid JSON"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        analyzer.client.chat.completions.create = AsyncMock(
            return_value=mock_completion
        )

        with pytest.raises(json.JSONDecodeError):
            await analyzer.analyze_code(
                code="def test(): pass",
                language="python",
                max_retries=1,
            )


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def notification_service(self):
        """Create notification service with mocked dependencies."""
        return NotificationService()

    async def test_send_email_success(
        self,
        notification_service: NotificationService,
    ):
        """Test successful email sending."""
        with patch("app.services.notification_service.resend") as mock_resend:
            mock_resend.api_key = "test_key"
            mock_resend.Emails.send = MagicMock(return_value={"id": "email_123"})

            result = await notification_service.send_email(
                to="test@example.com",
                subject="Test Subject",
                html_content="<p>Test content</p>",
            )

            assert result is True
            mock_resend.Emails.send.assert_called_once()

    async def test_send_email_no_api_key(
        self,
        notification_service: NotificationService,
    ):
        """Test email sending without API key configured."""
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.resend_api_key = None

            result = await notification_service.send_email(
                to="test@example.com",
                subject="Test Subject",
                html_content="<p>Test content</p>",
            )

            assert result is False

    async def test_send_webhook_success(
        self,
        notification_service: NotificationService,
    ):
        """Test successful webhook sending."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await notification_service.send_webhook(
                url="https://example.com/webhook",
                payload={"event": "analysis_complete", "data": {}},
            )

            assert result is True

    async def test_send_webhook_with_secret(
        self,
        notification_service: NotificationService,
    ):
        """Test webhook sending with HMAC signature."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await notification_service.send_webhook(
                url="https://example.com/webhook",
                payload={"event": "analysis_complete"},
                secret="webhook_secret_key",
            )

            assert result is True
            # Verify signature header was included
            call_args = mock_client.post.call_args
            assert "X-Webhook-Signature" in call_args.kwargs.get("headers", {})

    async def test_send_webhook_failure(
        self,
        notification_service: NotificationService,
    ):
        """Test webhook sending failure handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await notification_service.send_webhook(
                url="https://example.com/webhook",
                payload={"event": "analysis_complete"},
            )

            assert result is False

    def test_format_analysis_email(
        self,
        notification_service: NotificationService,
    ):
        """Test email HTML formatting."""
        html, text = notification_service.format_analysis_email(
            submission_id="test-123",
            grade="A",
            summary="Excellent code quality!",
            bugs_count=0,
            security_count=0,
            optimizations_count=1,
        )

        assert "test-123" in html
        assert "A" in html
        assert "Excellent code quality!" in html
        assert "0" in html  # bugs count
        assert "1" in html  # optimizations count
        assert "test-123" in text
        assert "Overall Grade: A" in text

    def test_format_webhook_payload(
        self,
        notification_service: NotificationService,
    ):
        """Test webhook payload formatting."""
        result = {
            "overall_grade": "B",
            "summary": "Good code quality",
            "bugs": [{"line": 1}],
            "security_issues": [],
            "optimizations": [{"line": 2}, {"line": 3}],
            "scores": {"performance": 80, "security": 90, "quality": 85},
        }

        payload = notification_service.format_webhook_payload(
            event_type="analysis_complete",
            submission_id="sub-456",
            result=result,
        )

        assert payload["event"] == "analysis_complete"
        assert payload["submission_id"] == "sub-456"
        assert payload["grade"] == "B"
        assert payload["findings"]["bugs"] == 1
        assert payload["findings"]["optimizations"] == 2
