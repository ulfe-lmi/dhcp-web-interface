from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import AuditEvent, OrganizationMembership, OrganizationRole, SiteMembership, SiteRole

from .factories import create_organization, create_site, create_user


pytestmark = pytest.mark.django_db


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def organization_memberships_url(organization) -> str:
    return f"/api/v1/organizations/{organization.id}/memberships/"


def organization_membership_detail_url(organization, membership) -> str:
    return f"/api/v1/organizations/{organization.id}/memberships/{membership.id}/"


def site_memberships_url(site) -> str:
    return f"/api/v1/sites/{site.id}/memberships/"


def site_membership_detail_url(site, membership) -> str:
    return f"/api/v1/sites/{site.id}/memberships/{membership.id}/"


def test_inactive_user_cannot_list_or_mutate_organization_memberships() -> None:
    organization = create_organization("membership-security-inactive-org")
    inactive = create_user("membership-security-inactive-org", is_active=False)
    target = create_user("membership-security-inactive-org-target")
    actor_membership = OrganizationMembership.objects.create(organization=organization, user=inactive, role=OrganizationRole.OWNER)
    target_membership = OrganizationMembership.objects.create(organization=organization, user=target, role=OrganizationRole.VIEWER)
    client = authenticated_client(inactive)

    assert client.get(organization_memberships_url(organization)).status_code == 404
    assert client.post(organization_memberships_url(organization), {"user": target.id, "role": OrganizationRole.AUDITOR}, format="json").status_code == 404
    assert client.patch(organization_membership_detail_url(organization, target_membership), {"role": OrganizationRole.AUDITOR}, format="json").status_code == 404
    assert client.delete(organization_membership_detail_url(organization, actor_membership)).status_code == 404


def test_inactive_user_cannot_list_or_mutate_site_memberships() -> None:
    site = create_site("membership-security-inactive-site")
    inactive = create_user("membership-security-inactive-site", is_active=False)
    target = create_user("membership-security-inactive-site-target")
    SiteMembership.objects.create(site=site, user=inactive, role=SiteRole.SITE_ADMIN)
    target_membership = SiteMembership.objects.create(site=site, user=target, role=SiteRole.VIEWER)
    client = authenticated_client(inactive)

    assert client.get(site_memberships_url(site)).status_code == 404
    assert client.post(site_memberships_url(site), {"user": target.id, "role": SiteRole.DEVICE_INSTALLER}, format="json").status_code == 404
    assert client.patch(site_membership_detail_url(site, target_membership), {"role": SiteRole.DEVICE_INSTALLER}, format="json").status_code == 404
    assert client.delete(site_membership_detail_url(site, target_membership)).status_code == 404


def test_membership_endpoint_under_inaccessible_organization_returns_404() -> None:
    organization = create_organization("membership-security-hidden-org")
    user = create_user("membership-security-hidden-org")

    response = authenticated_client(user).get(organization_memberships_url(organization))

    assert response.status_code == 404


def test_membership_endpoint_under_inaccessible_site_returns_404() -> None:
    site = create_site("membership-security-hidden-site")
    user = create_user("membership-security-hidden-site")

    response = authenticated_client(user).get(site_memberships_url(site))

    assert response.status_code == 404


@pytest.mark.parametrize("field", ["user", "organization", "site"])
def test_organization_membership_patch_cannot_change_user_or_parent_fields(field: str) -> None:
    organization = create_organization(f"membership-security-org-patch-{field}")
    owner = create_user(f"membership-security-org-patch-owner-{field}")
    target = create_user(f"membership-security-org-patch-target-{field}")
    other_user = create_user(f"membership-security-org-patch-other-{field}")
    OrganizationMembership.objects.create(organization=organization, user=owner, role=OrganizationRole.OWNER)
    membership = OrganizationMembership.objects.create(organization=organization, user=target, role=OrganizationRole.VIEWER)
    value = other_user.id if field == "user" else str(create_organization(f"membership-security-other-{field}").id)

    response = authenticated_client(owner).patch(
        organization_membership_detail_url(organization, membership),
        {"role": OrganizationRole.AUDITOR, field: value},
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.parametrize("field", ["user", "organization", "site"])
def test_site_membership_patch_cannot_change_user_or_parent_fields(field: str) -> None:
    site = create_site(f"membership-security-site-patch-{field}")
    actor = create_user(f"membership-security-site-patch-actor-{field}")
    target = create_user(f"membership-security-site-patch-target-{field}")
    other_user = create_user(f"membership-security-site-patch-other-{field}")
    SiteMembership.objects.create(site=site, user=actor, role=SiteRole.SITE_ADMIN)
    membership = SiteMembership.objects.create(site=site, user=target, role=SiteRole.VIEWER)
    value = other_user.id if field == "user" else str(create_site(f"membership-security-other-site-{field}").id)

    response = authenticated_client(actor).patch(
        site_membership_detail_url(site, membership),
        {"role": SiteRole.DEVICE_INSTALLER, field: value},
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.parametrize("field", ["organization", "site"])
def test_organization_membership_post_cannot_set_parent_fields(field: str) -> None:
    organization = create_organization(f"membership-security-org-post-{field}")
    owner = create_user(f"membership-security-org-post-owner-{field}")
    target = create_user(f"membership-security-org-post-target-{field}")
    OrganizationMembership.objects.create(organization=organization, user=owner, role=OrganizationRole.OWNER)
    value = str(create_organization(f"membership-security-org-post-other-{field}").id)

    response = authenticated_client(owner).post(
        organization_memberships_url(organization),
        {"user": target.id, "role": OrganizationRole.VIEWER, field: value},
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.parametrize("field", ["organization", "site"])
def test_site_membership_post_cannot_set_parent_fields(field: str) -> None:
    site = create_site(f"membership-security-site-post-{field}")
    actor = create_user(f"membership-security-site-post-actor-{field}")
    target = create_user(f"membership-security-site-post-target-{field}")
    SiteMembership.objects.create(site=site, user=actor, role=SiteRole.SITE_ADMIN)
    value = str(create_site(f"membership-security-site-post-other-{field}").id)

    response = authenticated_client(actor).post(
        site_memberships_url(site),
        {"user": target.id, "role": SiteRole.VIEWER, field: value},
        format="json",
    )

    assert response.status_code == 400
    assert field in response.json()


def test_audit_metadata_does_not_include_sensitive_request_data() -> None:
    organization = create_organization("membership-security-audit")
    owner = create_user("membership-security-audit-owner")
    target = create_user("membership-security-audit-target")
    OrganizationMembership.objects.create(organization=organization, user=owner, role=OrganizationRole.OWNER)

    response = authenticated_client(owner).post(
        organization_memberships_url(organization),
        {
            "user": target.id,
            "role": OrganizationRole.VIEWER,
            "password": "not-allowed",
            "token": "not-allowed",
            "session": "not-allowed",
            "cookie": "not-allowed",
            "headers": {"Authorization": "not-allowed"},
        },
        format="json",
    )

    assert response.status_code == 400
    assert AuditEvent.objects.count() == 0

    create_response = authenticated_client(owner).post(
        organization_memberships_url(organization),
        {"user": target.id, "role": OrganizationRole.VIEWER},
        format="json",
    )

    assert create_response.status_code == 201
    metadata = AuditEvent.objects.get(event_type="organization_membership.created").metadata
    forbidden_keys = {"password", "token", "session", "cookie", "header", "headers", "authorization"}
    assert forbidden_keys.isdisjoint({key.lower() for key in metadata})
