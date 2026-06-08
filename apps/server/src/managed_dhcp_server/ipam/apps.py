from __future__ import annotations

from django.apps import AppConfig


class IpamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "managed_dhcp_server.ipam"
    label = "ipam"
