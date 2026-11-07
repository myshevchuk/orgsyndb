"""The application's URLs, all under /lab/."""

from django.contrib import admin
from django.urls import include, path

from overview import views as overview

urlpatterns = [
    path("lab/", overview.overview, name="overview"),
    path("lab/summary/", overview.summary, name="summary"),
    path("lab/inventory/", include("inventory.urls")),
    path("lab/planning/", include("planning.urls")),
    path("lab/tasks/", include("tasks.urls")),
    path("lab/accounts/", include("accounts.urls")),
    path("lab/admin/", admin.site.urls),
]
