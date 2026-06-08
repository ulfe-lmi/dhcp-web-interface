from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("managed_dhcp_server.api.urls")),
]
