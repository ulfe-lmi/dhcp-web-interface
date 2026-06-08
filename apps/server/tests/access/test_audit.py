import pytest
from django.core.exceptions import ValidationError

from managed_dhcp_server.access.models import AuditEvent

from .factories import create_organization, create_site, create_user


pytestmark = pytest.mark.django_db


def test_audit_event_record_creates_event() -> None:
    organization = create_organization()
    site = create_site(organization=organization)
    user = create_user("auditor-actor")

    event = AuditEvent.record(
        actor=user,
        organization=organization,
        site=site,
        event_type="membership.created",
        object_type="OrganizationMembership",
        object_id="member-1",
        summary="Added organization membership.",
        metadata={"role": "viewer"},
    )

    assert event.pk is not None
    assert event.actor == user
    assert event.organization == organization
    assert event.site == site
    assert event.metadata == {"role": "viewer"}


def test_audit_event_metadata_defaults_to_empty_dict() -> None:
    event = AuditEvent.record(event_type="system.started", summary="System event.")

    assert event.metadata == {}


def test_audit_event_metadata_must_be_dict() -> None:
    event = AuditEvent(event_type="bad.metadata", summary="Bad metadata.", metadata=["not", "a", "dict"])

    with pytest.raises(ValidationError, match="metadata"):
        event.full_clean()

    with pytest.raises(ValidationError, match="metadata"):
        event.save()


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("event_type", {"event_type": "", "summary": "Missing event type."}),
        ("summary", {"event_type": "missing.summary", "summary": ""}),
    ],
)
def test_audit_event_required_fields(field: str, kwargs: dict[str, str]) -> None:
    event = AuditEvent(**kwargs)

    with pytest.raises(ValidationError, match=field):
        event.full_clean()


def test_existing_audit_event_cannot_be_changed_via_save() -> None:
    event = AuditEvent.record(event_type="membership.created", summary="Created membership.")
    event.summary = "Changed summary."

    with pytest.raises(ValidationError, match="append-only"):
        event.save()


def test_existing_audit_event_cannot_be_deleted_via_instance_delete() -> None:
    event = AuditEvent.record(event_type="membership.created", summary="Created membership.")

    with pytest.raises(ValidationError, match="append-only"):
        event.delete()


def test_actor_can_be_null_for_system_events() -> None:
    event = AuditEvent.record(event_type="system.maintenance", summary="System maintenance started.")

    assert event.actor is None


def test_organization_and_site_can_be_null_for_global_system_events() -> None:
    event = AuditEvent.record(event_type="system.started", summary="System started.")

    assert event.organization is None
    assert event.site is None
