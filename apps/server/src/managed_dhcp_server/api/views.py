from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from managed_dhcp_server.access.models import OrganizationMembership, SiteMembership
from managed_dhcp_server.ipam.models import Organization, Site

from .permissions import (
    can_list_organization_memberships,
    can_list_site_memberships,
    can_mutate_organization_memberships,
    can_mutate_site_memberships,
)
from .selectors import organizations_visible_to_user, sites_visible_to_user
from .serializers import (
    OrganizationMembershipSerializer,
    OrganizationMembershipWriteSerializer,
    OrganizationSerializer,
    SiteMembershipSerializer,
    SiteMembershipWriteSerializer,
    SiteSerializer,
    UserSummarySerializer,
)
from .services import (
    create_organization_membership,
    create_site_membership,
    delete_organization_membership,
    delete_site_membership,
    update_organization_membership,
    update_site_membership,
)


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


class OrganizationMembershipListCreateView(APIView):
    def get(self, request: Request, organization_id: str) -> Response:
        organization = _visible_organization_or_404(request.user, organization_id)
        if not can_list_organization_memberships(request.user, organization):
            raise PermissionDenied("You cannot list memberships for this organization.")

        memberships = organization.memberships.select_related("user").all()
        return Response(OrganizationMembershipSerializer(memberships, many=True).data)

    def post(self, request: Request, organization_id: str) -> Response:
        organization = _visible_organization_or_404(request.user, organization_id)
        if not can_mutate_organization_memberships(request.user, organization):
            raise PermissionDenied("You cannot create memberships for this organization.")

        serializer = OrganizationMembershipWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = create_organization_membership(
            actor=request.user,
            organization=organization,
            user=serializer.validated_data["user"],
            role=serializer.validated_data["role"],
        )
        return Response(OrganizationMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class OrganizationMembershipDetailView(APIView):
    def patch(self, request: Request, organization_id: str, membership_id: str) -> Response:
        organization = _visible_organization_or_404(request.user, organization_id)
        membership = _organization_membership_or_404(organization, membership_id)
        if not can_mutate_organization_memberships(request.user, organization):
            raise PermissionDenied("You cannot update memberships for this organization.")

        serializer = OrganizationMembershipWriteSerializer(data=request.data, context={"patch": True})
        serializer.is_valid(raise_exception=True)
        membership = update_organization_membership(
            actor=request.user,
            membership=membership,
            role=serializer.validated_data["role"],
        )
        return Response(OrganizationMembershipSerializer(membership).data)

    def delete(self, request: Request, organization_id: str, membership_id: str) -> Response:
        organization = _visible_organization_or_404(request.user, organization_id)
        membership = _organization_membership_or_404(organization, membership_id)
        if not can_mutate_organization_memberships(request.user, organization):
            raise PermissionDenied("You cannot delete memberships for this organization.")

        delete_organization_membership(actor=request.user, membership=membership)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SiteMembershipListCreateView(APIView):
    def get(self, request: Request, site_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        if not can_list_site_memberships(request.user, site):
            raise PermissionDenied("You cannot list memberships for this site.")

        memberships = site.memberships.select_related("user").all()
        return Response(SiteMembershipSerializer(memberships, many=True).data)

    def post(self, request: Request, site_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        if not can_mutate_site_memberships(request.user, site):
            raise PermissionDenied("You cannot create memberships for this site.")

        serializer = SiteMembershipWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = create_site_membership(
            actor=request.user,
            site=site,
            user=serializer.validated_data["user"],
            role=serializer.validated_data["role"],
        )
        return Response(SiteMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class SiteMembershipDetailView(APIView):
    def patch(self, request: Request, site_id: str, membership_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        membership = _site_membership_or_404(site, membership_id)
        if not can_mutate_site_memberships(request.user, site):
            raise PermissionDenied("You cannot update memberships for this site.")

        serializer = SiteMembershipWriteSerializer(data=request.data, context={"patch": True})
        serializer.is_valid(raise_exception=True)
        membership = update_site_membership(
            actor=request.user,
            membership=membership,
            role=serializer.validated_data["role"],
        )
        return Response(SiteMembershipSerializer(membership).data)

    def delete(self, request: Request, site_id: str, membership_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        membership = _site_membership_or_404(site, membership_id)
        if not can_mutate_site_memberships(request.user, site):
            raise PermissionDenied("You cannot delete memberships for this site.")

        delete_site_membership(actor=request.user, membership=membership)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _visible_organization_or_404(user: object, organization_id: str) -> Organization:
    organization = organizations_visible_to_user(user).filter(pk=organization_id).first()
    if organization is None:
        raise NotFound("Organization not found.")
    return organization


def _visible_site_or_404(user: object, site_id: str) -> Site:
    site = sites_visible_to_user(user).filter(pk=site_id).first()
    if site is None:
        raise NotFound("Site not found.")
    return site


def _organization_membership_or_404(organization: Organization, membership_id: str) -> OrganizationMembership:
    return get_object_or_404(
        OrganizationMembership.objects.select_related("user", "organization"),
        pk=membership_id,
        organization=organization,
    )


def _site_membership_or_404(site: Site, membership_id: str) -> SiteMembership:
    return get_object_or_404(
        SiteMembership.objects.select_related("user", "site", "site__organization"),
        pk=membership_id,
        site=site,
    )
