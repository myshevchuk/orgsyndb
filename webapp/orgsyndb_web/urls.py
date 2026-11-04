"""The application's URLs, all under /lab/."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("lab/", RedirectView.as_view(url="/lab/tasks/")),
    path("lab/tasks/", include("tasks.urls")),
    path("lab/accounts/", include("accounts.urls")),
    path("lab/admin/", admin.site.urls),
]
