from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import AuditEvent, OrganizationRole, SiteRole
from managed_dhcp_server.configs.models import ConfigVersion

from .helpers import authenticated_client, create_reservation, create_site, create_subnet, create_user, grant_organization_role, grant_site_role


pytestmark = pytest.mark.django_db


def config_version_list_url(site) -> str:
    return f"/api/v1/sites/{site.id}/config-versions/"


def config_version_detail_url(site, config_version: ConfigVersion) -> str:
    return f"/api/v1/sites/{site.id}/config-versions/{config_version.id}/"


def rendered_files_url(site, config_version: ConfigVersion) -> str:
    return f"/api/v1/sites/{site.id}/config-versions/{config_version.id}/rendered-files/"


def create_version_through_api(site, user, change_summary: str = "Initial generated config.") -> ConfigVersion:
    response = authenticated_client(user).post(
        config_version_list_url(site),
        {"change_summary": change_summary},
        format="json",
    )
    assert response.status_code == 201
    return ConfigVersion.objects.get(pk=response.json()["id"])


def test_anonymous_cannot_list_config_versions() -> None:
    site = create_site("config-api-anonymous")

    response = APIClient().get(config_version_list_url(site))

    assert response.status_code in {401, 403}


def test_site_viewer_and_dhcp_editor_can_list_config_versions() -> None:
    site = create_site("config-api-list")
    editor = create_user("config-api-list-editor")
    viewer = create_user("config-api-list-viewer")
    grant_site_role(editor, site, SiteRole.DHCP_EDITOR)
    grant_site_role(viewer, site, SiteRole.VIEWER)
    config_version = create_version_through_api(site, editor)

    response = authenticated_client(viewer).get(config_version_list_url(site))

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(config_version.id)
    assert "rendered_files" not in response.json()[0]


def test_unrelated_user_cannot_list_config_versions() -> None:
    site = create_site("config-api-unrelated")
    user = create_user("config-api-unrelated")

    response = authenticated_client(user).get(config_version_list_url(site))

    assert response.status_code == 404


@pytest.mark.parametrize("role", [SiteRole.VIEWER, SiteRole.PUBLIC_PUBLISHER, SiteRole.DEVICE_INSTALLER])
def test_non_editor_site_roles_cannot_create_config_version(role: str) -> None:
    site = create_site(f"config-api-denied-{role}")
    user = create_user(f"config-api-denied-{role}")
    grant_site_role(user, site, role)

    response = authenticated_client(user).post(config_version_list_url(site), {"change_summary": "Denied"}, format="json")

    assert response.status_code == 403


def test_dhcp_editor_and_organization_admin_can_create_config_version() -> None:
    editor_site = create_site("config-api-editor")
    admin_site = create_site("config-api-admin")
    editor = create_user("config-api-editor")
    admin = create_user("config-api-admin")
    grant_site_role(editor, editor_site, SiteRole.DHCP_EDITOR)
    grant_organization_role(admin, admin_site, OrganizationRole.ADMIN)

    editor_response = authenticated_client(editor).post(config_version_list_url(editor_site), {"change_summary": "Editor"}, format="json")
    admin_response = authenticated_client(admin).post(config_version_list_url(admin_site), {"change_summary": "Admin"}, format="json")

    assert editor_response.status_code == 201
    assert admin_response.status_code == 201
    assert editor_response.json()["version_number"] == 1
    assert admin_response.json()["status"] == "validated"


def test_create_endpoint_rejects_client_supplied_read_only_fields() -> None:
    site = create_site("config-api-read-only")
    user = create_user("config-api-read-only")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        config_version_list_url(site),
        {
            "change_summary": "Injected",
            "version_number": 99,
            "status": "approved",
            "rendered_files": {"dnsmasq/30-reservations.conf": "bad"},
            "artifact_hash": "bad",
            "artifact_signature": "bad",
            "created_by": str(user.id),
            "approved_by": str(user.id),
        },
        format="json",
    )

    assert response.status_code == 400
    for field in ["version_number", "status", "rendered_files", "artifact_hash", "artifact_signature", "created_by", "approved_by"]:
        assert field in response.json()
    assert ConfigVersion.objects.count() == 0


