from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import AuditEvent, SiteRole

from .factories import create_site, create_user
from .ipam_helpers import (
    authenticated_client,
    create_pool,
    create_reservation,
    create_subnet,
    grant_site_role,
    pool_detail_url,
    pool_list_url,
    reservation_detail_url,
    reservation_list_url,
    subnet_detail_url,
    subnet_list_url,
)


pytestmark = pytest.mark.django_db


def test_inactive_user_cannot_list_or_mutate_dhcp_ipam_endpoints() -> None:
    site = create_site("dhcp-security-inactive")
    subnet = create_subnet(site)
    pool = create_pool(subnet)
    reservation = create_reservation(subnet)
    inactive = create_user("dhcp-security-inactive", is_active=False)
    grant_site_role(inactive, site, SiteRole.DHCP_EDITOR)
    client = authenticated_client(inactive)

    assert client.get(subnet_list_url(site)).status_code == 404
    assert client.post(subnet_list_url(site), {"name": "LAN", "cidr": "192.168.20.0/24"}, format="json").status_code == 404
    assert client.get(pool_list_url(subnet)).status_code == 404
    assert client.patch(pool_detail_url(subnet, pool), {"enabled": False}, format="json").status_code == 404
    assert client.get(reservation_list_url(subnet)).status_code == 404
    assert client.delete(reservation_detail_url(subnet, reservation)).status_code == 404


def test_inaccessible_site_and_subnet_objects_return_404() -> None:
    site = create_site("dhcp-security-hidden")
    subnet = create_subnet(site)
    pool = create_pool(subnet)
    reservation = create_reservation(subnet)
    user = create_user("dhcp-security-hidden")
    client = authenticated_client(user)

    assert client.get(subnet_list_url(site)).status_code == 404
    assert client.get(subnet_detail_url(site, subnet)).status_code == 404
    assert client.get(pool_list_url(subnet)).status_code == 404
    assert client.get(pool_detail_url(subnet, pool)).status_code == 404
    assert client.get(reservation_list_url(subnet)).status_code == 404
    assert client.get(reservation_detail_url(subnet, reservation)).status_code == 404


@pytest.mark.parametrize(
    ("method", "url_name", "payload"),
    [
        ("post", "subnet-list", {"name": "LAN", "cidr": "192.168.20.0/24"}),
        ("patch", "subnet-detail", {"name": "Nope"}),
        ("post", "pool-list", {"name": "Pool", "start_ip": "192.168.10.160", "end_ip": "192.168.10.170"}),
        ("patch", "pool-detail", {"enabled": False}),
        ("post", "reservation-list", {"hostname": "host-2", "mac_address": "aa:bb:cc:dd:ee:02", "ip_address": "192.168.10.43"}),
        ("patch", "reservation-detail", {"description": "Nope"}),
    ],
)
def test_viewer_receives_403_on_mutation_for_visible_object(method: str, url_name: str, payload: dict[str, object]) -> None:
    site = create_site(f"dhcp-security-viewer-{url_name}")
    subnet = create_subnet(site)
    pool = create_pool(subnet)
    reservation = create_reservation(subnet)
    user = create_user(f"dhcp-security-viewer-{url_name}")
    grant_site_role(user, site, SiteRole.VIEWER)
    client = authenticated_client(user)

    urls = {
        "subnet-list": subnet_list_url(site),
        "subnet-detail": subnet_detail_url(site, subnet),
        "pool-list": pool_list_url(subnet),
        "pool-detail": pool_detail_url(subnet, pool),
        "reservation-list": reservation_list_url(subnet),
        "reservation-detail": reservation_detail_url(subnet, reservation),
    }
    response = getattr(client, method)(urls[url_name], payload, format="json")

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("subnet", {"name": "LAN", "cidr": "192.168.20.0/24", "site": "ignored"}),
        ("subnet", {"name": "LAN", "cidr": "192.168.20.0/24", "organization": "ignored"}),
        ("pool", {"name": "Pool", "start_ip": "192.168.10.160", "end_ip": "192.168.10.170", "subnet": "ignored"}),
        ("pool", {"name": "Pool", "start_ip": "192.168.10.160", "end_ip": "192.168.10.170", "site": "ignored"}),
        ("reservation", {"hostname": "host-2", "mac_address": "aa:bb:cc:dd:ee:02", "ip_address": "192.168.10.43", "subnet": "ignored"}),
        ("reservation", {"hostname": "host-2", "mac_address": "aa:bb:cc:dd:ee:02", "ip_address": "192.168.10.43", "site": "ignored"}),
    ],
)
def test_mutation_endpoints_do_not_accept_parent_override_fields(endpoint: str, payload: dict[str, object]) -> None:
    site = create_site(f"dhcp-security-parent-{endpoint}-{list(payload)[-1]}")
    subnet = create_subnet(site)
    user = create_user(f"dhcp-security-parent-{endpoint}-{list(payload)[-1]}")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)
    client = authenticated_client(user)

    urls = {
        "subnet": subnet_list_url(site),
        "pool": pool_list_url(subnet),
        "reservation": reservation_list_url(subnet),
    }
    response = client.post(urls[endpoint], payload, format="json")

    assert response.status_code == 400
    assert list(payload)[-1] in response.json()


def test_audit_metadata_does_not_include_sensitive_request_fields() -> None:
    site = create_site("dhcp-security-audit")
    subnet = create_subnet(site)
    user = create_user("dhcp-security-audit")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        reservation_list_url(subnet),
        {
            "hostname": "host-2",
            "mac_address": "aa:bb:cc:dd:ee:02",
            "ip_address": "192.168.10.43",
            "password": "do-not-record",
            "token": "do-not-record",
        },
        format="json",
    )

    assert response.status_code == 400
    assert AuditEvent.objects.filter(event_type="dhcp_reservation.created").count() == 0

    good_response = authenticated_client(user).post(
        reservation_list_url(subnet),
        {"hostname": "host-2", "mac_address": "aa:bb:cc:dd:ee:02", "ip_address": "192.168.10.43"},
        format="json",
    )

    event = AuditEvent.objects.get(event_type="dhcp_reservation.created")
    metadata_text = str(event.metadata).lower()
    assert good_response.status_code == 201
    for forbidden_key in ["password", "token", "session", "cookie", "header"]:
        assert forbidden_key not in metadata_text


def test_no_public_anonymous_dhcp_table_endpoint_exists() -> None:
    client = APIClient()

    assert client.get("/public/example/").status_code == 404
    assert client.get("/api/v1/public/example/").status_code == 404
