from __future__ import annotations

from managed_dhcp_server.ipam.models import Organization, Site

from .models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole


def can_view_site(user: object, site: Site) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    organization_role = _organization_role(user, site.organization)
    if organization_role in {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.VIEWER,
        OrganizationRole.AUDITOR,
    }:
        return True

    return _site_role(user, site) in {
        SiteRole.SITE_ADMIN,
        SiteRole.DHCP_EDITOR,
        SiteRole.VIEWER,
        SiteRole.PUBLIC_PUBLISHER,
        SiteRole.DEVICE_INSTALLER,
    }


def can_edit_site_dhcp(user: object, site: Site) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    if _organization_role(user, site.organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
        return True

    return _site_role(user, site) in {SiteRole.SITE_ADMIN, SiteRole.DHCP_EDITOR}


def can_manage_site(user: object, site: Site) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    if _organization_role(user, site.organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
        return True

    return _site_role(user, site) == SiteRole.SITE_ADMIN


def can_publish_public_view(user: object, site: Site) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    if _organization_role(user, site.organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
        return True

    return _site_role(user, site) in {SiteRole.SITE_ADMIN, SiteRole.PUBLIC_PUBLISHER}


def can_install_device(user: object, site: Site) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    if _organization_role(user, site.organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
        return True

    return _site_role(user, site) in {SiteRole.SITE_ADMIN, SiteRole.DEVICE_INSTALLER}


def can_view_audit_events(user: object, organization: Organization | None = None, site: Site | None = None) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    if site is not None:
        if _organization_role(user, site.organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.AUDITOR}:
            return True
        return _site_role(user, site) == SiteRole.SITE_ADMIN

    if organization is None:
        return False

    return _organization_role(user, organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.AUDITOR}


def _has_global_access(user: object) -> bool:
    return _is_active_authenticated_user(user) and bool(getattr(user, "is_superuser", False))


def _is_active_authenticated_user(user: object) -> bool:
    return bool(getattr(user, "is_authenticated", False)) and bool(getattr(user, "is_active", False))


def _organization_role(user: object, organization: Organization) -> str | None:
    membership = OrganizationMembership.objects.filter(user=user, organization=organization).only("role").first()
    return membership.role if membership else None


def _site_role(user: object, site: Site) -> str | None:
    membership = SiteMembership.objects.filter(user=user, site=site).only("role").first()
    return membership.role if membership else None
