from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import AuditEvent, OrganizationRole, SiteRole
from managed_dhcp_server.ipam.models import DHCPPool, IPv4Subnet

from .factories import create_site, create_user
from .ipam_helpers import (
    authenticated_client,
    create_pool,
    create_reservation,
    create_subnet,
    grant_organization_role,
    grant_site_role,
    subnet_detail_url,
    subnet_list_url,
)


pytestmark = pytest.mark.django_db


def test_anonymous_cannot_list_subnets() -> None:
    site = create_site("subnet-anonymous")

    response = APIClient().get(subnet_list_url(site))

    assert response.status_code in {401, 403}


def test_unrelated_user_cannot_list_subnets() -> None:
    site = create_site("subnet-unrelated")
    user = create_user("subnet-unrelated")

    response = authenticated_client(user).get(subnet_list_url(site))

    assert response.status_code == 404


def test_site_viewer_and_dhcp_editor_can_list_subnets() -> None:
    site = create_site("subnet-visible")
    subnet = create_subnet(site)
    viewer = create_user("subnet-visible-viewer")
    editor = create_user("subnet-visible-editor")
    grant_site_role(viewer, site, SiteRole.VIEWER)
    grant_site_role(editor, site, SiteRole.DHCP_EDITOR)

    viewer_response = authenticated_client(viewer).get(subnet_list_url(site))
    editor_response = authenticated_client(editor).get(subnet_list_url(site))

    assert viewer_response.status_code == 200
    assert editor_response.status_code == 200
    assert viewer_response.json()[0]["id"] == str(subnet.id)


def test_dhcp_editor_and_organization_admin_can_create_subnet() -> None:
    editor_site = create_site("subnet-editor-create")
    admin_site = create_site("subnet-admin-create")
    editor = create_user("subnet-editor-create")
    admin = create_user("subnet-admin-create")
    grant_site_role(editor, editor_site, SiteRole.DHCP_EDITOR)
    grant_organization_role(admin, admin_site, OrganizationRole.ADMIN)

    editor_response = authenticated_client(editor).post(
        subnet_list_url(editor_site),
        {"name": "LAN", "cidr": "192.168.30.0/24", "gateway": "192.168.30.1", "dns_servers": ["192.168.30.1"]},
        format="json",
    )
    admin_response = authenticated_client(admin).post(
        subnet_list_url(admin_site),
        {"name": "LAN", "cidr": "192.168.40.0/24"},
        format="json",
    )

    assert editor_response.status_code == 201
    assert admin_response.status_code == 201
    assert IPv4Subnet.objects.filter(site=editor_site, cidr="192.168.30.0/24").exists()
    assert IPv4Subnet.objects.filter(site=admin_site, cidr="192.168.40.0/24").exists()


@pytest.mark.parametrize(
    ("role_model", "role"),
    [
        ("organization", OrganizationRole.VIEWER),
        ("site", SiteRole.VIEWER),
    ],
)
def test_viewers_cannot_create_subnet(role_model: str, role: str) -> None:
    site = create_site(f"subnet-viewer-denied-{role_model}")
    user = create_user(f"subnet-viewer-denied-{role_model}")
    if role_model == "organization":
        grant_organization_role(user, site, role)
    else:
        grant_site_role(user, site, role)

    response = authenticated_client(user).post(
        subnet_list_url(site),
        {"name": "LAN", "cidr": "192.168.50.0/24"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"name": "Bad", "cidr": "not-a-cidr"}, "cidr"),
        ({"name": "Bad", "cidr": "192.168.60.0/24", "gateway": "192.168.61.1"}, "gateway"),
    ],
)
def test_create_subnet_validates_cidr_and_gateway(payload: dict[str, object], field: str) -> None:
    site = create_site(f"subnet-validation-{field}")
    user = create_user(f"subnet-validation-{field}")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(subnet_list_url(site), payload, format="json")

    assert response.status_code == 400
    assert field in response.json()


def test_update_subnet_records_audit_event() -> None:
    site = create_site("subnet-audit-update")
    subnet = create_subnet(site)
    user = create_user("subnet-audit-update")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).patch(subnet_detail_url(site, subnet), {"name": "Updated LAN"}, format="json")

    subnet.refresh_from_db()
    event = AuditEvent.objects.get(event_type="ipv4_subnet.updated")
    assert response.status_code == 200
    assert subnet.name == "Updated LAN"
    assert event.actor == user
    assert event.site == site
    assert event.object_id == str(subnet.id)
    assert event.metadata["old"]["name"] == "Office LAN"
    assert event.metadata["new"]["name"] == "Updated LAN"


def test_delete_empty_subnet_records_audit_event() -> None:
    site = create_site("subnet-delete-empty")
    subnet = create_subnet(site)
    user = create_user("subnet-delete-empty")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).delete(subnet_detail_url(site, subnet))

    event = AuditEvent.objects.get(event_type="ipv4_subnet.deleted")
    assert response.status_code == 204
    assert not IPv4Subnet.objects.filter(pk=subnet.pk).exists()
    assert event.object_id == str(subnet.id)


@pytest.mark.parametrize("child_kind", ["pool", "reservation"])
def test_delete_subnet_with_children_is_rejected(child_kind: str) -> None:
    site = create_site(f"subnet-delete-child-{child_kind}")
    subnet = create_subnet(site)
    if child_kind == "pool":
        create_pool(subnet)
    else:
        create_reservation(subnet)
    user = create_user(f"subnet-delete-child-{child_kind}")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).delete(subnet_detail_url(site, subnet))

    assert response.status_code == 400
    assert IPv4Subnet.objects.filter(pk=subnet.pk).exists()


def test_cross_site_subnet_detail_returns_404() -> None:
    site_a = create_site("subnet-cross-a")
    site_b = create_site("subnet-cross-b")
    subnet_b = create_subnet(site_b)
    user = create_user("subnet-cross")
    grant_site_role(user, site_a, SiteRole.VIEWER)
    grant_site_role(user, site_b, SiteRole.VIEWER)

    response = authenticated_client(user).get(subnet_detail_url(site_a, subnet_b))

    assert response.status_code == 404


def test_post_cannot_override_site_through_body() -> None:
    site = create_site("subnet-parent-body")
    other_site = create_site("subnet-parent-body-other")
    user = create_user("subnet-parent-body")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        subnet_list_url(site),
        {"name": "LAN", "cidr": "192.168.70.0/24", "site": str(other_site.id)},
        format="json",
    )

    assert response.status_code == 400
    assert "site" in response.json()
