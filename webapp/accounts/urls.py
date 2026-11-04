"""Sign-in, sign-out and the change of one's own password."""

from django.contrib.auth import views as auth
from django.urls import path

from accounts.views import PasswordChangeView

urlpatterns = [
    path("login/", auth.LoginView.as_view(
        template_name="accounts/login.html"), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("password/", PasswordChangeView.as_view(),
         name="password_change"),
]
