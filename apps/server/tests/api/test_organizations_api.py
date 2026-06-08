import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole

from .factories import create_organization, create_site, create_user


pytestmark = pytest.mark.django_db


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def response_ids(response) -> set[str]:
    return {item["id"] for item in response.json()}


def test_anonymous_cannot_list_organizations() -> None:
    response = APIClient().get("/api/v1/organizations/")

    assert response.status_code in {401, 403}


def test_superuser_sees_all_organizations() -> None:
    organization_a = create_organization("a")
    organization_b = create_organization("b")
    user = create_user("super-orgs", is_superuser=True)

    response = authenticated_client(user).get("/api/v1/organizations/")

    assert response.status_code == 200
    assert response_ids(response) == {str(organization_a.id), str(organization_b.id)}


def test_organization_member_sees_their_organization() -> None:
    organization = create_organization("member-org")
    other = create_organization("other-org")
    user = create_user("org-member")
    OrganizationMembership.objects.create(organization=organization, user=user, role=OrganizationRole.VIEWER)

    response = authenticated_client(user).get("/api/v1/organizations/")

    assert response.status_code == 200
    assert response_ids(response) == {str(organization.id)}
    assert str(other.id) not in response_ids(response)


def test_site_only_member_sees_organization_containing_their_site() -> None:
    site = create_site("site-only")
    user = create_user("site-only-member")
    SiteMembership.objects.create(site=site, user=user, role=SiteRole.VIEWER)

    response = authenticated_client(user).get("/api/v1/organizations/")

    assert response.status_code == 200
    assert response_ids(response) == {str(site.organization.id)}


def test_unrelated_user_sees_empty_organization_list() -> None:
    create_organization("hidden")
    user = create_user("unrelated-orgs")

    response = authenticated_client(user).get("/api/v1/organizations/")

    assert response.status_code == 200
    assert response.json() == []


def test_organization_detail_works_for_member() -> None:
    organization = create_organization("detail")
    user = create_user("org-detail")
    OrganizationMembership.objects.create(organization=organization, user=user, role=OrganizationRole.AUDITOR)

    response = authenticated_client(user).get(f"/api/v1/organizations/{organization.id}/")

    assert response.status_code == 200
    assert response.json()["id"] == str(organization.id)
    assert set(response.json()) == {"id", "name", "slug", "created_at", "updated_at"}


def test_organization_detail_returns_404_for_inaccessible_organization() -> None:
    organization = create_organization("inaccessible")
    user = create_user("no-org-detail")

    response = authenticated_client(user).get(f"/api/v1/organizations/{organization.id}/")

    assert response.status_code == 404