def test_detail_endpoint_works_for_site_viewer_and_returns_404_for_inaccessible_user() -> None:
    site = create_site("config-api-detail")
    editor = create_user("config-api-detail-editor")
    viewer = create_user("config-api-detail-viewer")
    unrelated = create_user("config-api-detail-unrelated")
    grant_site_role(editor, site, SiteRole.DHCP_EDITOR)
    grant_site_role(viewer, site, SiteRole.VIEWER)
    config_version = create_version_through_api(site, editor)

    viewer_response = authenticated_client(viewer).get(config_version_detail_url(site, config_version))
    unrelated_response = authenticated_client(unrelated).get(config_version_detail_url(site, config_version))

    assert viewer_response.status_code == 200
    assert viewer_response.json()["id"] == str(config_version.id)
    assert unrelated_response.status_code == 404


def test_rendered_files_endpoint_is_authenticated_and_returns_all_files() -> None:
    site = create_site("config-api-rendered")
    subnet = create_subnet(site)
    create_reservation(subnet)
    editor = create_user("config-api-rendered-editor")
    viewer = create_user("config-api-rendered-viewer")
    grant_site_role(editor, site, SiteRole.DHCP_EDITOR)
    grant_site_role(viewer, site, SiteRole.VIEWER)
    config_version = create_version_through_api(site, editor)

    anonymous_response = APIClient().get(rendered_files_url(site, config_version))
    viewer_response = authenticated_client(viewer).get(rendered_files_url(site, config_version))

    assert anonymous_response.status_code in {401, 403}
    assert viewer_response.status_code == 200
    assert viewer_response.json()["version_number"] == 1
    assert sorted(viewer_response.json()["files"]) == [
        "dnsmasq/10-ranges.conf",
        "dnsmasq/20-options.conf",
        "dnsmasq/30-reservations.conf",
        "dnsmasq/40-hosts.conf",
    ]
    assert "dhcp-host=" in viewer_response.json()["files"]["dnsmasq/30-reservations.conf"]


def test_cross_site_config_version_detail_returns_404() -> None:
    site_a = create_site("config-api-cross-a")
    site_b = create_site("config-api-cross-b")
    editor = create_user("config-api-cross-editor")
    viewer = create_user("config-api-cross-viewer")
    grant_site_role(editor, site_b, SiteRole.DHCP_EDITOR)
    grant_site_role(viewer, site_a, SiteRole.VIEWER)
    grant_site_role(viewer, site_b, SiteRole.VIEWER)
    config_version_b = create_version_through_api(site_b, editor)

    response = authenticated_client(viewer).get(config_version_detail_url(site_a, config_version_b))

    assert response.status_code == 404


def test_creating_config_version_records_audit_event_and_does_not_deploy() -> None:
    site = create_site("config-api-audit")
    user = create_user("config-api-audit")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(config_version_list_url(site), {"change_summary": "Audit"}, format="json")
    event = AuditEvent.objects.get(event_type="config_version.created")

    assert response.status_code == 201
    assert event.object_type == "ConfigVersion"
    assert event.metadata["rendered_file_paths"] == [
        "dnsmasq/10-ranges.conf",
        "dnsmasq/20-options.conf",
        "dnsmasq/30-reservations.conf",
        "dnsmasq/40-hosts.conf",
    ]
    assert not AuditEvent.objects.exclude(event_type="config_version.created").exists()


def test_rendered_files_do_not_include_obvious_secret_values() -> None:
    site = create_site("config-api-safe-output")
    user = create_user("config-api-safe-output")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)
    config_version = create_version_through_api(site, user)

    response = authenticated_client(user).get(rendered_files_url(site, config_version))
    payload = str(response.json()).lower()

    assert response.status_code == 200
    for forbidden in ["password", "token", "secret", "cookie", "session"]:
        assert forbidden not in payload
