from __future__ import annotations

from django.apps import AppConfig


class ConfigsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "managed_dhcp_server.configs"
