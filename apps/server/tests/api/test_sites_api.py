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


def test_anonymous_cannot_list_sites() -> None:
    response = APIClient().get("/api/v1/sites/")

    assert response.status_code in {401, 403}


def test_superuser_sees_all_sites() -> None:
    site_a = create_site("a")
    site_b = create_site("b")
    user = create_user("super-sites", is_superuser=True)

    response = authenticated_client(user).get("/api/v1/sites/")

    assert response.status_code == 200
    assert response_ids(response) == {str(site_a.id), str(site_b.id)}


def test_organization_viewer_sees_sites_in_organization() -> None:
    organization = create_organization("org-sites")
    site_a = create_site("site-a", organization=organization)
    site_b = create_site("site-b", organization=organization)
    hidden = create_site("hidden")
    user = create_user("org-site-viewer")
    OrganizationMembership.objects.create(organization=organization, user=user, role=OrganizationRole.VIEWER)

    response = authenticated_client(user).get("/api/v1/sites/")

    assert response.status_code == 200
    assert response_ids(response) == {str(site_a.id), str(site_b.id)}
    assert str(hidden.id) not in response_ids(response)


def test_site_level_viewer_sees_assigned_site() -> None:
    site = create_site("assigned")
    other = create_site("not-assigned")
    user = create_user("site-viewer")
    SiteMembership.objects.create(site=site, user=user, role=SiteRole.VIEWER)

    response = authenticated_client(user).get("/api/v1/sites/")

    assert response.status_code == 200
    assert response_ids(response) == {str(site.id)}
    assert str(other.id) not in response_ids(response)


def test_unrelated_user_sees_empty_site_list() -> None:
    create_site("hidden-site")
    user = create_user("unrelated-sites")

    response = authenticated_client(user).get("/api/v1/sites/")

    assert response.status_code == 200
    assert response.json() == []


def test_site_detail_works_for_site_member() -> None:
    site = create_site("site-detail")
    user = create_user("site-detail-user")
    SiteMembership.objects.create(site=site, user=user, role=SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).get(f"/api/v1/sites/{site.id}/")

    assert response.status_code == 200
    assert response.json()["id"] == str(site.id)
    assert response.json()["organization"] == str(site.organization.id)
    assert response.json()["organization_name"] == site.organization.name
    assert set(response.json()) == {"id", "organization", "organization_name", "name", "slug", "description", "created_at", "updated_at"}


def test_site_detail_returns_404_for_inaccessible_site() -> None:
    site = create_site("inaccessible-site")
    user = create_user("no-site-detail")

    response = authenticated_client(user).get(f"/api/v1/sites/{site.id}/")

    assert response.status_code == 404


def test_site_membership_does_not_grant_access_to_another_site() -> None:
    site_a = create_site("scope-a")
    site_b = create_site("scope-b")
    user = create_user("site-scope-user")
    SiteMembership.objects.create(site=site_a, user=user, role=SiteRole.SITE_ADMIN)

    response = authenticated_client(user).get(f"/api/v1/sites/{site_b.id}/")

    assert response.status_code == 404


def test_organization_membership_grants_access_only_inside_that_organization() -> None:
    organization_a = create_organization("api-org-a")
    organization_b = create_organization("api-org-b")
    site_a = create_site("api-site-a", organization=organization_a)
    site_b = create_site("api-site-b", organization=organization_b)
    user = create_user("api-org-scoped")
    OrganizationMembership.objects.create(organization=organization_a, user=user, role=OrganizationRole.ADMIN)

    response = authenticated_client(user).get("/api/v1/sites/")

    assert response.status_code == 200
    assert response_ids(response) == {str(site_a.id)}
    assert str(site_b.id) not in response_ids(response)
