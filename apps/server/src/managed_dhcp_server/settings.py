from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = "dev-only-domain-model-tests"
DEBUG = True
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "managed_dhcp_server.ipam.apps.IpamConfig",
]

MIDDLEWARE: list[str] = []

ROOT_URLCONF = "managed_dhcp_server.urls"

TEMPLATES: list[dict[str, object]] = []

WSGI_APPLICATION = "managed_dhcp_server.wsgi.application"
ASGI_APPLICATION = "managed_dhcp_server.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
