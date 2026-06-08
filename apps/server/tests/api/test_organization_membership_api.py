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


def create_org_membership(organization, user, role: str = OrganizationRole.VIEWER) -> OrganizationMembership:
    return OrganizationMembership.objects.create(organization=organization, user=user, role=role)


def test_anonymous_user_cannot_list_organization_memberships() -> None:
    organization = create_organization("org-members-anon")

    response = APIClient().get(organization_memberships_url(organization))

    assert response.status_code in {401, 403}


def test_unrelated_user_cannot_list_organization_memberships() -> None:
    organization = create_organization("org-members-unrelated")
    user = create_user("org-members-unrelated")

    response = authenticated_client(user).get(organization_memberships_url(organization))

    assert response.status_code == 404


@pytest.mark.parametrize("role", [OrganizationRole.VIEWER, OrganizationRole.AUDITOR])
def test_read_only_organization_roles_cannot_list_organization_memberships(role: str) -> None:
    organization = create_organization(f"org-members-{role}")
    user = create_user(f"org-members-{role}")
    create_org_membership(organization, user, role)

    response = authenticated_client(user).get(organization_memberships_url(organization))

    assert response.status_code == 403


def test_site_only_member_cannot_list_organization_memberships() -> None:
    site = create_site("org-members-site-only")
    user = create_user("org-members-site-only")
    SiteMembership.objects.create(site=site, user=user, role=SiteRole.SITE_ADMIN)

    response = authenticated_client(user).get(organization_memberships_url(site.organization))

    assert response.status_code == 403


@pytest.mark.parametrize("role", [OrganizationRole.ADMIN, OrganizationRole.OWNER])
def test_privileged_organization_roles_can_list_organization_memberships(role: str) -> None:
    organization = create_organization(f"org-members-list-{role}")
    user = create_user(f"org-members-list-{role}")
    member = create_user(f"org-members-listed-{role}")
    create_org_membership(organization, user, role)
    membership = create_org_membership(organization, member, OrganizationRole.VIEWER)

    response = authenticated_client(user).get(organization_memberships_url(organization))

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {str(membership.id), str(OrganizationMembership.objects.get(user=user).id)}


def test_superuser_can_list_organization_memberships() -> None:
    organization = create_organization("org-members-super")
    membership = create_org_membership(organization, create_user("org-members-super-member"))
    superuser = create_user("org-members-super", is_superuser=True)

    response = authenticated_client(superuser).get(organization_memberships_url(organization))

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {str(membership.id)}


