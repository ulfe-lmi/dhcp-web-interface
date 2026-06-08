from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from managed_dhcp_server.ipam.models import Organization, Site


class OrganizationRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    VIEWER = "viewer", "Viewer"
    AUDITOR = "auditor", "Auditor"


class SiteRole(models.TextChoices):
    SITE_ADMIN = "site_admin", "Site admin"
    DHCP_EDITOR = "dhcp_editor", "DHCP editor"
    VIEWER = "viewer", "Viewer"
    PUBLIC_PUBLISHER = "public_publisher", "Public publisher"
    DEVICE_INSTALLER = "device_installer", "Device installer"


class OrganizationMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships")
    role = models.CharField(max_length=32, choices=OrganizationRole.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__name", "user_id"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="unique_organization_membership_user"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.user_id}:{self.role}"


class SiteMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="site_memberships")
    role = models.CharField(max_length=32, choices=SiteRole.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["site__organization__name", "site__name", "user_id"]
        constraints = [
            models.UniqueConstraint(fields=["site", "user"], name="unique_site_membership_user"),
        ]

    def __str__(self) -> str:
        return f"{self.site}:{self.user_id}:{self.role}"


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="audit_events", blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name="audit_events", blank=True, null=True)
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, related_name="audit_events", blank=True, null=True)
    event_type = models.CharField(max_length=128)
    object_type = models.CharField(max_length=128, blank=True)
    object_id = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=500)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def record(
        cls,
        *,
        actor: object | None = None,
        organization: Organization | None = None,
        site: Site | None = None,
        event_type: str,
        object_type: str = "",
        object_id: str = "",
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> "AuditEvent":
        event = cls(
            actor=actor,
            organization=organization,
            site=site,
            event_type=event_type,
            object_type=object_type,
            object_id=object_id,
            summary=summary,
            metadata=metadata or {},
        )
        event.save()
        return event

    def clean(self) -> None:
        errors: dict[str, list[ValidationError]] = {}

        self.event_type = self.event_type.strip()
        self.summary = self.summary.strip()
        self.object_type = self.object_type.strip()
        self.object_id = self.object_id.strip()

        if not self.event_type:
            errors.setdefault("event_type", []).append(ValidationError("Event type is required."))

        if not self.summary:
            errors.setdefault("summary", []).append(ValidationError("Summary is required."))

        if not isinstance(self.metadata, dict):
            errors.setdefault("metadata", []).append(ValidationError("Audit event metadata must be a JSON object."))

        if errors:
            raise ValidationError(errors)

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit events are append-only and cannot be changed.")

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise ValidationError("Audit events are append-only and cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.event_type}: {self.summary}"
