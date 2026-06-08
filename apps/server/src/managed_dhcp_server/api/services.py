from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from managed_dhcp_server.access.models import AuditEvent, OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.ipam.models import Organization, Site

from .permissions import (
    can_create_organization_owner_membership,
    can_manage_existing_organization_owner_membership,
    has_full_site_membership_management,
)

SITE_ADMIN_MANAGED_ROLES = {
    SiteRole.DHCP_EDITOR,
    SiteRole.VIEWER,
    SiteRole.PUBLIC_PUBLISHER,
    SiteRole.DEVICE_INSTALLER,
}


def create_organization_membership(
    *,
    actor: object,
    organization: Organization,
    user: object,
    role: str,
) -> OrganizationMembership:
    if role == OrganizationRole.OWNER and not can_create_organization_owner_membership(actor):
        raise PermissionDenied("Only superusers can create organization owner memberships.")

    membership = OrganizationMembership(organization=organization, user=user, role=role)

    with transaction.atomic():
        _save_membership_or_raise_duplicate(membership, "User already has a membership in this organization.")
        AuditEvent.record(
            actor=actor,
            organization=organization,
            event_type="organization_membership.created",
            object_type="OrganizationMembership",
            object_id=str(membership.id),
            summary="Created organization membership.",
            metadata={"target_user_id": str(user.pk), "new_role": role},
        )

    return membership


def update_organization_membership(
    *,
    actor: object,
    membership: OrganizationMembership,
    role: str,
) -> OrganizationMembership:
    old_role = membership.role

    if old_role == OrganizationRole.OWNER and role != OrganizationRole.OWNER and _is_last_organization_owner(membership):
        raise ValidationError({"role": ["Cannot demote the last owner membership in an organization."]})

    if not can_manage_existing_organization_owner_membership(actor) and (old_role == OrganizationRole.OWNER or role == OrganizationRole.OWNER):
        raise PermissionDenied("Only superusers can modify organization owner memberships.")

    membership.role = role

    with transaction.atomic():
        membership.full_clean()
        membership.save()
        AuditEvent.record(
            actor=actor,
            organization=membership.organization,
            event_type="organization_membership.updated",
            object_type="OrganizationMembership",
            object_id=str(membership.id),
            summary="Updated organization membership.",
            metadata={"target_user_id": str(membership.user_id), "old_role": old_role, "new_role": role},
        )

    return membership


def delete_organization_membership(*, actor: object, membership: OrganizationMembership) -> None:
    if membership.role == OrganizationRole.OWNER and _is_last_organization_owner(membership):
        raise ValidationError({"role": ["Cannot delete the last owner membership in an organization."]})

    if membership.role == OrganizationRole.OWNER and not can_manage_existing_organization_owner_membership(actor):
        raise PermissionDenied("Only superusers can delete organization owner memberships.")

    organization = membership.organization
    target_user_id = str(membership.user_id)
    old_role = membership.role
    object_id = str(membership.id)

    with transaction.atomic():
        AuditEvent.record(
            actor=actor,
            organization=organization,
            event_type="organization_membership.deleted",
            object_type="OrganizationMembership",
            object_id=object_id,
            summary="Deleted organization membership.",
            metadata={"target_user_id": target_user_id, "old_role": old_role},
        )
        membership.delete()


def create_site_membership(
    *,
    actor: object,
    site: Site,
    user: object,
    role: str,
) -> SiteMembership:
    _validate_site_admin_role_boundary(actor=actor, site=site, new_role=role)

    membership = SiteMembership(site=site, user=user, role=role)

    with transaction.atomic():
        _save_membership_or_raise_duplicate(membership, "User already has a membership for this site.")
        AuditEvent.record(
            actor=actor,
            organization=site.organization,
            site=site,
            event_type="site_membership.created",
            object_type="SiteMembership",
            object_id=str(membership.id),
            summary="Created site membership.",
            metadata={"target_user_id": str(user.pk), "new_role": role},
        )

    return membership


def update_site_membership(*, actor: object, membership: SiteMembership, role: str) -> SiteMembership:
    old_role = membership.role
    _validate_site_admin_role_boundary(actor=actor, site=membership.site, old_role=old_role, new_role=role)

    membership.role = role

    with transaction.atomic():
        membership.full_clean()
        membership.save()
        AuditEvent.record(
            actor=actor,
            organization=membership.site.organization,
            site=membership.site,
            event_type="site_membership.updated",
            object_type="SiteMembership",
            object_id=str(membership.id),
            summary="Updated site membership.",
            metadata={"target_user_id": str(membership.user_id), "old_role": old_role, "new_role": role},
        )

    return membership


def delete_site_membership(*, actor: object, membership: SiteMembership) -> None:
    _validate_site_admin_role_boundary(actor=actor, site=membership.site, old_role=membership.role)

    site = membership.site
    target_user_id = str(membership.user_id)
    old_role = membership.role
    object_id = str(membership.id)

    with transaction.atomic():
        AuditEvent.record(
            actor=actor,
            organization=site.organization,
            site=site,
            event_type="site_membership.deleted",
            object_type="SiteMembership",
            object_id=object_id,
            summary="Deleted site membership.",
            metadata={"target_user_id": target_user_id, "old_role": old_role},
        )
        membership.delete()


def _save_membership_or_raise_duplicate(membership: OrganizationMembership | SiteMembership, duplicate_message: str) -> None:
    if isinstance(membership, OrganizationMembership) and OrganizationMembership.objects.filter(
        organization=membership.organization,
        user=membership.user,
    ).exists():
        raise ValidationError({"user": [duplicate_message]})

    if isinstance(membership, SiteMembership) and SiteMembership.objects.filter(
        site=membership.site,
        user=membership.user,
    ).exists():
        raise ValidationError({"user": [duplicate_message]})

    try:
        membership.full_clean()
        membership.save()
    except IntegrityError as exc:
        raise ValidationError({"user": [duplicate_message]}) from exc
    except Exception as exc:
        if _is_unique_constraint_validation_error(exc):
            raise ValidationError({"user": [duplicate_message]}) from exc
        raise


def _is_unique_constraint_validation_error(exc: Exception) -> bool:
    message = str(exc)
    return "unique" in message.lower() and "membership" in message.lower()


def _is_last_organization_owner(membership: OrganizationMembership) -> bool:
    return (
        OrganizationMembership.objects.filter(
            organization=membership.organization,
            role=OrganizationRole.OWNER,
        )
        .exclude(pk=membership.pk)
        .count()
        == 0
    )


def _validate_site_admin_role_boundary(
    *,
    actor: object,
    site: Site,
    old_role: str | None = None,
    new_role: str | None = None,
) -> None:
    if has_full_site_membership_management(actor, site):
        return

    if old_role == SiteRole.SITE_ADMIN or new_role == SiteRole.SITE_ADMIN:
        raise PermissionDenied("Site admins cannot manage site_admin memberships.")

    if new_role is not None and new_role not in SITE_ADMIN_MANAGED_ROLES:
        raise PermissionDenied("Site admins cannot assign that site role.")
