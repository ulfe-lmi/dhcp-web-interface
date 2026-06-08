from __future__ import annotations

import ipaddress
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .validators import (
    ipv4_address_in_cidr,
    normalize_mac_address,
    validate_hostname,
    validate_ipv4_address,
    validate_ipv4_cidr,
)


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Site(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sites")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "slug"], name="unique_site_slug_per_organization"),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.slug}"


class IPv4Subnet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="ipv4_subnets")
    name = models.CharField(max_length=255)
    cidr = models.CharField(max_length=43)
    gateway = models.GenericIPAddressField(protocol="IPv4", blank=True, null=True)
    dns_servers = models.JSONField(default=list, blank=True)
    default_lease_time_seconds = models.PositiveIntegerField(default=43_200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["site__name", "cidr"]
        constraints = [
            models.UniqueConstraint(fields=["site", "cidr"], name="unique_ipv4_subnet_cidr_per_site"),
        ]

    def clean(self) -> None:
        errors: dict[str, list[ValidationError]] = {}

        try:
            self.cidr = validate_ipv4_cidr(self.cidr)
        except ValidationError as exc:
            errors.setdefault("cidr", []).append(exc)

        if self.gateway:
            try:
                self.gateway = validate_ipv4_address(self.gateway)
                if not errors.get("cidr") and not ipv4_address_in_cidr(self.gateway, self.cidr):
                    errors.setdefault("gateway", []).append(ValidationError("Gateway must be inside the subnet."))
            except ValidationError as exc:
                errors.setdefault("gateway", []).append(exc)

        if not isinstance(self.dns_servers, list):
            errors.setdefault("dns_servers", []).append(ValidationError("DNS servers must be a list of IPv4 addresses."))
        else:
            normalized_dns_servers: list[str] = []
            for dns_server in self.dns_servers:
                try:
                    normalized_dns_servers.append(validate_ipv4_address(dns_server))
                except ValidationError as exc:
                    errors.setdefault("dns_servers", []).append(exc)
            self.dns_servers = normalized_dns_servers

        if self.default_lease_time_seconds <= 0:
            errors.setdefault("default_lease_time_seconds", []).append(ValidationError("Default lease time must be positive."))

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.site}: {self.cidr}"


class DHCPPool(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subnet = models.ForeignKey(IPv4Subnet, on_delete=models.CASCADE, related_name="dhcp_pools")
    name = models.CharField(max_length=255)
    start_ip = models.GenericIPAddressField(protocol="IPv4")
    end_ip = models.GenericIPAddressField(protocol="IPv4")
    lease_time_seconds = models.PositiveIntegerField(blank=True, null=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subnet__cidr", "start_ip"]

    def clean(self) -> None:
        errors: dict[str, list[ValidationError]] = {}

        try:
            self.start_ip = validate_ipv4_address(self.start_ip)
        except ValidationError as exc:
            errors.setdefault("start_ip", []).append(exc)

        try:
            self.end_ip = validate_ipv4_address(self.end_ip)
        except ValidationError as exc:
            errors.setdefault("end_ip", []).append(exc)

        if self.lease_time_seconds is not None and self.lease_time_seconds <= 0:
            errors.setdefault("lease_time_seconds", []).append(ValidationError("Lease time must be positive."))

        if errors:
            raise ValidationError(errors)

        start = ipaddress.ip_address(self.start_ip)
        end = ipaddress.ip_address(self.end_ip)

        if start > end:
            errors.setdefault("start_ip", []).append(ValidationError("Start IP must be less than or equal to end IP."))

        if not ipv4_address_in_cidr(self.start_ip, self.subnet.cidr):
            errors.setdefault("start_ip", []).append(ValidationError("Start IP must be inside the subnet."))

        if not ipv4_address_in_cidr(self.end_ip, self.subnet.cidr):
            errors.setdefault("end_ip", []).append(ValidationError("End IP must be inside the subnet."))

        if not errors and self._overlaps_existing_pool(start, end):
            errors.setdefault("__all__", []).append(ValidationError("DHCP pool overlaps another pool in the same subnet."))

        if errors:
            raise ValidationError(errors)

    def _overlaps_existing_pool(self, start: ipaddress.IPv4Address, end: ipaddress.IPv4Address) -> bool:
        existing_pools = DHCPPool.objects.filter(subnet=self.subnet)
        if self.pk:
            existing_pools = existing_pools.exclude(pk=self.pk)

        for pool in existing_pools:
            existing_start = ipaddress.ip_address(pool.start_ip)
            existing_end = ipaddress.ip_address(pool.end_ip)
            if start <= existing_end and end >= existing_start:
                return True

        return False

    def __str__(self) -> str:
        return f"{self.subnet.cidr}: {self.start_ip}-{self.end_ip}"


class DHCPReservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subnet = models.ForeignKey(IPv4Subnet, on_delete=models.CASCADE, related_name="dhcp_reservations")
    hostname = models.CharField(max_length=253)
    mac_address = models.CharField(max_length=17)
    ip_address = models.GenericIPAddressField(protocol="IPv4")
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subnet__cidr", "ip_address"]
        constraints = [
            models.UniqueConstraint(fields=["subnet", "ip_address"], name="unique_reservation_ip_per_subnet"),
        ]

    def clean(self) -> None:
        errors: dict[str, list[ValidationError]] = {}

        try:
            self.hostname = validate_hostname(self.hostname)
        except ValidationError as exc:
            errors.setdefault("hostname", []).append(exc)

        try:
            self.mac_address = normalize_mac_address(self.mac_address)
        except ValidationError as exc:
            errors.setdefault("mac_address", []).append(exc)

        try:
            self.ip_address = validate_ipv4_address(self.ip_address)
        except ValidationError as exc:
            errors.setdefault("ip_address", []).append(exc)

        if not errors.get("ip_address") and not ipv4_address_in_cidr(self.ip_address, self.subnet.cidr):
            errors.setdefault("ip_address", []).append(ValidationError("Reservation IP must be inside the subnet."))

        if not errors.get("ip_address") and self._ip_exists_in_subnet():
            errors.setdefault("ip_address", []).append(ValidationError("Reservation IP already exists in this subnet."))

        if self.enabled and not errors.get("mac_address") and self._enabled_mac_exists_in_site():
            errors.setdefault("mac_address", []).append(ValidationError("Enabled reservation MAC address must be unique within a site."))

        if errors:
            raise ValidationError(errors)

    def save(self, *args: object, **kwargs: object) -> None:
        self.mac_address = normalize_mac_address(self.mac_address)
        super().save(*args, **kwargs)

    def _enabled_mac_exists_in_site(self) -> bool:
        reservations = DHCPReservation.objects.filter(
            enabled=True,
            mac_address=self.mac_address,
            subnet__site=self.subnet.site,
        )
        if self.pk:
            reservations = reservations.exclude(pk=self.pk)

        return reservations.exists()

    def _ip_exists_in_subnet(self) -> bool:
        reservations = DHCPReservation.objects.filter(subnet=self.subnet, ip_address=self.ip_address)
        if self.pk:
            reservations = reservations.exclude(pk=self.pk)

        return reservations.exists()

    def __str__(self) -> str:
        return f"{self.hostname} {self.ip_address}"
