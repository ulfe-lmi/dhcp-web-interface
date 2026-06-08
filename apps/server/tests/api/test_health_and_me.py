import pytest
from rest_framework.test import APIClient

from .factories import create_user


pytestmark = pytest.mark.django_db


def test_health_endpoint_works_unauthenticated() -> None:
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_does_not_leak_obvious_sensitive_fields() -> None:
    response = APIClient().get("/api/v1/health/")

    payload = response.json()
    forbidden_keys = {"secret_key", "database_url", "databases", "installed_apps", "debug", "environment", "settings"}
    assert set(payload) == {"status"}
    assert forbidden_keys.isdisjoint({key.lower() for key in payload})


def test_me_endpoint_rejects_anonymous_user() -> None:
    response = APIClient().get("/api/v1/me/")

    assert response.status_code in {401, 403}


def test_me_endpoint_returns_safe_authenticated_user_fields() -> None:
    user = create_user("api-user")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/me/")

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": "api-user",
        "email": "api-user@example.test",
        "is_staff": False,
        "is_superuser": False,
    }


def test_me_endpoint_does_not_include_password() -> None:
    user = create_user("safe-user")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/me/")

    payload = response.json()
    assert "password" not in payload
    assert "last_login" not in payload
    assert "groups" not in payload
    assert "user_permissions" not in payload
