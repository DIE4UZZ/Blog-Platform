import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("BLOG_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("BLOG_JWT_SECRET", "test-secret")

from backend.app.main import create_app


@pytest.fixture()
def client():
    """Provide a TestClient with in-memory SQLite."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_register_and_login_with_multiple_accounts(client):
    """Verify registration and login by username, email, and phone."""

    response = client.post(
        "/api/user/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "phone": "13800000000",
            "password": "123456",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"].get("user_id")

    for account in ["testuser", "test@example.com", "13800000000"]:
        response = client.post(
            "/api/user/login",
            json={"account": account, "password": "123456"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["code"] == 0
        assert payload["data"].get("token")
        assert payload["data"].get("username") == "testuser"


def test_register_requires_contact(client):
    """Verify registration rejects payloads without email or phone."""

    response = client.post(
        "/api/user/register",
        json={"username": "nocontact", "password": "123456"},
    )
    assert response.status_code == 422
