from __future__ import annotations

from django.db.models import Q, QuerySet

from managed_dhcp_server.ipam.models import Organization, Site


def organizations_visible_to_user(user: object) -> QuerySet[Organization]:
    if _has_global_access(user):
        return Organization.objects.all().order_by("name")
    if not _is_active_authenticated_user(user):
        return Organization.objects.none()

    return (
        Organization.objects.filter(
            Q(memberships__user=user)
            | Q(sites__memberships__user=user),
        )
        .distinct()
        .order_by("name")
    )


def sites_visible_to_user(user: object) -> QuerySet[Site]:
    if _has_global_access(user):
        return Site.objects.select_related("organization").all().order_by("organization__name", "name")
    if not _is_active_authenticated_user(user):
        return Site.objects.none()

    return (
        Site.objects.select_related("organization")
        .filter(
            Q(organization__memberships__user=user)
            | Q(memberships__user=user),
        )
        .distinct()
        .order_by("organization__name", "name")
    )


def _has_global_access(user: object) -> bool:
    return _is_active_authenticated_user(user) and bool(getattr(user, "is_superuser", False))


def _is_active_authenticated_user(user: object) -> bool:
    return bool(getattr(user, "is_authenticated", False)) and bool(getattr(user, "is_active", False))
