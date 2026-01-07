"""
Tests for Code Analysis API endpoints.
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CodeSubmission, Shop, SubmissionStatus


@pytest.fixture
async def test_shop(db_session: AsyncSession) -> Shop:
    """Create a test shop for code analysis tests."""
    from app.core.security import encrypt_token

    shop = Shop(
        id=uuid4(),
        domain="code-test-shop.myshopify.com",
        access_token_encrypted=encrypt_token("shpat_test_123"),
        scopes="read_products,read_orders",
    )
    db_session.add(shop)
    await db_session.commit()
    await db_session.refresh(shop)
    return shop


@pytest.fixture
def sample_code() -> str:
    """Sample Python code for testing."""
    return '''
def calculate_total(items):
    total = 0
    for item in items:
        total += item["price"] * item["quantity"]
    return total
'''


@pytest.fixture
def sample_submission_data(sample_code: str) -> dict:
    """Sample code submission data."""
    return {
        "code": sample_code,
        "language": "python",
        "filename": "calculator.py",
        "priority": "normal",
    }


class TestCodeSubmission:
    """Tests for code submission endpoints."""

    async def test_submit_code_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_shop: Shop,
        sample_submission_data: dict,
    ):
        """Test successful code submission."""
        with patch("app.routers.code_analysis.get_redis", return_value=None):
            response = await async_client.post(
                f"/api/code/submit?shop_id={test_shop.id}",
                json=sample_submission_data,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == SubmissionStatus.PENDING.value
        assert data["language"] == "python"
        assert data["filename"] == "calculator.py"
        assert "id" in data

    async def test_submit_code_invalid_shop(
        self,
        async_client: AsyncClient,
        sample_submission_data: dict,
    ):
        """Test code submission with invalid shop ID."""
        fake_shop_id = uuid4()

        response = await async_client.post(
            f"/api/code/submit?shop_id={fake_shop_id}",
            json=sample_submission_data,
        )

        assert response.status_code == 404

    async def test_submit_code_empty_code(
        self,
        async_client: AsyncClient,
        test_shop: Shop,
    ):
        """Test code submission with empty code."""
        response = await async_client.post(
            f"/api/code/submit?shop_id={test_shop.id}",
            json={"code": "", "language": "python"},
        )

        assert response.status_code == 422

    async def test_get_submission(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_shop: Shop,
        sample_code: str,
    ):
        """Test getting a submission by ID."""
        # Create submission directly
        submission = CodeSubmission(
            id=uuid4(),
            shop_id=test_shop.id,
            code=sample_code,
            language="python",
            status=SubmissionStatus.PENDING.value,
        )
        db_session.add(submission)
        await db_session.commit()

        response = await async_client.get(f"/api/code/{submission.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(submission.id)
        assert data["status"] == SubmissionStatus.PENDING.value

    async def test_get_submission_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test getting non-existent submission."""
        fake_id = uuid4()

        response = await async_client.get(f"/api/code/{fake_id}")

        assert response.status_code == 404

    async def test_list_submissions(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_shop: Shop,
        sample_code: str,
    ):
        """Test listing submissions for a shop."""
        # Create multiple submissions
        for i in range(3):
            submission = CodeSubmission(
                id=uuid4(),
                shop_id=test_shop.id,
                code=f"{sample_code}# {i}",
                language="python",
                status=SubmissionStatus.PENDING.value,
            )
            db_session.add(submission)
        await db_session.commit()

        response = await async_client.get(
            f"/api/code/submissions?shop_id={test_shop.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestAnalysisResults:
    """Tests for analysis result endpoints."""

    async def test_get_result_pending(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_shop: Shop,
        sample_code: str,
    ):
        """Test getting result for pending submission."""
        submission = CodeSubmission(
            id=uuid4(),
            shop_id=test_shop.id,
            code=sample_code,
            language="python",
            status=SubmissionStatus.PENDING.value,
        )
        db_session.add(submission)
        await db_session.commit()

        response = await async_client.get(f"/api/code/{submission.id}/result")

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"

    async def test_get_result_completed(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_shop: Shop,
        sample_code: str,
    ):
        """Test getting result for completed submission."""
        from app.models import AnalysisResult

        submission = CodeSubmission(
            id=uuid4(),
            shop_id=test_shop.id,
            code=sample_code,
            language="python",
            status=SubmissionStatus.COMPLETED.value,
        )
        db_session.add(submission)
        await db_session.flush()

        result = AnalysisResult(
            id=uuid4(),
            submission_id=submission.id,
            bugs=[{"type": "potential_bug", "line": 3, "message": "Test bug"}],
            security_issues=[],
            optimizations=[{"type": "performance", "suggestion": "Use list comprehension"}],
            performance_suggestions=[],
            performance_score=80,
            security_score=90,
            quality_score=85,
            overall_grade="B",
            summary="Code looks good overall.",
            tokens_used=150,
        )
        db_session.add(result)
        await db_session.commit()

        response = await async_client.get(f"/api/code/{submission.id}/result")

        assert response.status_code == 200
        data = response.json()
        assert data["overall_grade"] == "B"
        assert len(data["bugs"]) == 1
        assert data["performance_score"] == 80


class TestNotificationPreferences:
    """Tests for notification preference endpoints."""

    async def test_get_preferences_default(
        self,
        async_client: AsyncClient,
        test_shop: Shop,
    ):
        """Test getting default notification preferences."""
        response = await async_client.get(
            f"/api/code/preferences?shop_id={test_shop.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] is True
        assert data["in_app_enabled"] is True

    async def test_update_preferences(
        self,
        async_client: AsyncClient,
        test_shop: Shop,
    ):
        """Test updating notification preferences."""
        # First get/create preferences
        await async_client.get(
            f"/api/code/preferences?shop_id={test_shop.id}"
        )

        # Update preferences
        response = await async_client.put(
            f"/api/code/preferences?shop_id={test_shop.id}",
            json={
                "email_enabled": False,
                "email_address": "test@example.com",
                "webhook_enabled": True,
                "webhook_url": "https://example.com/webhook",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] is False
        assert data["email_address"] == "test@example.com"
        assert data["webhook_enabled"] is True


class TestCodeAnalysisStats:
    """Tests for code analysis statistics endpoint."""

    async def test_get_stats(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_shop: Shop,
        sample_code: str,
    ):
        """Test getting analysis statistics."""
        # Create submissions with different statuses
        statuses = [
            SubmissionStatus.PENDING.value,
            SubmissionStatus.COMPLETED.value,
            SubmissionStatus.COMPLETED.value,
            SubmissionStatus.FAILED.value,
        ]

        for status in statuses:
            submission = CodeSubmission(
                id=uuid4(),
                shop_id=test_shop.id,
                code=sample_code,
                language="python",
                status=status,
            )
            db_session.add(submission)
        await db_session.commit()

        response = await async_client.get(
            f"/api/code/stats?shop_id={test_shop.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_submissions"] == 4
        assert data["pending_count"] == 1
        assert data["completed_count"] == 2
        assert data["failed_count"] == 1
