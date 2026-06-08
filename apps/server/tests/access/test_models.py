import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole

from .factories import create_organization, create_site, create_user


pytestmark = pytest.mark.django_db


def test_can_create_organization_membership() -> None:
    organization = create_organization()
    user = create_user("org-member")

    membership = OrganizationMembership(organization=organization, user=user, role=OrganizationRole.OWNER)
    membership.full_clean()
    membership.save()

    assert membership.organization == organization
    assert membership.user == user
    assert membership.role == OrganizationRole.OWNER


def test_can_create_site_membership() -> None:
    site = create_site()
    user = create_user("site-member")

    membership = SiteMembership(site=site, user=user, role=SiteRole.DHCP_EDITOR)
    membership.full_clean()
    membership.save()

    assert membership.site == site
    assert membership.user == user
    assert membership.role == SiteRole.DHCP_EDITOR


def test_cannot_create_duplicate_organization_membership_for_same_user_and_org() -> None:
    organization = create_organization()
    user = create_user("duplicate-org-member")
    OrganizationMembership.objects.create(organization=organization, user=user, role=OrganizationRole.VIEWER)

    duplicate = OrganizationMembership(organization=organization, user=user, role=OrganizationRole.ADMIN)

    with pytest.raises(ValidationError, match="already exists"):
        duplicate.full_clean()

    with pytest.raises(IntegrityError):
        duplicate.save()


def test_cannot_create_duplicate_site_membership_for_same_user_and_site() -> None:
    site = create_site()
    user = create_user("duplicate-site-member")
    SiteMembership.objects.create(site=site, user=user, role=SiteRole.VIEWER)

    duplicate = SiteMembership(site=site, user=user, role=SiteRole.SITE_ADMIN)

    with pytest.raises(ValidationError, match="already exists"):
        duplicate.full_clean()

    with pytest.raises(IntegrityError):
        duplicate.save()


@pytest.mark.parametrize(
    ("model_factory", "role_field"),
    [
        (lambda user: OrganizationMembership(organization=create_organization("invalid-role-org"), user=user, role="bad_role"), "role"),
        (lambda user: SiteMembership(site=create_site("invalid-role-site"), user=user, role="bad_role"), "role"),
    ],
)
def test_invalid_membership_role_rejected_by_full_clean(model_factory, role_field: str) -> None:
    user = create_user(f"invalid-role-{role_field}")
    membership = model_factory(user)

    with pytest.raises(ValidationError, match="Value 'bad_role' is not a valid choice"):
        membership.full_clean()
