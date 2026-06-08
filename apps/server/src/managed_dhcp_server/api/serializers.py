from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.ipam.models import Organization, Site


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "email", "is_staff", "is_superuser"]
        read_only_fields = fields


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "created_at", "updated_at"]
        read_only_fields = fields


class SiteSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Site
        fields = ["id", "organization", "organization_name", "name", "slug", "description", "created_at", "updated_at"]
        read_only_fields = fields


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    user_summary = UserSummarySerializer(source="user", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user", "user_summary", "role", "created_at", "updated_at"]
        read_only_fields = fields


class SiteMembershipSerializer(serializers.ModelSerializer):
    user_summary = UserSummarySerializer(source="user", read_only=True)

    class Meta:
        model = SiteMembership
        fields = ["id", "user", "user_summary", "role", "created_at", "updated_at"]
        read_only_fields = fields


class OrganizationMembershipWriteSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    role = serializers.ChoiceField(choices=OrganizationRole.choices)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        if self.context.get("patch"):
            self.fields["user"].required = False

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        self._validate_allowed_fields()
        if self.context.get("patch") and "role" not in self.initial_data:
            raise serializers.ValidationError({"role": ["This field is required."]})
        return attrs

    def _validate_allowed_fields(self) -> None:
        allowed_fields = {"role"} if self.context.get("patch") else {"user", "role"}
        extra_fields = set(self.initial_data) - allowed_fields
        if extra_fields:
            raise serializers.ValidationError({field: ["This field is not writable here."] for field in sorted(extra_fields)})


class SiteMembershipWriteSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    role = serializers.ChoiceField(choices=SiteRole.choices)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        if self.context.get("patch"):
            self.fields["user"].required = False

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        self._validate_allowed_fields()
        if self.context.get("patch") and "role" not in self.initial_data:
            raise serializers.ValidationError({"role": ["This field is required."]})
        return attrs

    def _validate_allowed_fields(self) -> None:
        allowed_fields = {"role"} if self.context.get("patch") else {"user", "role"}
        extra_fields = set(self.initial_data) - allowed_fields
        if extra_fields:
            raise serializers.ValidationError({field: ["This field is not writable here."] for field in sorted(extra_fields)})
