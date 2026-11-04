"""The task tracker's URLs, below /lab/tasks/."""

from django.urls import path

from tasks import views

urlpatterns = [
    path("", views.task_list, name="task_list"),
    path("new/", views.task_new, name="task_new"),
    path("<str:number>/", views.task_page, name="task"),
    path("<str:number>/edit/", views.task_edit, name="task_edit"),
    path("<str:number>/<str:action>/", views.task_action,
         name="task_action"),
]
