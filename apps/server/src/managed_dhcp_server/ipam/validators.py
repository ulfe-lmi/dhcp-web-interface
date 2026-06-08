from __future__ import annotations

import ipaddress
import re
from typing import Final

from django.core.exceptions import ValidationError

_MAC_HEX_RE: Final = re.compile(r"^[0-9a-fA-F]{12}$")
_HOST_LABEL_RE: Final = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def normalize_mac_address(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("MAC address must be a string.")

    compact = value.strip().replace(":", "").replace("-", "").replace(".", "")
    if not _MAC_HEX_RE.fullmatch(compact):
        raise ValidationError("Enter a valid MAC address.")

    lower = compact.lower()
    return ":".join(lower[index : index + 2] for index in range(0, 12, 2))


def validate_mac_address(value: str) -> str:
    return normalize_mac_address(value)


def validate_ipv4_address(value: str) -> str:
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValidationError("Enter a valid IPv4 address.") from exc

    if not isinstance(parsed, ipaddress.IPv4Address):
        raise ValidationError("Enter a valid IPv4 address.")

    return str(parsed)


def validate_ipv4_cidr(value: str) -> str:
    try:
        parsed = ipaddress.ip_network(value, strict=True)
    except ValueError as exc:
        raise ValidationError("Enter a valid IPv4 CIDR block.") from exc

    if not isinstance(parsed, ipaddress.IPv4Network):
        raise ValidationError("Enter a valid IPv4 CIDR block.")

    return parsed.with_prefixlen


def ipv4_address_in_cidr(address: str, cidr: str) -> bool:
    try:
        parsed_address = ipaddress.ip_address(validate_ipv4_address(address))
        parsed_network = ipaddress.ip_network(validate_ipv4_cidr(cidr), strict=True)
    except ValidationError:
        return False

    return parsed_address in parsed_network


def validate_hostname(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("Hostname must be a string.")

    hostname = value.strip()
    if not hostname:
        raise ValidationError("Hostname is required.")

    if len(hostname) > 253:
        raise ValidationError("Hostname must be 253 characters or fewer.")

    labels = hostname.split(".")
    if any(label == "" for label in labels):
        raise ValidationError("Hostname labels must not be empty.")

    for label in labels:
        if len(label) > 63:
            raise ValidationError("Hostname labels must be 63 characters or fewer.")
        if not _HOST_LABEL_RE.fullmatch(label):
            raise ValidationError("Hostname labels may contain only letters, digits, and hyphens, and must not start or end with a hyphen.")

    return hostname
