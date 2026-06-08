from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.access.permissions import (
    can_edit_site_dhcp,
    can_install_device,
    can_manage_site,
    can_publish_public_view,
    can_view_audit_events,
    can_view_site,
)

from .factories import create_organization, create_site, create_user


pytestmark = pytest.mark.django_db


def permission_results(user: object, site) -> dict[str, bool]:
    return {
        "view": can_view_site(user, site),
        "edit": can_edit_site_dhcp(user, site),
        "manage": can_manage_site(user, site),
        "publish": can_publish_public_view(user, site),
        "install": can_install_device(user, site),
        "audit": can_view_audit_events(user, site=site),
    }


def test_anonymous_user_cannot_view_edit_or_manage() -> None:
    site = create_site()

    assert permission_results(AnonymousUser(), site) == {
        "view": False,
        "edit": False,
        "manage": False,
        "publish": False,
        "install": False,
        "audit": False,
    }


def test_inactive_user_cannot_view_edit_or_manage() -> None:
    site = create_site()
    user = create_user("inactive", is_active=False)
    OrganizationMembership.objects.create(organization=site.organization, user=user, role=OrganizationRole.OWNER)

    assert permission_results(user, site) == {
        "view": False,
        "edit": False,
        "manage": False,
        "publish": False,
        "install": False,
        "audit": False,
    }


def test_superuser_can_do_all_helper_actions() -> None:
    site = create_site()
    user = create_user("superuser", is_superuser=True)

    assert permission_results(user, site) == {
        "view": True,
        "edit": True,
        "manage": True,
        "publish": True,
        "install": True,
        "audit": True,
    }


@pytest.mark.parametrize("role", [OrganizationRole.OWNER, OrganizationRole.ADMIN])
def test_organization_owner_and_admin_can_do_all_site_helper_actions(role: str) -> None:
    site = create_site()
    user = create_user(f"org-{role}")
    OrganizationMembership.objects.create(organization=site.organization, user=user, role=role)

    assert permission_results(user, site) == {
        "view": True,
        "edit": True,
        "manage": True,
        "publish": True,
        "install": True,
        "audit": True,
    }


def test_organization_viewer_can_view_only() -> None:
    site = create_site()
    user = create_user("org-viewer")
    OrganizationMembership.objects.create(organization=site.organization, user=user, role=OrganizationRole.VIEWER)

    assert permission_results(user, site) == {
        "view": True,
        "edit": False,
        "manage": False,
        "publish": False,
        "install": False,
        "audit": False,
    }


def test_organization_auditor_can_view_and_audit_only() -> None:
    site = create_site()
    user = create_user("org-auditor")
    OrganizationMembership.objects.create(organization=site.organization, user=user, role=OrganizationRole.AUDITOR)

    assert permission_results(user, site) == {
        "view": True,
        "edit": False,
        "manage": False,
        "publish": False,
        "install": False,
        "audit": True,
    }


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (SiteRole.SITE_ADMIN, {"view": True, "edit": True, "manage": True, "publish": True, "install": True, "audit": True}),
        (SiteRole.DHCP_EDITOR, {"view": True, "edit": True, "manage": False, "publish": False, "install": False, "audit": False}),
        (SiteRole.VIEWER, {"view": True, "edit": False, "manage": False, "publish": False, "install": False, "audit": False}),
        (SiteRole.PUBLIC_PUBLISHER, {"view": True, "edit": False, "manage": False, "publish": True, "install": False, "audit": False}),
        (SiteRole.DEVICE_INSTALLER, {"view": True, "edit": False, "manage": False, "publish": False, "install": True, "audit": False}),
    ],
)
def test_site_membership_roles(role: str, expected: dict[str, bool]) -> None:
    site = create_site(f"site-{role}")
    user = create_user(f"user-{role}")
    SiteMembership.objects.create(site=site, user=user, role=role)

    assert permission_results(user, site) == expected


def test_user_with_no_membership_has_no_access() -> None:
    site = create_site()
    user = create_user("no-membership")

    assert permission_results(user, site) == {
        "view": False,
        "edit": False,
        "manage": False,
        "publish": False,
        "install": False,
        "audit": False,
    }


def test_site_membership_does_not_grant_access_to_another_site() -> None:
    site_a = create_site("a")
    site_b = create_site("b")
    user = create_user("site-scoped")
    SiteMembership.objects.create(site=site_a, user=user, role=SiteRole.SITE_ADMIN)

    assert can_view_site(user, site_a) is True
    assert permission_results(user, site_b) == {
        "view": False,
        "edit": False,
        "manage": False,
        "publish": False,
        "install": False,
        "audit": False,
    }


def test_organization_membership_grants_access_only_inside_that_organization() -> None:
    organization_a = create_organization("org-a")
    organization_b = create_organization("org-b")
    site_a = create_site("site-a", organization=organization_a)
    site_b = create_site("site-b", organization=organization_b)
    user = create_user("org-scoped")
    OrganizationMembership.objects.create(organization=organization_a, user=user, role=OrganizationRole.ADMIN)

    assert permission_results(user, site_a) == {
        "view": True,
        "edit": True,
        "manage": True,
        "publish": True,
        "install": True,
        "audit": True,
    }
    assert permission_results(user, site_b) == {
        "view": False,
        "edit": False,
        "manage": False,
        "publish": False,
        "install": False,
        "audit": False,
    }


def test_organization_audit_permission_without_site_uses_organization_membership() -> None:
    organization = create_organization()
    user = create_user("org-audit")
    OrganizationMembership.objects.create(organization=organization, user=user, role=OrganizationRole.AUDITOR)

    assert can_view_audit_events(user, organization=organization) is True
    assert can_view_audit_events(user) is False


def test_site_admin_audit_permission_is_site_scoped() -> None:
    site_a = create_site("audit-a")
    site_b = create_site("audit-b")
    user = create_user("site-admin-audit")
    SiteMembership.objects.create(site=site_a, user=user, role=SiteRole.SITE_ADMIN)

    assert can_view_audit_events(user, site=site_a) is True
    assert can_view_audit_events(user, site=site_b) is False
