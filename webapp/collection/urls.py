"""The collection's URLs, below /lab/collection/."""

from django.urls import path

from collection import views

urlpatterns = [
    path("", views.imports, name="imports"),
    path("manifest/", views.manifest, name="manifest"),
]
