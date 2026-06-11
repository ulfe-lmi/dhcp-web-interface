from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import AuditEvent, SiteRole
from managed_dhcp_server.ipam.models import DHCPPool

from .factories import create_site, create_user
from .ipam_helpers import (
    authenticated_client,
    create_pool,
    create_subnet,
    grant_site_role,
    pool_detail_url,
    pool_list_url,
)


pytestmark = pytest.mark.django_db


def test_anonymous_cannot_list_pools() -> None:
    subnet = create_subnet(create_site("pool-anonymous"))

    response = APIClient().get(pool_list_url(subnet))

    assert response.status_code in {401, 403}


def test_site_viewer_can_list_pools() -> None:
    site = create_site("pool-viewer-list")
    subnet = create_subnet(site)
    pool = create_pool(subnet)
    user = create_user("pool-viewer-list")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).get(pool_list_url(subnet))

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(pool.id)


def test_dhcp_editor_can_create_pool() -> None:
    site = create_site("pool-editor-create")
    subnet = create_subnet(site)
    user = create_user("pool-editor-create")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        pool_list_url(subnet),
        {"name": "Pool", "start_ip": "192.168.10.100", "end_ip": "192.168.10.120"},
        format="json",
    )

    assert response.status_code == 201
    assert DHCPPool.objects.filter(subnet=subnet, start_ip="192.168.10.100", end_ip="192.168.10.120").exists()


def test_site_viewer_cannot_create_pool() -> None:
    site = create_site("pool-viewer-create")
    subnet = create_subnet(site)
    user = create_user("pool-viewer-create")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).post(
        pool_list_url(subnet),
        {"name": "Pool", "start_ip": "192.168.10.100", "end_ip": "192.168.10.120"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"name": "Bad", "start_ip": "192.168.11.10", "end_ip": "192.168.11.20"}, "start_ip"),
        ({"name": "Bad", "start_ip": "192.168.10.150", "end_ip": "192.168.10.100"}, "start_ip"),
    ],
)
def test_create_pool_validates_range(payload: dict[str, str], field: str) -> None:
    site = create_site(f"pool-validation-{field}-{payload['start_ip'].replace('.', '-')}")
    subnet = create_subnet(site)
    user = create_user(f"pool-validation-{field}-{payload['end_ip'].replace('.', '-')}")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(pool_list_url(subnet), payload, format="json")

    assert response.status_code == 400
    assert field in response.json()


def test_create_pool_rejects_overlapping_pool() -> None:
    site = create_site("pool-overlap")
    subnet = create_subnet(site)
    create_pool(subnet, start_ip="192.168.10.100", end_ip="192.168.10.150")
    user = create_user("pool-overlap")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        pool_list_url(subnet),
        {"name": "Overlap", "start_ip": "192.168.10.140", "end_ip": "192.168.10.160"},
        format="json",
    )

    assert response.status_code == 400
    assert "__all__" in response.json()


def test_update_pool_records_audit_event() -> None:
    site = create_site("pool-audit-update")
    subnet = create_subnet(site)
    pool = create_pool(subnet)
    user = create_user("pool-audit-update")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).patch(pool_detail_url(subnet, pool), {"end_ip": "192.168.10.160"}, format="json")

    pool.refresh_from_db()
    event = AuditEvent.objects.get(event_type="dhcp_pool.updated")
    assert response.status_code == 200
    assert pool.end_ip == "192.168.10.160"
    assert event.object_id == str(pool.id)
    assert event.metadata["old"]["end_ip"] == "192.168.10.150"
    assert event.metadata["new"]["end_ip"] == "192.168.10.160"


def test_delete_disables_pool_and_records_audit_event() -> None:
    site = create_site("pool-disable")
    subnet = create_subnet(site)
    pool = create_pool(subnet)
    user = create_user("pool-disable")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).delete(pool_detail_url(subnet, pool))

    pool.refresh_from_db()
    event = AuditEvent.objects.get(event_type="dhcp_pool.disabled")
    assert response.status_code == 204
    assert pool.enabled is False
    assert event.object_id == str(pool.id)
    assert event.metadata["old"]["enabled"] is True
    assert event.metadata["new"]["enabled"] is False


def test_disabled_pool_remains_visible_in_authenticated_list() -> None:
    site = create_site("pool-disabled-visible")
    subnet = create_subnet(site)
    pool = create_pool(subnet)
    pool.enabled = False
    pool.full_clean()
    pool.save()
    user = create_user("pool-disabled-visible")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).get(pool_list_url(subnet))

    assert response.status_code == 200
    assert response.json()[0]["enabled"] is False


def test_cross_subnet_pool_detail_returns_404() -> None:
    site = create_site("pool-cross")
    subnet_a = create_subnet(site, "192.168.10.0/24")
    subnet_b = create_subnet(site, "192.168.20.0/24")
    pool_b = create_pool(subnet_b, start_ip="192.168.20.100", end_ip="192.168.20.120")
    user = create_user("pool-cross")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).get(pool_detail_url(subnet_a, pool_b))

    assert response.status_code == 404


def test_post_cannot_override_subnet_through_body() -> None:
    site = create_site("pool-parent-body")
    subnet = create_subnet(site, "192.168.10.0/24")
    other_subnet = create_subnet(site, "192.168.20.0/24")
    user = create_user("pool-parent-body")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        pool_list_url(subnet),
        {"name": "Pool", "start_ip": "192.168.10.100", "end_ip": "192.168.10.120", "subnet": str(other_subnet.id)},
        format="json",
    )

    assert response.status_code == 400
    assert "subnet" in response.json()
