from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from managed_dhcp_server.ipam.models import Organization, Site

from .selectors import organizations_visible_to_user, sites_visible_to_user
from .serializers import OrganizationSerializer, SiteSerializer, UserSummarySerializer


class HealthView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class CurrentUserView(APIView):
    def get(self, request: Request) -> Response:
        serializer = UserSummarySerializer(request.user)
        return Response(serializer.data)


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrganizationSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return organizations_visible_to_user(self.request.user)


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SiteSerializer
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return sites_visible_to_user(self.request.user)
