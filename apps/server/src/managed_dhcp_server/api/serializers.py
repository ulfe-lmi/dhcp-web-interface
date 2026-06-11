from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from managed_dhcp_server.access.models import OrganizationMembership, OrganizationRole, SiteMembership, SiteRole
from managed_dhcp_server.ipam.models import DHCPPool, DHCPReservation, IPv4Subnet, Organization, Site


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


class _StrictFieldsMixin:
    required_create_fields: set[str] = set()
    writable_fields: set[str] = set()

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        self._validate_allowed_fields()
        if self.context.get("patch") and not attrs:
            raise serializers.ValidationError({"non_field_errors": ["At least one writable field is required."]})
        if not self.context.get("patch"):
            missing_fields = self.required_create_fields - set(self.initial_data)
            if missing_fields:
                raise serializers.ValidationError({field: ["This field is required."] for field in sorted(missing_fields)})
        return attrs

    def _validate_allowed_fields(self) -> None:
        extra_fields = set(self.initial_data) - self.writable_fields
        if extra_fields:
            raise serializers.ValidationError({field: ["This field is not writable here."] for field in sorted(extra_fields)})


class IPv4SubnetSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = IPv4Subnet
        fields = [
            "id",
            "site",
            "site_name",
            "name",
            "cidr",
            "gateway",
            "dns_servers",
            "default_lease_time_seconds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class IPv4SubnetWriteSerializer(_StrictFieldsMixin, serializers.Serializer):
    required_create_fields = {"name", "cidr"}
    writable_fields = {"name", "cidr", "gateway", "dns_servers", "default_lease_time_seconds"}

    name = serializers.CharField(max_length=255, required=False)
    cidr = serializers.CharField(max_length=43, required=False)
    gateway = serializers.IPAddressField(protocol="IPv4", required=False, allow_null=True)
    dns_servers = serializers.ListField(child=serializers.IPAddressField(protocol="IPv4"), required=False)
    default_lease_time_seconds = serializers.IntegerField(min_value=1, required=False)


class DHCPPoolSerializer(serializers.ModelSerializer):
    subnet_cidr = serializers.CharField(source="subnet.cidr", read_only=True)

    class Meta:
        model = DHCPPool
        fields = [
            "id",
            "subnet",
            "subnet_cidr",
            "name",
            "start_ip",
            "end_ip",
            "lease_time_seconds",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DHCPPoolWriteSerializer(_StrictFieldsMixin, serializers.Serializer):
    required_create_fields = {"name", "start_ip", "end_ip"}
    writable_fields = {"name", "start_ip", "end_ip", "lease_time_seconds", "enabled"}

    name = serializers.CharField(max_length=255, required=False)
    start_ip = serializers.IPAddressField(protocol="IPv4", required=False)
    end_ip = serializers.IPAddressField(protocol="IPv4", required=False)
    lease_time_seconds = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    enabled = serializers.BooleanField(required=False)


class DHCPReservationSerializer(serializers.ModelSerializer):
    subnet_cidr = serializers.CharField(source="subnet.cidr", read_only=True)

    class Meta:
        model = DHCPReservation
        fields = [
            "id",
            "subnet",
            "subnet_cidr",
            "hostname",
            "mac_address",
            "ip_address",
            "description",
            "enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DHCPReservationWriteSerializer(_StrictFieldsMixin, serializers.Serializer):
    required_create_fields = {"hostname", "mac_address", "ip_address"}
    writable_fields = {"hostname", "mac_address", "ip_address", "description", "enabled"}

    hostname = serializers.CharField(max_length=253, required=False)
    mac_address = serializers.CharField(max_length=32, required=False)
    ip_address = serializers.IPAddressField(protocol="IPv4", required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    enabled = serializers.BooleanField(required=False)
