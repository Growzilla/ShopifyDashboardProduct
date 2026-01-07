"""
Tests for shop management endpoints.
"""
import pytest
from fastapi.testclient import TestClient


def test_create_shop(client: TestClient, sample_shop_data: dict):
    """Test creating a new shop."""
    response = client.post("/api/shops", json=sample_shop_data)

    assert response.status_code == 201
    data = response.json()
    assert data["domain"] == sample_shop_data["domain"]
    assert "id" in data
    assert data["syncStatus"] == "pending"


def test_create_shop_duplicate_updates(client: TestClient, sample_shop_data: dict):
    """Test that creating a shop with existing domain updates it."""
    # Create first
    response1 = client.post("/api/shops", json=sample_shop_data)
    assert response1.status_code == 201
    shop_id1 = response1.json()["id"]

    # Create again (should update)
    response2 = client.post("/api/shops", json=sample_shop_data)
    assert response2.status_code == 201
    shop_id2 = response2.json()["id"]

    # Should be the same shop
    assert shop_id1 == shop_id2


def test_get_shop(client: TestClient, sample_shop_data: dict):
    """Test getting a shop by domain."""
    # Create first
    client.post("/api/shops", json=sample_shop_data)

    # Get
    response = client.get(f"/api/shops/{sample_shop_data['domain']}")

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == sample_shop_data["domain"]


def test_get_shop_not_found(client: TestClient):
    """Test getting a non-existent shop returns 404."""
    response = client.get("/api/shops/non-existent.myshopify.com")

    assert response.status_code == 404


def test_update_shop_settings(client: TestClient, sample_shop_data: dict):
    """Test updating shop settings."""
    # Create first
    client.post("/api/shops", json=sample_shop_data)

    # Update
    update_data = {
        "deepModeEnabled": True,
        "clarityProjectId": "clarity123",
    }
    response = client.patch(
        f"/api/shops/{sample_shop_data['domain']}",
        json=update_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["deepModeEnabled"] is True
    assert data["clarityProjectId"] == "clarity123"


def test_delete_shop(client: TestClient, sample_shop_data: dict):
    """Test deleting a shop."""
    # Create first
    client.post("/api/shops", json=sample_shop_data)

    # Delete
    response = client.delete(f"/api/shops/{sample_shop_data['domain']}")
    assert response.status_code == 204

    # Verify deleted
    response = client.get(f"/api/shops/{sample_shop_data['domain']}")
    assert response.status_code == 404
