from __future__ import annotations

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.ipam.models import Organization, Site


def can_list_organization_memberships(user: object, organization: Organization) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    return _organization_role(user, organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN}


def can_mutate_organization_memberships(user: object, organization: Organization) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    return _organization_role(user, organization) == OrganizationRole.OWNER


def can_create_organization_owner_membership(user: object) -> bool:
    return _has_global_access(user)


def can_manage_existing_organization_owner_membership(user: object) -> bool:
    return _has_global_access(user)


def can_list_site_memberships(user: object, site: Site) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    if _organization_role(user, site.organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
        return True

    return _site_role(user, site) == SiteRole.SITE_ADMIN


def can_mutate_site_memberships(user: object, site: Site) -> bool:
    return can_list_site_memberships(user, site)


def has_full_site_membership_management(user: object, site: Site) -> bool:
    if _has_global_access(user):
        return True
    if not _is_active_authenticated_user(user):
        return False

    return _organization_role(user, site.organization) in {OrganizationRole.OWNER, OrganizationRole.ADMIN}


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
