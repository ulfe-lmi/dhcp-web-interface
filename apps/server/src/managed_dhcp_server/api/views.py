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
from managed_dhcp_server.access.permissions import can_edit_site_dhcp
from managed_dhcp_server.ipam.models import DHCPPool, DHCPReservation, IPv4Subnet, Organization, Site

from .permissions import (
    can_list_organization_memberships,
    can_list_site_memberships,
    can_mutate_organization_memberships,
    can_mutate_site_memberships,
)
from .selectors import organizations_visible_to_user, sites_visible_to_user
from .serializers import (
    DHCPPoolSerializer,
    DHCPPoolWriteSerializer,
    DHCPReservationSerializer,
    DHCPReservationWriteSerializer,
    IPv4SubnetSerializer,
    IPv4SubnetWriteSerializer,
    OrganizationMembershipSerializer,
    OrganizationMembershipWriteSerializer,
    OrganizationSerializer,
    SiteMembershipSerializer,
    SiteMembershipWriteSerializer,
    SiteSerializer,
    UserSummarySerializer,
)
from .services import (
    create_dhcp_pool,
    create_dhcp_reservation,
    create_ipv4_subnet,
    create_organization_membership,
    create_site_membership,
    delete_ipv4_subnet,
    disable_dhcp_pool,
    disable_dhcp_reservation,
    delete_organization_membership,
    delete_site_membership,
    update_dhcp_pool,
    update_dhcp_reservation,
    update_ipv4_subnet,
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


class IPv4SubnetListCreateView(APIView):
    def get(self, request: Request, site_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        subnets = site.ipv4_subnets.all()
        return Response(IPv4SubnetSerializer(subnets, many=True).data)

    def post(self, request: Request, site_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        _check_dhcp_edit_permission(request.user, site)

        serializer = IPv4SubnetWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subnet = create_ipv4_subnet(actor=request.user, site=site, data=serializer.validated_data)
        return Response(IPv4SubnetSerializer(subnet).data, status=status.HTTP_201_CREATED)


class IPv4SubnetDetailView(APIView):
    def get(self, request: Request, site_id: str, subnet_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        subnet = _site_subnet_or_404(site, subnet_id)
        return Response(IPv4SubnetSerializer(subnet).data)

    def patch(self, request: Request, site_id: str, subnet_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        subnet = _site_subnet_or_404(site, subnet_id)
        _check_dhcp_edit_permission(request.user, site)

        serializer = IPv4SubnetWriteSerializer(data=request.data, context={"patch": True}, partial=True)
        serializer.is_valid(raise_exception=True)
        subnet = update_ipv4_subnet(actor=request.user, subnet=subnet, data=serializer.validated_data)
        return Response(IPv4SubnetSerializer(subnet).data)

    def delete(self, request: Request, site_id: str, subnet_id: str) -> Response:
        site = _visible_site_or_404(request.user, site_id)
        subnet = _site_subnet_or_404(site, subnet_id)
        _check_dhcp_edit_permission(request.user, site)

        delete_ipv4_subnet(actor=request.user, subnet=subnet)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DHCPPoolListCreateView(APIView):
    def get(self, request: Request, subnet_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        pools = subnet.dhcp_pools.all()
        return Response(DHCPPoolSerializer(pools, many=True).data)

    def post(self, request: Request, subnet_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        _check_dhcp_edit_permission(request.user, subnet.site)

        serializer = DHCPPoolWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pool = create_dhcp_pool(actor=request.user, subnet=subnet, data=serializer.validated_data)
        return Response(DHCPPoolSerializer(pool).data, status=status.HTTP_201_CREATED)


class DHCPPoolDetailView(APIView):
    def get(self, request: Request, subnet_id: str, pool_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        pool = _subnet_pool_or_404(subnet, pool_id)
        return Response(DHCPPoolSerializer(pool).data)

    def patch(self, request: Request, subnet_id: str, pool_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        pool = _subnet_pool_or_404(subnet, pool_id)
        _check_dhcp_edit_permission(request.user, subnet.site)

        serializer = DHCPPoolWriteSerializer(data=request.data, context={"patch": True}, partial=True)
        serializer.is_valid(raise_exception=True)
        pool = update_dhcp_pool(actor=request.user, pool=pool, data=serializer.validated_data)
        return Response(DHCPPoolSerializer(pool).data)

    def delete(self, request: Request, subnet_id: str, pool_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        pool = _subnet_pool_or_404(subnet, pool_id)
        _check_dhcp_edit_permission(request.user, subnet.site)

        disable_dhcp_pool(actor=request.user, pool=pool)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DHCPReservationListCreateView(APIView):
    def get(self, request: Request, subnet_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        reservations = subnet.dhcp_reservations.all()
        return Response(DHCPReservationSerializer(reservations, many=True).data)

    def post(self, request: Request, subnet_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        _check_dhcp_edit_permission(request.user, subnet.site)

        serializer = DHCPReservationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = create_dhcp_reservation(actor=request.user, subnet=subnet, data=serializer.validated_data)
        return Response(DHCPReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


class DHCPReservationDetailView(APIView):
    def get(self, request: Request, subnet_id: str, reservation_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        reservation = _subnet_reservation_or_404(subnet, reservation_id)
        return Response(DHCPReservationSerializer(reservation).data)

    def patch(self, request: Request, subnet_id: str, reservation_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        reservation = _subnet_reservation_or_404(subnet, reservation_id)
        _check_dhcp_edit_permission(request.user, subnet.site)

        serializer = DHCPReservationWriteSerializer(data=request.data, context={"patch": True}, partial=True)
        serializer.is_valid(raise_exception=True)
        reservation = update_dhcp_reservation(actor=request.user, reservation=reservation, data=serializer.validated_data)
        return Response(DHCPReservationSerializer(reservation).data)

    def delete(self, request: Request, subnet_id: str, reservation_id: str) -> Response:
        subnet = _visible_subnet_or_404(request.user, subnet_id)
        reservation = _subnet_reservation_or_404(subnet, reservation_id)
        _check_dhcp_edit_permission(request.user, subnet.site)

        disable_dhcp_reservation(actor=request.user, reservation=reservation)
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


def _visible_subnet_or_404(user: object, subnet_id: str) -> IPv4Subnet:
    subnet = (
        IPv4Subnet.objects.select_related("site", "site__organization")
        .filter(pk=subnet_id, site__in=sites_visible_to_user(user))
        .first()
    )
    if subnet is None:
        raise NotFound("IPv4 subnet not found.")
    return subnet


def _site_subnet_or_404(site: Site, subnet_id: str) -> IPv4Subnet:
    return get_object_or_404(
        IPv4Subnet.objects.select_related("site", "site__organization"),
        pk=subnet_id,
        site=site,
    )


def _subnet_pool_or_404(subnet: IPv4Subnet, pool_id: str) -> DHCPPool:
    return get_object_or_404(
        DHCPPool.objects.select_related("subnet", "subnet__site", "subnet__site__organization"),
        pk=pool_id,
        subnet=subnet,
    )


def _subnet_reservation_or_404(subnet: IPv4Subnet, reservation_id: str) -> DHCPReservation:
    return get_object_or_404(
        DHCPReservation.objects.select_related("subnet", "subnet__site", "subnet__site__organization"),
        pk=reservation_id,
        subnet=subnet,
    )


def _check_dhcp_edit_permission(user: object, site: Site) -> None:
    if not can_edit_site_dhcp(user, site):
        raise PermissionDenied("You cannot mutate DHCP/IPAM data for this site.")
