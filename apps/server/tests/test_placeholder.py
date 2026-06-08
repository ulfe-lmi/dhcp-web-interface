from managed_dhcp_server import placeholder_message


def test_placeholder_message() -> None:
    assert placeholder_message() == "managed-dhcp-server scaffold only"
