"""Sign-in, sign-out, the change of one's own password and one's own
access tokens."""

from django.contrib.auth import views as auth
from django.urls import path

from accounts import views

urlpatterns = [
    path("login/", auth.LoginView.as_view(
        template_name="accounts/login.html"), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("password/", views.PasswordChangeView.as_view(),
         name="password_change"),
    path("tokens/", views.tokens, name="access_tokens"),
    path("tokens/<int:pk>/revoke/", views.revoke,
         name="access_token_revoke"),
]
