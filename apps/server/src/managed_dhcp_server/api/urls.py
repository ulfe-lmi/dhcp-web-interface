from __future__ import annotations

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CurrentUserView, HealthView, OrganizationViewSet, SiteViewSet

router = SimpleRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("sites", SiteViewSet, basename="site")

urlpatterns = [
    path("health/", HealthView.as_view(), name="api-health"),
    path("me/", CurrentUserView.as_view(), name="api-me"),
    *router.urls,
]
