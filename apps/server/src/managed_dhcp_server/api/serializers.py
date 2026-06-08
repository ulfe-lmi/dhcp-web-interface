from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

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
