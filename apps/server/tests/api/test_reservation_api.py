from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import AuditEvent, OrganizationRole, SiteRole
from managed_dhcp_server.ipam.models import DHCPReservation

from .factories import create_site, create_user
from .ipam_helpers import (
    authenticated_client,
    create_reservation,
    create_subnet,
    grant_organization_role,
    grant_site_role,
    reservation_detail_url,
    reservation_list_url,
)


pytestmark = pytest.mark.django_db


def test_anonymous_cannot_list_reservations() -> None:
    subnet = create_subnet(create_site("reservation-anonymous"))

    response = APIClient().get(reservation_list_url(subnet))

    assert response.status_code in {401, 403}


def test_site_viewer_can_list_reservations() -> None:
    site = create_site("reservation-viewer-list")
    subnet = create_subnet(site)
    reservation = create_reservation(subnet)
    user = create_user("reservation-viewer-list")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).get(reservation_list_url(subnet))

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(reservation.id)


def test_dhcp_editor_and_organization_admin_can_create_reservation() -> None:
    editor_site = create_site("reservation-editor-create")
    admin_site = create_site("reservation-admin-create")
    editor_subnet = create_subnet(editor_site, "192.168.10.0/24")
    admin_subnet = create_subnet(admin_site, "192.168.20.0/24")
    editor = create_user("reservation-editor-create")
    admin = create_user("reservation-admin-create")
    grant_site_role(editor, editor_site, SiteRole.DHCP_EDITOR)
    grant_organization_role(admin, admin_site, OrganizationRole.ADMIN)

    editor_response = authenticated_client(editor).post(
        reservation_list_url(editor_subnet),
        {
            "hostname": "printer-1",
            "mac_address": "AA-BB-CC-DD-EE-FF",
            "ip_address": "192.168.10.42",
            "description": "Office printer",
        },
        format="json",
    )
    admin_response = authenticated_client(admin).post(
        reservation_list_url(admin_subnet),
        {
            "hostname": "printer-2",
            "mac_address": "aa:bb:cc:dd:ee:02",
            "ip_address": "192.168.20.42",
            "description": "Lab printer",
        },
        format="json",
    )

    assert editor_response.status_code == 201
    assert admin_response.status_code == 201
    assert editor_response.json()["mac_address"] == "aa:bb:cc:dd:ee:ff"
    assert DHCPReservation.objects.filter(subnet=editor_subnet, hostname="printer-1").exists()
    assert DHCPReservation.objects.filter(subnet=admin_subnet, hostname="printer-2").exists()


@pytest.mark.parametrize("site_role", [SiteRole.VIEWER, SiteRole.PUBLIC_PUBLISHER, SiteRole.DEVICE_INSTALLER])
def test_non_editor_site_roles_cannot_create_reservation(site_role: str) -> None:
    site = create_site(f"reservation-denied-{site_role}")
    subnet = create_subnet(site)
    user = create_user(f"reservation-denied-{site_role}")
    grant_site_role(user, site, site_role)

    response = authenticated_client(user).post(
        reservation_list_url(subnet),
        {"hostname": "printer-1", "mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "192.168.10.42"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"hostname": "printer-1", "mac_address": "not-a-mac", "ip_address": "192.168.10.42"}, "mac_address"),
        ({"hostname": "printer-1", "mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "192.168.11.42"}, "ip_address"),
        ({"hostname": "bad_name", "mac_address": "aa:bb:cc:dd:ee:ff", "ip_address": "192.168.10.42"}, "hostname"),
    ],
)
def test_create_reservation_validates_mac_ip_and_hostname(payload: dict[str, str], field: str) -> None:
    site = create_site(f"reservation-validation-{field}")
    subnet = create_subnet(site)
    user = create_user(f"reservation-validation-{field}")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(reservation_list_url(subnet), payload, format="json")

    assert response.status_code == 400
    assert field in response.json()


def test_create_reservation_rejects_duplicate_ip_in_same_subnet() -> None:
    site = create_site("reservation-duplicate-ip")
    subnet = create_subnet(site)
    create_reservation(subnet, ip_address="192.168.10.42", mac_address="aa:bb:cc:dd:ee:01")
    user = create_user("reservation-duplicate-ip")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        reservation_list_url(subnet),
        {"hostname": "printer-2", "mac_address": "aa:bb:cc:dd:ee:02", "ip_address": "192.168.10.42"},
        format="json",
    )

    assert response.status_code == 400
    assert "ip_address" in response.json()


def test_create_reservation_rejects_duplicate_enabled_mac_in_same_site() -> None:
    site = create_site("reservation-duplicate-mac")
    subnet_a = create_subnet(site, "192.168.10.0/24")
    subnet_b = create_subnet(site, "192.168.20.0/24")
    create_reservation(subnet_a, ip_address="192.168.10.42", mac_address="aa:bb:cc:dd:ee:ff")
    user = create_user("reservation-duplicate-mac")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        reservation_list_url(subnet_b),
        {"hostname": "printer-2", "mac_address": "AA:BB:CC:DD:EE:FF", "ip_address": "192.168.20.42"},
        format="json",
    )

    assert response.status_code == 400
    assert "mac_address" in response.json()


