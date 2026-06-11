from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Max
from rest_framework.exceptions import PermissionDenied, ValidationError

from managed_dhcp_server.access.models import AuditEvent
from managed_dhcp_server.access.permissions import can_edit_site_dhcp
from managed_dhcp_server.ipam.models import Site

from .models import ConfigVersion, ConfigVersionStatus
from .renderer import build_artifact_manifest, compute_artifact_hash, render_site_dnsmasq_config


def create_config_version_for_site(*, actor: object, site: Site, change_summary: str = "") -> ConfigVersion:
    if not _is_active_authenticated_user(actor):
        raise PermissionDenied("Authentication is required to create config versions.")
    if not can_edit_site_dhcp(actor, site):
        raise PermissionDenied("You cannot create config versions for this site.")

    with transaction.atomic():
        version_number = _next_version_number(site)
        rendered_files = render_site_dnsmasq_config(site)
        artifact_manifest = build_artifact_manifest(
            site=site,
            version_number=version_number,
            rendered_files=rendered_files,
        )
        artifact_hash = compute_artifact_hash(artifact_manifest)
        config_version = ConfigVersion(
            site=site,
            version_number=version_number,
            status=ConfigVersionStatus.VALIDATED,
            created_by=actor,
            source_kind="manual",
            change_summary=change_summary,
            validation_result={"status": "ok"},
            rendered_files=rendered_files,
            artifact_manifest=artifact_manifest,
            artifact_hash=artifact_hash,
            artifact_signature="",
        )
        try:
            config_version.save()
        except IntegrityError as exc:
            raise ValidationError({"version_number": ["Config version number already exists for this site."]}) from exc

        AuditEvent.record(
            actor=actor,
            organization=site.organization,
            site=site,
            event_type="config_version.created",
            object_type="ConfigVersion",
            object_id=str(config_version.id),
            summary=f"Created config version {config_version.version_number} for site {site.slug}.",
            metadata={
                "version_number": config_version.version_number,
                "artifact_hash": config_version.artifact_hash,
                "rendered_file_paths": sorted(config_version.rendered_files),
            },
        )

    return config_version


def _next_version_number(site: Site) -> int:
    current = ConfigVersion.objects.filter(site=site).aggregate(max_version=Max("version_number"))["max_version"]
    return int(current or 0) + 1


def _is_active_authenticated_user(user: object) -> bool:
    return bool(getattr(user, "is_authenticated", False)) and bool(getattr(user, "is_active", False))
