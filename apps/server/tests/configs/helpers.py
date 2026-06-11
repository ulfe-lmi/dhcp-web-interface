from __future__ import annotations

import ipaddress

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.ipam.models import DHCPPool, DHCPReservation, IPv4Subnet, Organization, Site


def create_user(username: str, *, is_active: bool = True, is_superuser: bool = False):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="test-password",
        is_active=is_active,
        is_superuser=is_superuser,
        is_staff=is_superuser,
    )


def create_organization(slug: str = "example") -> Organization:
    return Organization.objects.create(name=f"Example {slug}", slug=slug)


def create_site(slug: str = "main", *, organization: Organization | None = None) -> Site:
    organization = organization or create_organization(f"org-{slug}")
    return Site.objects.create(organization=organization, name=f"Site {slug}", slug=slug)


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
