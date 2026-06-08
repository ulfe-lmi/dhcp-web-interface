import pytest
from django.core.exceptions import ValidationError

from managed_dhcp_server.ipam.validators import (
    ipv4_address_in_cidr,
    normalize_mac_address,
    validate_hostname,
    validate_ipv4_cidr,
)


@pytest.mark.parametrize(
    "value",
    [
        "AA:BB:CC:DD:EE:FF",
        "aa-bb-cc-dd-ee-ff",
        "aabb.ccdd.eeff",
        "aabbccddeeff",
    ],
)
def test_mac_formats_normalize_to_colon_lowercase(value: str) -> None:
    assert normalize_mac_address(value) == "aa:bb:cc:dd:ee:ff"


@pytest.mark.parametrize("value", ["", "aa:bb:cc:dd:ee", "aa:bb:cc:dd:ee:gg", "not-a-mac"])
def test_invalid_mac_addresses_fail(value: str) -> None:
    with pytest.raises(ValidationError):
        normalize_mac_address(value)


def test_valid_ipv4_cidr_is_accepted() -> None:
    assert validate_ipv4_cidr("192.168.10.0/24") == "192.168.10.0/24"


@pytest.mark.parametrize("value", ["192.168.10.1/24", "not-a-cidr", "2001:db8::/64"])
def test_invalid_ipv4_cidr_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_ipv4_cidr(value)


def test_ipv4_address_in_cidr_helper() -> None:
    assert ipv4_address_in_cidr("192.168.10.42", "192.168.10.0/24") is True
    assert ipv4_address_in_cidr("192.168.11.42", "192.168.10.0/24") is False


@pytest.mark.parametrize("value", ["printer-1", "lab-pc-01", "host.example.local"])
def test_valid_hostnames(value: str) -> None:
    assert validate_hostname(value) == value


@pytest.mark.parametrize("value", ["bad_name", "-bad", "bad-", "has space"])
def test_invalid_hostnames(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_hostname(value)
