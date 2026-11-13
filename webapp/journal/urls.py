"""The journal's URLs, below /lab/journal/."""

from django.urls import path

from journal import views

urlpatterns = [
    path("", views.notebook_list, name="notebook_list"),
    path("new/", views.notebook_new, name="notebook_new"),
    path("<str:code>/", views.notebook_page, name="notebook"),
    path("<str:code>/edit/", views.notebook_edit, name="notebook_edit"),
]
