"""
Tests for health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns API info."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "EcomDash V2 API"
    assert "version" in data
    assert data["status"] == "running"


def test_health_check(client: TestClient):
    """Test the basic health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_liveness_probe(client: TestClient):
    """Test the liveness probe endpoint."""
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_probe(async_client):
    """Test the readiness probe endpoint."""
    response = await async_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