def test_organization_owner_can_create_viewer_membership() -> None:
    organization = create_organization("org-members-create")
    owner = create_user("org-members-owner")
    target = create_user("org-members-target")
    create_org_membership(organization, owner, OrganizationRole.OWNER)

    response = authenticated_client(owner).post(
        organization_memberships_url(organization),
        {"user": target.id, "role": OrganizationRole.VIEWER},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["user"] == target.id
    assert response.json()["role"] == OrganizationRole.VIEWER
    assert OrganizationMembership.objects.filter(organization=organization, user=target, role=OrganizationRole.VIEWER).exists()


def test_organization_owner_can_update_non_owner_membership_role() -> None:
    organization = create_organization("org-members-update")
    owner = create_user("org-members-update-owner")
    target = create_user("org-members-update-target")
    create_org_membership(organization, owner, OrganizationRole.OWNER)
    membership = create_org_membership(organization, target, OrganizationRole.VIEWER)

    response = authenticated_client(owner).patch(
        organization_membership_detail_url(organization, membership),
        {"role": OrganizationRole.ADMIN},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["role"] == OrganizationRole.ADMIN
    membership.refresh_from_db()
    assert membership.role == OrganizationRole.ADMIN


def test_organization_owner_can_delete_non_owner_membership() -> None:
    organization = create_organization("org-members-delete")
    owner = create_user("org-members-delete-owner")
    target = create_user("org-members-delete-target")
    create_org_membership(organization, owner, OrganizationRole.OWNER)
    membership = create_org_membership(organization, target, OrganizationRole.VIEWER)

    response = authenticated_client(owner).delete(organization_membership_detail_url(organization, membership))

    assert response.status_code == 204
    assert not OrganizationMembership.objects.filter(pk=membership.pk).exists()


def test_organization_admin_cannot_create_update_or_delete_memberships_in_this_pr() -> None:
    organization = create_organization("org-members-admin-denied")
    admin = create_user("org-members-admin-denied")
    target = create_user("org-members-admin-target")
    membership = create_org_membership(organization, target, OrganizationRole.VIEWER)
    create_org_membership(organization, admin, OrganizationRole.ADMIN)
    client = authenticated_client(admin)

    assert client.post(organization_memberships_url(organization), {"user": target.id, "role": OrganizationRole.AUDITOR}, format="json").status_code == 403
    assert client.patch(organization_membership_detail_url(organization, membership), {"role": OrganizationRole.AUDITOR}, format="json").status_code == 403
    assert client.delete(organization_membership_detail_url(organization, membership)).status_code == 403


def test_unrelated_user_cannot_create_update_or_delete_organization_memberships() -> None:
    organization = create_organization("org-members-unrelated-denied")
    target = create_user("org-members-unrelated-target")
    membership = create_org_membership(organization, target, OrganizationRole.VIEWER)
    client = authenticated_client(create_user("org-members-unrelated-denied"))

    assert client.post(organization_memberships_url(organization), {"user": target.id, "role": OrganizationRole.AUDITOR}, format="json").status_code == 404
    assert client.patch(organization_membership_detail_url(organization, membership), {"role": OrganizationRole.AUDITOR}, format="json").status_code == 404
    assert client.delete(organization_membership_detail_url(organization, membership)).status_code == 404


def test_superuser_can_create_owner_membership() -> None:
    organization = create_organization("org-members-super-owner")
    target = create_user("org-members-super-owner-target")
    superuser = create_user("org-members-super-owner", is_superuser=True)

    response = authenticated_client(superuser).post(
        organization_memberships_url(organization),
        {"user": target.id, "role": OrganizationRole.OWNER},
        format="json",
    )

    assert response.status_code == 201
    assert OrganizationMembership.objects.filter(organization=organization, user=target, role=OrganizationRole.OWNER).exists()


def test_organization_owner_cannot_create_owner_membership() -> None:
    organization = create_organization("org-members-owner-denied")
    owner = create_user("org-members-owner-denied")
    target = create_user("org-members-owner-denied-target")
    create_org_membership(organization, owner, OrganizationRole.OWNER)

    response = authenticated_client(owner).post(
        organization_memberships_url(organization),
        {"user": target.id, "role": OrganizationRole.OWNER},
        format="json",
    )

    assert response.status_code == 403


def test_cannot_delete_last_organization_owner() -> None:
    organization = create_organization("org-members-last-delete")
    owner = create_user("org-members-last-delete")
    membership = create_org_membership(organization, owner, OrganizationRole.OWNER)
    superuser = create_user("org-members-last-delete-super", is_superuser=True)

    response = authenticated_client(superuser).delete(organization_membership_detail_url(organization, membership))

    assert response.status_code == 400
    assert OrganizationMembership.objects.filter(pk=membership.pk).exists()


def test_cannot_demote_last_organization_owner() -> None:
    organization = create_organization("org-members-last-demote")
    owner = create_user("org-members-last-demote")
    membership = create_org_membership(organization, owner, OrganizationRole.OWNER)
    superuser = create_user("org-members-last-demote-super", is_superuser=True)

    response = authenticated_client(superuser).patch(
        organization_membership_detail_url(organization, membership),
        {"role": OrganizationRole.ADMIN},
        format="json",
    )

    assert response.status_code == 400
    membership.refresh_from_db()
    assert membership.role == OrganizationRole.OWNER


def test_duplicate_organization_membership_is_rejected_cleanly() -> None:
    organization = create_organization("org-members-duplicate")
    owner = create_user("org-members-duplicate-owner")
    target = create_user("org-members-duplicate-target")
    create_org_membership(organization, owner, OrganizationRole.OWNER)
    create_org_membership(organization, target, OrganizationRole.VIEWER)

    response = authenticated_client(owner).post(
        organization_memberships_url(organization),
        {"user": target.id, "role": OrganizationRole.AUDITOR},
        format="json",
    )

    assert response.status_code == 400
    assert "user" in response.json()


def test_cross_organization_membership_manipulation_returns_404() -> None:
    organization_a = create_organization("org-members-cross-a")
    organization_b = create_organization("org-members-cross-b")
    owner = create_user("org-members-cross-owner")
    target = create_user("org-members-cross-target")
    create_org_membership(organization_a, owner, OrganizationRole.OWNER)
    membership_b = create_org_membership(organization_b, target, OrganizationRole.VIEWER)

    response = authenticated_client(owner).patch(
        organization_membership_detail_url(organization_a, membership_b),
        {"role": OrganizationRole.AUDITOR},
        format="json",
    )

    assert response.status_code == 404


def test_organization_membership_create_update_delete_record_audit_events() -> None:
    organization = create_organization("org-members-audit")
    owner = create_user("org-members-audit-owner")
    target = create_user("org-members-audit-target")
    create_org_membership(organization, owner, OrganizationRole.OWNER)
    client = authenticated_client(owner)

    create_response = client.post(
        organization_memberships_url(organization),
        {"user": target.id, "role": OrganizationRole.VIEWER},
        format="json",
    )
    membership = OrganizationMembership.objects.get(id=create_response.json()["id"])
    update_response = client.patch(organization_membership_detail_url(organization, membership), {"role": OrganizationRole.AUDITOR}, format="json")
    delete_response = client.delete(organization_membership_detail_url(organization, membership))

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert delete_response.status_code == 204
    event_types = list(AuditEvent.objects.filter(organization=organization).order_by("created_at").values_list("event_type", flat=True))
    assert event_types == [
        "organization_membership.created",
        "organization_membership.updated",
        "organization_membership.deleted",
    ]
    update_event = AuditEvent.objects.get(event_type="organization_membership.updated")
    assert update_event.metadata == {
        "target_user_id": str(target.id),
        "old_role": OrganizationRole.VIEWER,
        "new_role": OrganizationRole.AUDITOR,
    }
    delete_event = AuditEvent.objects.get(event_type="organization_membership.deleted")
    assert delete_event.metadata == {"target_user_id": str(target.id), "old_role": OrganizationRole.AUDITOR}


def test_organization_membership_serializer_does_not_expose_sensitive_user_fields() -> None:
    organization = create_organization("org-members-safe")
    owner = create_user("org-members-safe-owner")
    target = create_user("org-members-safe-target")
    create_org_membership(organization, owner, OrganizationRole.OWNER)
    create_org_membership(organization, target, OrganizationRole.VIEWER)

    response = authenticated_client(owner).get(organization_memberships_url(organization))

    assert response.status_code == 200
    target_payload = next(item for item in response.json() if item["user"] == target.id)
    assert set(target_payload["user_summary"]) == {"id", "username", "email", "is_staff", "is_superuser"}
    assert "password" not in target_payload["user_summary"]
    assert "groups" not in target_payload["user_summary"]
    assert "user_permissions" not in target_payload["user_summary"]