def test_same_mac_allowed_in_different_site() -> None:
    site_a = create_site("reservation-same-mac-a")
    site_b = create_site("reservation-same-mac-b")
    subnet_a = create_subnet(site_a, "192.168.10.0/24")
    subnet_b = create_subnet(site_b, "192.168.10.0/24")
    create_reservation(subnet_a, ip_address="192.168.10.42", mac_address="aa:bb:cc:dd:ee:ff")
    user = create_user("reservation-same-mac")
    grant_site_role(user, site_b, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        reservation_list_url(subnet_b),
        {"hostname": "printer-2", "mac_address": "AA:BB:CC:DD:EE:FF", "ip_address": "192.168.10.43"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["mac_address"] == "aa:bb:cc:dd:ee:ff"


def test_patch_can_update_reservation_fields_and_records_audit_event() -> None:
    site = create_site("reservation-patch")
    subnet = create_subnet(site)
    reservation = create_reservation(subnet)
    user = create_user("reservation-patch")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).patch(
        reservation_detail_url(subnet, reservation),
        {
            "hostname": "printer-renamed",
            "description": "Updated description",
            "ip_address": "192.168.10.43",
            "mac_address": "aa-bb-cc-dd-ee-01",
            "enabled": False,
        },
        format="json",
    )

    reservation.refresh_from_db()
    event = AuditEvent.objects.get(event_type="dhcp_reservation.updated")
    assert response.status_code == 200
    assert reservation.hostname == "printer-renamed"
    assert reservation.mac_address == "aa:bb:cc:dd:ee:01"
    assert reservation.enabled is False
    assert event.metadata["old"]["hostname"] == "printer-1"
    assert event.metadata["new"]["hostname"] == "printer-renamed"
    assert event.metadata["old"]["mac_address"] == "aa:bb:cc:dd:ee:ff"
    assert event.metadata["new"]["mac_address"] == "aa:bb:cc:dd:ee:01"


def test_delete_disables_reservation_and_records_audit_event() -> None:
    site = create_site("reservation-disable")
    subnet = create_subnet(site)
    reservation = create_reservation(subnet)
    user = create_user("reservation-disable")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).delete(reservation_detail_url(subnet, reservation))

    reservation.refresh_from_db()
    event = AuditEvent.objects.get(event_type="dhcp_reservation.disabled")
    assert response.status_code == 204
    assert reservation.enabled is False
    assert event.object_id == str(reservation.id)
    assert event.metadata["ip_address"] == "192.168.10.42"
    assert event.metadata["mac_address"] == "aa:bb:cc:dd:ee:ff"
    assert event.metadata["old"]["enabled"] is True
    assert event.metadata["new"]["enabled"] is False


def test_disabled_reservation_remains_visible_in_authenticated_list() -> None:
    site = create_site("reservation-disabled-visible")
    subnet = create_subnet(site)
    reservation = create_reservation(subnet)
    reservation.enabled = False
    reservation.full_clean()
    reservation.save()
    user = create_user("reservation-disabled-visible")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).get(reservation_list_url(subnet))

    assert response.status_code == 200
    assert response.json()[0]["enabled"] is False


def test_cross_subnet_reservation_detail_returns_404() -> None:
    site = create_site("reservation-cross")
    subnet_a = create_subnet(site, "192.168.10.0/24")
    subnet_b = create_subnet(site, "192.168.20.0/24")
    reservation_b = create_reservation(subnet_b, ip_address="192.168.20.42")
    user = create_user("reservation-cross")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).get(reservation_detail_url(subnet_a, reservation_b))

    assert response.status_code == 404


def test_post_cannot_override_subnet_through_body() -> None:
    site = create_site("reservation-parent-body")
    subnet = create_subnet(site, "192.168.10.0/24")
    other_subnet = create_subnet(site, "192.168.20.0/24")
    user = create_user("reservation-parent-body")
    grant_site_role(user, site, SiteRole.DHCP_EDITOR)

    response = authenticated_client(user).post(
        reservation_list_url(subnet),
        {
            "hostname": "printer-1",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "ip_address": "192.168.10.42",
            "subnet": str(other_subnet.id),
        },
        format="json",
    )

    assert response.status_code == 400
    assert "subnet" in response.json()


def test_reservation_serializer_does_not_expose_user_data() -> None:
    site = create_site("reservation-no-user-data")
    subnet = create_subnet(site)
    create_reservation(subnet)
    user = create_user("reservation-no-user-data")
    grant_site_role(user, site, SiteRole.VIEWER)

    response = authenticated_client(user).get(reservation_list_url(subnet))

    payload = response.json()[0]
    assert response.status_code == 200
    assert "user" not in payload
    assert "password" not in payload
    assert "groups" not in payload
    assert "user_permissions" not in payload
