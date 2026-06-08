import ipaddress

import pytest
from django.core.exceptions import ValidationError

from managed_dhcp_server.ipam.models import DHCPPool, DHCPReservation, IPv4Subnet, Organization, Site


pytestmark = pytest.mark.django_db


def create_site(slug_suffix: str = "main") -> Site:
    organization = Organization.objects.create(name=f"Example Org {slug_suffix}", slug=f"example-{slug_suffix}")
    return Site.objects.create(organization=organization, name=f"Main Site {slug_suffix}", slug="main")


def create_subnet(site: Site | None = None, cidr: str = "192.168.10.0/24") -> IPv4Subnet:
    site = site or create_site()
    network = ipaddress.ip_network(cidr)
    gateway = str(network.network_address + 1)
    subnet = IPv4Subnet(
        site=site,
        name="Office LAN",
        cidr=cidr,
        gateway=gateway,
        dns_servers=[gateway, "8.8.8.8"],
    )
    subnet.full_clean()
    subnet.save()
    return subnet


def test_can_create_organization_site_and_subnet() -> None:
    site = create_site()
    subnet = create_subnet(site=site)

    assert subnet.site == site
    assert subnet.cidr == "192.168.10.0/24"
    assert subnet.default_lease_time_seconds == 43_200


def test_subnet_rejects_invalid_cidr() -> None:
    subnet = IPv4Subnet(site=create_site(), name="Bad", cidr="not-a-cidr")

    with pytest.raises(ValidationError, match="valid IPv4 CIDR"):
        subnet.full_clean()


def test_subnet_rejects_gateway_outside_subnet() -> None:
    subnet = IPv4Subnet(site=create_site(), name="Bad Gateway", cidr="192.168.10.0/24", gateway="192.168.11.1")

    with pytest.raises(ValidationError, match="Gateway must be inside"):
        subnet.full_clean()


def test_pool_accepts_valid_range() -> None:
    pool = DHCPPool(subnet=create_subnet(), name="Main Pool", start_ip="192.168.10.100", end_ip="192.168.10.150")

    pool.full_clean()
    pool.save()

    assert pool.enabled is True


def test_pool_rejects_start_after_end() -> None:
    pool = DHCPPool(subnet=create_subnet(), name="Bad Pool", start_ip="192.168.10.150", end_ip="192.168.10.100")

    with pytest.raises(ValidationError, match="Start IP"):
        pool.full_clean()


def test_pool_rejects_range_outside_subnet() -> None:
    pool = DHCPPool(subnet=create_subnet(), name="Bad Pool", start_ip="192.168.11.10", end_ip="192.168.11.20")

    with pytest.raises(ValidationError, match="inside the subnet"):
        pool.full_clean()


def test_pool_rejects_overlapping_pool_in_same_subnet() -> None:
    subnet = create_subnet()
    first = DHCPPool(subnet=subnet, name="First", start_ip="192.168.10.100", end_ip="192.168.10.150")
    first.full_clean()
    first.save()

    second = DHCPPool(subnet=subnet, name="Second", start_ip="192.168.10.140", end_ip="192.168.10.160")

    with pytest.raises(ValidationError, match="overlaps"):
        second.full_clean()


def test_reservation_normalizes_mac() -> None:
    reservation = DHCPReservation(
        subnet=create_subnet(),
        hostname="printer-1",
        mac_address="AA-BB-CC-DD-EE-FF",
        ip_address="192.168.10.42",
    )

    reservation.full_clean()
    reservation.save()

    assert reservation.mac_address == "aa:bb:cc:dd:ee:ff"


def test_reservation_rejects_ip_outside_subnet() -> None:
    reservation = DHCPReservation(
        subnet=create_subnet(),
        hostname="printer-1",
        mac_address="aa:bb:cc:dd:ee:ff",
        ip_address="192.168.11.42",
    )

    with pytest.raises(ValidationError, match="inside the subnet"):
        reservation.full_clean()


def test_reservation_rejects_duplicate_ip_in_same_subnet() -> None:
    subnet = create_subnet()
    first = DHCPReservation(subnet=subnet, hostname="printer-1", mac_address="aa:bb:cc:dd:ee:01", ip_address="192.168.10.42")
    first.full_clean()
    first.save()

    second = DHCPReservation(subnet=subnet, hostname="printer-2", mac_address="aa:bb:cc:dd:ee:02", ip_address="192.168.10.42")

    with pytest.raises(ValidationError, match="already exists"):
        second.full_clean()


def test_reservation_rejects_duplicate_enabled_mac_in_same_site() -> None:
    site = create_site()
    subnet_a = create_subnet(site=site, cidr="192.168.10.0/24")
    subnet_b = create_subnet(site=site, cidr="192.168.20.0/24")
    first = DHCPReservation(subnet=subnet_a, hostname="printer-1", mac_address="aa:bb:cc:dd:ee:ff", ip_address="192.168.10.42")
    first.full_clean()
    first.save()

    second = DHCPReservation(subnet=subnet_b, hostname="printer-2", mac_address="AA:BB:CC:DD:EE:FF", ip_address="192.168.20.42")

    with pytest.raises(ValidationError, match="unique within a site"):
        second.full_clean()


def test_reservation_allows_same_mac_in_different_site() -> None:
    subnet_a = create_subnet(site=create_site("a"), cidr="192.168.10.0/24")
    subnet_b = create_subnet(site=create_site("b"), cidr="192.168.10.0/24")
    first = DHCPReservation(subnet=subnet_a, hostname="printer-1", mac_address="aa:bb:cc:dd:ee:ff", ip_address="192.168.10.42")
    first.full_clean()
    first.save()

    second = DHCPReservation(subnet=subnet_b, hostname="printer-2", mac_address="AA:BB:CC:DD:EE:FF", ip_address="192.168.10.43")
    second.full_clean()
    second.save()

    assert second.mac_address == "aa:bb:cc:dd:ee:ff"
