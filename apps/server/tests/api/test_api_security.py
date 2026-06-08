import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole

from .factories import create_organization, create_site, create_user


pytestmark = pytest.mark.django_db


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_organization_endpoints_are_read_only() -> None:
    organization = create_organization("readonly-org")
    user = create_user("readonly-org-user")
    OrganizationMembership.objects.create(organization=organization, user=user, role=OrganizationRole.OWNER)
    client = authenticated_client(user)

    assert client.post("/api/v1/organizations/", {"name": "New"}, format="json").status_code == 405
    assert client.patch(f"/api/v1/organizations/{organization.id}/", {"name": "Changed"}, format="json").status_code == 405
    assert client.delete(f"/api/v1/organizations/{organization.id}/").status_code == 405


def test_site_endpoints_are_read_only() -> None:
    site = create_site("readonly-site")
    user = create_user("readonly-site-user")
    SiteMembership.objects.create(site=site, user=user, role=SiteRole.SITE_ADMIN)
    client = authenticated_client(user)

    assert client.post("/api/v1/sites/", {"name": "New"}, format="json").status_code == 405
    assert client.patch(f"/api/v1/sites/{site.id}/", {"name": "Changed"}, format="json").status_code == 405
    assert client.delete(f"/api/v1/sites/{site.id}/").status_code == 405


def test_me_endpoint_does_not_expose_sensitive_user_fields() -> None:
    user = create_user("safe-me")
    response = authenticated_client(user).get("/api/v1/me/")

    assert response.status_code == 200
    assert set(response.json()) == {"id", "username", "email", "is_staff", "is_superuser"}
    assert "password" not in response.json()
    assert "groups" not in response.json()
    assert "user_permissions" not in response.json()


def test_health_endpoint_is_anonymous_but_minimal() -> None:
    response = APIClient().get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
