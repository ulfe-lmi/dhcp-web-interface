from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from managed_dhcp_server.access.models import AuditEvent, OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.ipam.models import DHCPPool, DHCPReservation, IPv4Subnet, Organization, Site

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

SUBNET_AUDIT_FIELDS = ["name", "cidr", "gateway", "dns_servers", "default_lease_time_seconds"]
POOL_AUDIT_FIELDS = ["name", "start_ip", "end_ip", "lease_time_seconds", "enabled"]
RESERVATION_AUDIT_FIELDS = ["hostname", "mac_address", "ip_address", "description", "enabled"]


def create_ipv4_subnet(*, actor: object, site: Site, data: dict[str, object]) -> IPv4Subnet:
    subnet = IPv4Subnet(site=site, **data)

    with transaction.atomic():
        _full_clean_and_save(subnet)
        AuditEvent.record(
            actor=actor,
            organization=site.organization,
            site=site,
            event_type="ipv4_subnet.created",
            object_type="IPv4Subnet",
            object_id=str(subnet.id),
            summary="Created IPv4 subnet.",
            metadata=_model_snapshot(subnet, SUBNET_AUDIT_FIELDS),
        )

    return subnet


def update_ipv4_subnet(*, actor: object, subnet: IPv4Subnet, data: dict[str, object]) -> IPv4Subnet:
    old = _model_snapshot(subnet, SUBNET_AUDIT_FIELDS)
    for field, value in data.items():
        setattr(subnet, field, value)

    with transaction.atomic():
        _full_clean_and_save(subnet)
        new = _model_snapshot(subnet, SUBNET_AUDIT_FIELDS)
        AuditEvent.record(
            actor=actor,
            organization=subnet.site.organization,
            site=subnet.site,
            event_type="ipv4_subnet.updated",
            object_type="IPv4Subnet",
            object_id=str(subnet.id),
            summary="Updated IPv4 subnet.",
            metadata=_change_metadata(old, new),
        )

    return subnet


def delete_ipv4_subnet(*, actor: object, subnet: IPv4Subnet) -> None:
    if subnet.dhcp_pools.exists() or subnet.dhcp_reservations.exists():
        raise ValidationError({"subnet": ["Cannot delete a subnet that has DHCP pools or reservations."]})

    site = subnet.site
    object_id = str(subnet.id)
    metadata = _model_snapshot(subnet, SUBNET_AUDIT_FIELDS)

    with transaction.atomic():
        AuditEvent.record(
            actor=actor,
            organization=site.organization,
            site=site,
            event_type="ipv4_subnet.deleted",
            object_type="IPv4Subnet",
            object_id=object_id,
            summary="Deleted IPv4 subnet.",
            metadata=metadata,
        )
        subnet.delete()


def create_dhcp_pool(*, actor: object, subnet: IPv4Subnet, data: dict[str, object]) -> DHCPPool:
    pool = DHCPPool(subnet=subnet, **data)

    with transaction.atomic():
        _full_clean_and_save(pool)
        AuditEvent.record(
            actor=actor,
            organization=subnet.site.organization,
            site=subnet.site,
            event_type="dhcp_pool.created",
            object_type="DHCPPool",
            object_id=str(pool.id),
            summary="Created DHCP pool.",
            metadata=_model_snapshot(pool, POOL_AUDIT_FIELDS),
        )

    return pool


def update_dhcp_pool(*, actor: object, pool: DHCPPool, data: dict[str, object]) -> DHCPPool:
    old = _model_snapshot(pool, POOL_AUDIT_FIELDS)
    for field, value in data.items():
        setattr(pool, field, value)

    with transaction.atomic():
        _full_clean_and_save(pool)
        new = _model_snapshot(pool, POOL_AUDIT_FIELDS)
        AuditEvent.record(
            actor=actor,
            organization=pool.subnet.site.organization,
            site=pool.subnet.site,
            event_type="dhcp_pool.updated",
            object_type="DHCPPool",
            object_id=str(pool.id),
            summary="Updated DHCP pool.",
            metadata=_change_metadata(old, new),
        )

    return pool


