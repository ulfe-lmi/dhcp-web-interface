from __future__ import annotations

from django.contrib.auth import get_user_model

from managed_dhcp_server.ipam.models import Organization, Site


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
