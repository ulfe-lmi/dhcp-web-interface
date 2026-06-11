from __future__ import annotations

import ipaddress

from rest_framework.test import APIClient

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.ipam.models import DHCPPool, DHCPReservation, IPv4Subnet, Site


def authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def create_subnet(site: Site, cidr: str = "192.168.10.0/24", *, name: str = "Office LAN") -> IPv4Subnet:
    network = ipaddress.ip_network(cidr)
    gateway = str(network.network_address + 1)
    subnet = IPv4Subnet(
        site=site,
        name=name,
        cidr=cidr,
        gateway=gateway,
        dns_servers=[gateway, "8.8.8.8"],
    )
    subnet.full_clean()
    subnet.save()
    return subnet


def create_pool(subnet: IPv4Subnet, *, start_ip: str = "192.168.10.100", end_ip: str = "192.168.10.150") -> DHCPPool:
    pool = DHCPPool(subnet=subnet, name="Main Pool", start_ip=start_ip, end_ip=end_ip)
    pool.full_clean()
    pool.save()
    return pool


def create_reservation(
    subnet: IPv4Subnet,
    *,
    hostname: str = "printer-1",
    mac_address: str = "aa:bb:cc:dd:ee:ff",
    ip_address: str = "192.168.10.42",
    description: str = "Printer",
) -> DHCPReservation:
    reservation = DHCPReservation(
        subnet=subnet,
        hostname=hostname,
        mac_address=mac_address,
        ip_address=ip_address,
        description=description,
    )
    reservation.full_clean()
    reservation.save()
    return reservation


def grant_organization_role(user, site: Site, role: str = OrganizationRole.ADMIN) -> None:
    OrganizationMembership.objects.create(organization=site.organization, user=user, role=role)


def grant_site_role(user, site: Site, role: str = SiteRole.DHCP_EDITOR) -> None:
    SiteMembership.objects.create(site=site, user=user, role=role)


def subnet_list_url(site: Site) -> str:
    return f"/api/v1/sites/{site.id}/subnets/"


def subnet_detail_url(site: Site, subnet: IPv4Subnet) -> str:
    return f"/api/v1/sites/{site.id}/subnets/{subnet.id}/"


def pool_list_url(subnet: IPv4Subnet) -> str:
    return f"/api/v1/subnets/{subnet.id}/pools/"


def pool_detail_url(subnet: IPv4Subnet, pool: DHCPPool) -> str:
    return f"/api/v1/subnets/{subnet.id}/pools/{pool.id}/"


def reservation_list_url(subnet: IPv4Subnet) -> str:
    return f"/api/v1/subnets/{subnet.id}/reservations/"


def reservation_detail_url(subnet: IPv4Subnet, reservation: DHCPReservation) -> str:
    return f"/api/v1/subnets/{subnet.id}/reservations/{reservation.id}/"
