"""Views of the accounts that Django's own do not cover."""

from django.contrib.auth import views as auth
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _


class PasswordChangeView(SuccessMessageMixin, auth.PasswordChangeView):
    """Change the signed-in user's password, then return to the task
    list with a message."""

    template_name = "accounts/password_change.html"
    success_url = "/lab/tasks/"
    success_message = _("Your password has been changed.")
