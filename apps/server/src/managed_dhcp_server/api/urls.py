from __future__ import annotations

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    CurrentUserView,
    DHCPPoolDetailView,
    DHCPPoolListCreateView,
    DHCPReservationDetailView,
    DHCPReservationListCreateView,
    HealthView,
    IPv4SubnetDetailView,
    IPv4SubnetListCreateView,
    OrganizationMembershipDetailView,
    OrganizationMembershipListCreateView,
    OrganizationViewSet,
    SiteMembershipDetailView,
    SiteMembershipListCreateView,
    SiteViewSet,
)

router = SimpleRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("sites", SiteViewSet, basename="site")

urlpatterns = [
    path("health/", HealthView.as_view(), name="api-health"),
    path("me/", CurrentUserView.as_view(), name="api-me"),
    path(
        "organizations/<uuid:organization_id>/memberships/",
        OrganizationMembershipListCreateView.as_view(),
        name="organization-membership-list",
    ),
    path(
        "organizations/<uuid:organization_id>/memberships/<uuid:membership_id>/",
        OrganizationMembershipDetailView.as_view(),
        name="organization-membership-detail",
    ),
    path(
        "sites/<uuid:site_id>/memberships/",
        SiteMembershipListCreateView.as_view(),
        name="site-membership-list",
    ),
    path(
        "sites/<uuid:site_id>/memberships/<uuid:membership_id>/",
        SiteMembershipDetailView.as_view(),
        name="site-membership-detail",
    ),
    path(
        "sites/<uuid:site_id>/subnets/",
        IPv4SubnetListCreateView.as_view(),
        name="ipv4-subnet-list",
    ),
    path(
        "sites/<uuid:site_id>/subnets/<uuid:subnet_id>/",
        IPv4SubnetDetailView.as_view(),
        name="ipv4-subnet-detail",
    ),
    path(
        "subnets/<uuid:subnet_id>/pools/",
        DHCPPoolListCreateView.as_view(),
        name="dhcp-pool-list",
    ),
    path(
        "subnets/<uuid:subnet_id>/pools/<uuid:pool_id>/",
        DHCPPoolDetailView.as_view(),
        name="dhcp-pool-detail",
    ),
    path(
        "subnets/<uuid:subnet_id>/reservations/",
        DHCPReservationListCreateView.as_view(),
        name="dhcp-reservation-list",
    ),
    path(
        "subnets/<uuid:subnet_id>/reservations/<uuid:reservation_id>/",
        DHCPReservationDetailView.as_view(),
        name="dhcp-reservation-detail",
    ),
    *router.urls,
]
