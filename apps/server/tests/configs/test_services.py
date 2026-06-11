from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied

from managed_dhcp_server.access.models import AuditEvent, OrganizationRole, SiteRole
from managed_dhcp_server.configs.models import ConfigVersion, ConfigVersionStatus
from managed_dhcp_server.configs.services import create_config_version_for_site

from .helpers import create_reservation, create_site, create_subnet, create_user, grant_organization_role, grant_site_role


pytestmark = pytest.mark.django_db


def test_config_version_numbers_increment_per_site() -> None:
    site = create_site("config-numbering")
    user = create_user("config-numbering")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    first = create_config_version_for_site(actor=user, site=site)
    second = create_config_version_for_site(actor=user, site=site)

    assert first.version_number == 1
    assert second.version_number == 2


def test_same_version_number_allowed_on_different_sites() -> None:
    site_a = create_site("config-numbering-a")
    site_b = create_site("config-numbering-b")
    user = create_user("config-numbering-sites")
    grant_site_role(user, site_a, SiteRole.DHCP_EDITOR)
    grant_site_role(user, site_b, SiteRole.DHCP_EDITOR)

    first = create_config_version_for_site(actor=user, site=site_a)
    second = create_config_version_for_site(actor=user, site=site_b)

    assert first.version_number == 1
    assert second.version_number == 1


@pytest.mark.parametrize("field_name", ["rendered_files", "validation_result", "artifact_manifest"])
def test_json_object_fields_must_be_dict(field_name: str) -> None:
    site = create_site(f"config-json-{field_name}")
    config_version = ConfigVersion(site=site, version_number=1, **{field_name: []})

    with pytest.raises(DjangoValidationError):
        config_version.full_clean()


def test_create_config_version_for_site_creates_validated_version_and_audit_event() -> None:
    site = create_site("config-service")
    subnet = create_subnet(site)
    create_reservation(subnet)
    user = create_user("config-service")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    config_version = create_config_version_for_site(actor=user, site=site, change_summary="Initial generated config.")
    event = AuditEvent.objects.get(event_type="config_version.created")

    assert config_version.status == ConfigVersionStatus.VALIDATED
    assert config_version.validation_result == {"status": "ok"}
    assert config_version.rendered_files["dnsmasq/30-reservations.conf"].count("dhcp-host=") == 1
    assert len(config_version.artifact_hash) == 64
    assert config_version.artifact_signature == ""
    assert event.object_id == str(config_version.id)
    assert event.metadata["version_number"] == 1
    assert event.metadata["artifact_hash"] == config_version.artifact_hash


@pytest.mark.parametrize(
    "role",
    [OrganizationRole.VIEWER, OrganizationRole.AUDITOR],
)
def test_service_rejects_organization_read_only_roles(role: str) -> None:
    site = create_site(f"config-reject-org-{role}")
    user = create_user(f"config-reject-org-{role}")
    grant_organization_role(user, site, role)

    with pytest.raises(PermissionDenied):
        create_config_version_for_site(actor=user, site=site)


@pytest.mark.parametrize(
    "role",
    [SiteRole.VIEWER, SiteRole.PUBLIC_PUBLISHER, SiteRole.DEVICE_INSTALLER],
)
def test_service_rejects_non_editor_site_roles(role: str) -> None:
    site = create_site(f"config-reject-site-{role}")
    user = create_user(f"config-reject-site-{role}")
    grant_site_role(user, site, role)

    with pytest.raises(PermissionDenied):
        create_config_version_for_site(actor=user, site=site)


def test_dhcp_editor_organization_admin_and_superuser_can_create_config_version() -> None:
    editor_site = create_site("config-editor")
    admin_site = create_site("config-admin")
    superuser_site = create_site("config-superuser")
    editor = create_user("config-editor")
    admin = create_user("config-admin")
    superuser = create_user("config-superuser", is_superuser=True)
    grant_site_role(editor, editor_site, SiteRole.DHCP_EDITOR)
    grant_organization_role(admin, admin_site, OrganizationRole.ADMIN)

    editor_version = create_config_version_for_site(actor=editor, site=editor_site)
    admin_version = create_config_version_for_site(actor=admin, site=admin_site)
    superuser_version = create_config_version_for_site(actor=superuser, site=superuser_site)

    assert editor_version.version_number == 1
    assert admin_version.version_number == 1
    assert superuser_version.version_number == 1
