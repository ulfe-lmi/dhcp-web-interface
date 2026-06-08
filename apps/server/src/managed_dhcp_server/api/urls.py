from __future__ import annotations

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    CurrentUserView,
    HealthView,
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
    *router.urls,
]
