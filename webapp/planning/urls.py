"""The planning's URLs, below /lab/planning/."""

from django.urls import path

from planning import views

urlpatterns = [
    path("", views.planning_list, name="planning_list"),
]
