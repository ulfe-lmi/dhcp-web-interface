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


def site_memberships_url(site) -> str:
    return f"/api/v1/sites/{site.id}/memberships/"


def site_membership_detail_url(site, membership) -> str:
    return f"/api/v1/sites/{site.id}/memberships/{membership.id}/"


def create_org_membership(organization, user, role: str = OrganizationRole.VIEWER) -> OrganizationMembership:
    return OrganizationMembership.objects.create(organization=organization, user=user, role=role)


def create_site_membership(site, user, role: str = SiteRole.VIEWER) -> SiteMembership:
    return SiteMembership.objects.create(site=site, user=user, role=role)


def test_anonymous_user_cannot_list_site_memberships() -> None:
    site = create_site("site-members-anon")

    response = APIClient().get(site_memberships_url(site))

    assert response.status_code in {401, 403}


def test_unrelated_user_cannot_list_site_memberships() -> None:
    site = create_site("site-members-unrelated")
    user = create_user("site-members-unrelated")

    response = authenticated_client(user).get(site_memberships_url(site))

    assert response.status_code == 404


@pytest.mark.parametrize("role", [SiteRole.DHCP_EDITOR, SiteRole.VIEWER, SiteRole.PUBLIC_PUBLISHER, SiteRole.DEVICE_INSTALLER])
def test_non_admin_site_roles_cannot_list_site_memberships(role: str) -> None:
    site = create_site(f"site-members-{role}")
    user = create_user(f"site-members-{role}")
    create_site_membership(site, user, role)

    response = authenticated_client(user).get(site_memberships_url(site))

    assert response.status_code == 403


def test_site_member_of_another_site_cannot_list_site_memberships() -> None:
    site_a = create_site("site-members-other-a")
    site_b = create_site("site-members-other-b")
    user = create_user("site-members-other")
    create_site_membership(site_a, user, SiteRole.SITE_ADMIN)

    response = authenticated_client(user).get(site_memberships_url(site_b))

    assert response.status_code == 404


def test_site_admin_can_list_site_memberships() -> None:
    site = create_site("site-members-admin-list")
    user = create_user("site-members-admin-list")
    membership = create_site_membership(site, user, SiteRole.SITE_ADMIN)

    response = authenticated_client(user).get(site_memberships_url(site))

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {str(membership.id)}


@pytest.mark.parametrize("role", [OrganizationRole.ADMIN, OrganizationRole.OWNER])
def test_privileged_organization_roles_can_list_site_memberships(role: str) -> None:
    site = create_site(f"site-members-org-{role}")
    user = create_user(f"site-members-org-{role}")
    member = create_user(f"site-members-listed-{role}")
    create_org_membership(site.organization, user, role)
    membership = create_site_membership(site, member, SiteRole.VIEWER)

    response = authenticated_client(user).get(site_memberships_url(site))

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {str(membership.id)}


def test_superuser_can_list_site_memberships() -> None:
    site = create_site("site-members-super")
    membership = create_site_membership(site, create_user("site-members-super-member"))
    superuser = create_user("site-members-super", is_superuser=True)

    response = authenticated_client(superuser).get(site_memberships_url(site))

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {str(membership.id)}


@pytest.mark.parametrize("org_role", [OrganizationRole.OWNER, OrganizationRole.ADMIN])
def test_organization_owner_and_admin_can_create_site_admin_membership(org_role: str) -> None:
    site = create_site(f"site-members-create-admin-{org_role}")
    actor = create_user(f"site-members-create-admin-{org_role}")
    target = create_user(f"site-members-create-admin-target-{org_role}")
    create_org_membership(site.organization, actor, org_role)

    response = authenticated_client(actor).post(
        site_memberships_url(site),
        {"user": target.id, "role": SiteRole.SITE_ADMIN},
        format="json",
    )

    assert response.status_code == 201
    assert SiteMembership.objects.filter(site=site, user=target, role=SiteRole.SITE_ADMIN).exists()


@pytest.mark.parametrize("role", [SiteRole.VIEWER, SiteRole.DHCP_EDITOR, SiteRole.PUBLIC_PUBLISHER, SiteRole.DEVICE_INSTALLER])
def test_site_admin_can_create_allowed_site_membership_roles(role: str) -> None:
    site = create_site(f"site-members-create-{role}")
    actor = create_user(f"site-members-create-actor-{role}")
    target = create_user(f"site-members-create-target-{role}")
    create_site_membership(site, actor, SiteRole.SITE_ADMIN)

    response = authenticated_client(actor).post(
        site_memberships_url(site),
        {"user": target.id, "role": role},
        format="json",
    )

    assert response.status_code == 201
    assert SiteMembership.objects.filter(site=site, user=target, role=role).exists()


def test_site_admin_cannot_create_site_admin_membership() -> None:
    site = create_site("site-members-create-site-admin-denied")
    actor = create_user("site-members-create-site-admin-denied")
    target = create_user("site-members-create-site-admin-target")
    create_site_membership(site, actor, SiteRole.SITE_ADMIN)

    response = authenticated_client(actor).post(
        site_memberships_url(site),
        {"user": target.id, "role": SiteRole.SITE_ADMIN},
        format="json",
    )

    assert response.status_code == 403


def test_site_admin_cannot_update_membership_to_site_admin() -> None:
    site = create_site("site-members-update-site-admin-denied")
    actor = create_user("site-members-update-site-admin-denied")
    target = create_user("site-members-update-site-admin-target")
    create_site_membership(site, actor, SiteRole.SITE_ADMIN)
    membership = create_site_membership(site, target, SiteRole.VIEWER)

    response = authenticated_client(actor).patch(
        site_membership_detail_url(site, membership),
        {"role": SiteRole.SITE_ADMIN},
        format="json",
    )

    assert response.status_code == 403


