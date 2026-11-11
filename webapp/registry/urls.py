"""The registry's URLs, below /lab/registry/."""

from django.urls import path

from registry import views

urlpatterns = [
    path("", views.substance_list, name="substance_list"),
    path("snapshot.json", views.snapshot_json, name="registry_snapshot"),
    path("substances/new/", views.substance_new, name="substance_new"),
    path("substances/<str:key>/", views.substance_page, name="substance"),
    path("substances/<str:key>/edit/", views.substance_edit,
         name="substance_edit"),
    path("<str:vocabulary>/", views.vocabulary_page, name="vocabulary"),
    path("<str:vocabulary>/new/", views.term_new, name="term_new"),
    path("<str:vocabulary>/<str:key>/edit/", views.term_edit,
         name="term_edit"),
]