def disable_dhcp_pool(*, actor: object, pool: DHCPPool) -> DHCPPool:
    old = _model_snapshot(pool, POOL_AUDIT_FIELDS)
    pool.enabled = False

    with transaction.atomic():
        _full_clean_and_save(pool)
        AuditEvent.record(
            actor=actor,
            organization=pool.subnet.site.organization,
            site=pool.subnet.site,
            event_type="dhcp_pool.disabled",
            object_type="DHCPPool",
            object_id=str(pool.id),
            summary="Disabled DHCP pool.",
            metadata=_change_metadata(old, _model_snapshot(pool, POOL_AUDIT_FIELDS)),
        )

    return pool


def create_dhcp_reservation(*, actor: object, subnet: IPv4Subnet, data: dict[str, object]) -> DHCPReservation:
    reservation = DHCPReservation(subnet=subnet, **data)

    with transaction.atomic():
        _full_clean_and_save(reservation)
        AuditEvent.record(
            actor=actor,
            organization=subnet.site.organization,
            site=subnet.site,
            event_type="dhcp_reservation.created",
            object_type="DHCPReservation",
            object_id=str(reservation.id),
            summary="Created DHCP reservation.",
            metadata=_reservation_summary_metadata(reservation),
        )

    return reservation


def update_dhcp_reservation(*, actor: object, reservation: DHCPReservation, data: dict[str, object]) -> DHCPReservation:
    old = _model_snapshot(reservation, RESERVATION_AUDIT_FIELDS)
    for field, value in data.items():
        setattr(reservation, field, value)

    with transaction.atomic():
        _full_clean_and_save(reservation)
        new = _model_snapshot(reservation, RESERVATION_AUDIT_FIELDS)
        AuditEvent.record(
            actor=actor,
            organization=reservation.subnet.site.organization,
            site=reservation.subnet.site,
            event_type="dhcp_reservation.updated",
            object_type="DHCPReservation",
            object_id=str(reservation.id),
            summary="Updated DHCP reservation.",
            metadata=_change_metadata(old, new),
        )

    return reservation


def disable_dhcp_reservation(*, actor: object, reservation: DHCPReservation) -> DHCPReservation:
    old = _model_snapshot(reservation, RESERVATION_AUDIT_FIELDS)
    reservation.enabled = False

    with transaction.atomic():
        _full_clean_and_save(reservation)
        AuditEvent.record(
            actor=actor,
            organization=reservation.subnet.site.organization,
            site=reservation.subnet.site,
            event_type="dhcp_reservation.disabled",
            object_type="DHCPReservation",
            object_id=str(reservation.id),
            summary="Disabled DHCP reservation.",
            metadata={
                **_reservation_summary_metadata(reservation),
                **_change_metadata(old, _model_snapshot(reservation, RESERVATION_AUDIT_FIELDS)),
            },
        )

    return reservation


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


def _full_clean_and_save(instance: IPv4Subnet | DHCPPool | DHCPReservation) -> None:
    try:
        instance.full_clean()
        instance.save()
    except DjangoValidationError as exc:
        raise ValidationError(_django_validation_error_detail(exc)) from exc
    except IntegrityError as exc:
        raise ValidationError({"non_field_errors": ["Object violates a uniqueness constraint."]}) from exc


def _django_validation_error_detail(exc: DjangoValidationError) -> dict[str, list[str]]:
    if hasattr(exc, "message_dict"):
        return {
            field: [str(message) for message in messages]
            for field, messages in exc.message_dict.items()
        }
    return {"non_field_errors": [str(message) for message in exc.messages]}


def _model_snapshot(instance: object, fields: list[str]) -> dict[str, object]:
    return {field: _json_safe(getattr(instance, field)) for field in fields}


def _change_metadata(old: dict[str, object], new: dict[str, object]) -> dict[str, dict[str, object]]:
    changed_fields = {field for field in old if old[field] != new[field]}
    return {
        "old": {field: old[field] for field in sorted(changed_fields)},
        "new": {field: new[field] for field in sorted(changed_fields)},
    }


def _reservation_summary_metadata(reservation: DHCPReservation) -> dict[str, str]:
    return {
        "ip_address": str(reservation.ip_address),
        "mac_address": reservation.mac_address,
        "hostname": reservation.hostname,
    }


def _json_safe(value: object) -> object:
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)