def test_site_admin_cannot_delete_another_site_admin_membership() -> None:
    site = create_site("site-members-delete-site-admin-denied")
    actor = create_user("site-members-delete-site-admin-denied")
    target = create_user("site-members-delete-site-admin-target")
    create_site_membership(site, actor, SiteRole.SITE_ADMIN)
    membership = create_site_membership(site, target, SiteRole.SITE_ADMIN)

    response = authenticated_client(actor).delete(site_membership_detail_url(site, membership))

    assert response.status_code == 403
    assert SiteMembership.objects.filter(pk=membership.pk).exists()


def test_dhcp_editor_cannot_create_update_or_delete_site_memberships() -> None:
    site = create_site("site-members-editor-denied")
    actor = create_user("site-members-editor-denied")
    target = create_user("site-members-editor-target")
    create_site_membership(site, actor, SiteRole.DHCP_EDITOR)
    membership = create_site_membership(site, target, SiteRole.VIEWER)
    client = authenticated_client(actor)

    assert client.post(site_memberships_url(site), {"user": target.id, "role": SiteRole.DEVICE_INSTALLER}, format="json").status_code == 403
    assert client.patch(site_membership_detail_url(site, membership), {"role": SiteRole.DEVICE_INSTALLER}, format="json").status_code == 403
    assert client.delete(site_membership_detail_url(site, membership)).status_code == 403


def test_unrelated_user_cannot_create_update_or_delete_site_memberships() -> None:
    site = create_site("site-members-unrelated-denied")
    target = create_user("site-members-unrelated-target")
    membership = create_site_membership(site, target, SiteRole.VIEWER)
    client = authenticated_client(create_user("site-members-unrelated-denied"))

    assert client.post(site_memberships_url(site), {"user": target.id, "role": SiteRole.DEVICE_INSTALLER}, format="json").status_code == 404
    assert client.patch(site_membership_detail_url(site, membership), {"role": SiteRole.DEVICE_INSTALLER}, format="json").status_code == 404
    assert client.delete(site_membership_detail_url(site, membership)).status_code == 404


def test_cross_site_membership_manipulation_returns_404() -> None:
    site_a = create_site("site-members-cross-a")
    site_b = create_site("site-members-cross-b")
    actor = create_user("site-members-cross-actor")
    target = create_user("site-members-cross-target")
    create_site_membership(site_a, actor, SiteRole.SITE_ADMIN)
    membership_b = create_site_membership(site_b, target, SiteRole.VIEWER)

    response = authenticated_client(actor).patch(
        site_membership_detail_url(site_a, membership_b),
        {"role": SiteRole.DEVICE_INSTALLER},
        format="json",
    )

    assert response.status_code == 404


def test_duplicate_site_membership_is_rejected_cleanly() -> None:
    site = create_site("site-members-duplicate")
    actor = create_user("site-members-duplicate-actor")
    target = create_user("site-members-duplicate-target")
    create_site_membership(site, actor, SiteRole.SITE_ADMIN)
    create_site_membership(site, target, SiteRole.VIEWER)

    response = authenticated_client(actor).post(
        site_memberships_url(site),
        {"user": target.id, "role": SiteRole.DEVICE_INSTALLER},
        format="json",
    )

    assert response.status_code == 400
    assert "user" in response.json()


def test_site_membership_create_update_delete_record_audit_events() -> None:
    site = create_site("site-members-audit")
    actor = create_user("site-members-audit-actor")
    target = create_user("site-members-audit-target")
    create_site_membership(site, actor, SiteRole.SITE_ADMIN)
    client = authenticated_client(actor)

    create_response = client.post(
        site_memberships_url(site),
        {"user": target.id, "role": SiteRole.VIEWER},
        format="json",
    )
    membership = SiteMembership.objects.get(id=create_response.json()["id"])
    update_response = client.patch(site_membership_detail_url(site, membership), {"role": SiteRole.DEVICE_INSTALLER}, format="json")
    delete_response = client.delete(site_membership_detail_url(site, membership))

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert delete_response.status_code == 204
    event_types = list(AuditEvent.objects.filter(site=site).order_by("created_at").values_list("event_type", flat=True))
    assert event_types == [
        "site_membership.created",
        "site_membership.updated",
        "site_membership.deleted",
    ]
    update_event = AuditEvent.objects.get(event_type="site_membership.updated")
    assert update_event.metadata == {
        "target_user_id": str(target.id),
        "old_role": SiteRole.VIEWER,
        "new_role": SiteRole.DEVICE_INSTALLER,
    }
    delete_event = AuditEvent.objects.get(event_type="site_membership.deleted")
    assert delete_event.metadata == {"target_user_id": str(target.id), "old_role": SiteRole.DEVICE_INSTALLER}


def test_site_membership_serializer_does_not_expose_sensitive_user_fields() -> None:
    site = create_site("site-members-safe")
    actor = create_user("site-members-safe-actor")
    target = create_user("site-members-safe-target")
    create_site_membership(site, actor, SiteRole.SITE_ADMIN)
    create_site_membership(site, target, SiteRole.VIEWER)

    response = authenticated_client(actor).get(site_memberships_url(site))

    assert response.status_code == 200
    target_payload = next(item for item in response.json() if item["user"] == target.id)
    assert set(target_payload["user_summary"]) == {"id", "username", "email", "is_staff", "is_superuser"}
    assert "password" not in target_payload["user_summary"]
    assert "groups" not in target_payload["user_summary"]
    assert "user_permissions" not in target_payload["user_summary"]
