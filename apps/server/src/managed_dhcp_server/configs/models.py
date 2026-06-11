from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from managed_dhcp_server.ipam.models import Site


class ConfigVersionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    VALIDATED = "validated", "Validated"
    VALIDATION_FAILED = "validation_failed", "Validation failed"
    APPROVED = "approved", "Approved"
    SUPERSEDED = "superseded", "Superseded"
    ARCHIVED = "archived", "Archived"


class ConfigVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="config_versions")
    version_number = models.PositiveIntegerField()
    status = models.CharField(max_length=32, choices=ConfigVersionStatus.choices, default=ConfigVersionStatus.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_config_versions",
        blank=True,
        null=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_config_versions",
        blank=True,
        null=True,
    )
    source_kind = models.CharField(max_length=32, default="manual")
    change_summary = models.TextField(blank=True)
    validation_result = models.JSONField(default=dict, blank=True)
    rendered_files = models.JSONField(default=dict, blank=True)
    artifact_manifest = models.JSONField(default=dict, blank=True)
    artifact_hash = models.CharField(max_length=64, blank=True)
    artifact_signature = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["site__organization__name", "site__name", "-version_number"]
        constraints = [
            models.UniqueConstraint(fields=["site", "version_number"], name="unique_config_version_number_per_site"),
        ]

    def clean(self) -> None:
        errors: dict[str, list[ValidationError]] = {}
        for field_name in ("rendered_files", "validation_result", "artifact_manifest"):
            if not isinstance(getattr(self, field_name), dict):
                errors.setdefault(field_name, []).append(ValidationError("Value must be a JSON object."))

        if errors:
            raise ValidationError(errors)

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.site} config v{self.version_number}"
