"""Views of the accounts that Django's own do not cover: the change of
one's own password and one's own access tokens."""

from django import forms
from django.contrib import messages
from django.contrib.auth import views as auth
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.models import AccessToken

TOKENS = "/lab/accounts/tokens/"


class PasswordChangeView(SuccessMessageMixin, auth.PasswordChangeView):
    """Change the signed-in user's password, then return to the task
    list with a message."""

    template_name = "accounts/password_change.html"
    success_url = "/lab/tasks/"
    success_message = _("Your password has been changed.")


class TokenForm(forms.ModelForm):
    """The name of a new access token, at most 100 characters."""

    class Meta:
        model = AccessToken
        fields = ["name"]


@never_cache
@login_required
def tokens(request: HttpRequest) -> HttpResponse:
    """List the signed-in user's access tokens, and on a valid POST
    create one with the name posted and show it, this once, above the
    list. A name that is refused is shown with its error and creates
    nothing."""
    form = TokenForm(request.POST if request.method == "POST" else None)
    created = None
    if form.is_bound and form.is_valid():
        created = AccessToken.create_for(request.user,
                                         form.cleaned_data["name"])[1]
        form = TokenForm()
    return render(request, "accounts/tokens.html", {
        "form": form, "created": created,
        "tokens": request.user.access_tokens.order_by("created_at", "pk")})


@login_required
@require_POST
def revoke(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete the signed-in user's access token PK and return to the
    token page with a message. Answer 404 when the user has no token
    PK."""
    token = get_object_or_404(AccessToken, pk=pk, user=request.user)
    token.delete()
    messages.success(request, _("Access token “%(name)s” revoked.")
                     % {"name": token.name})
    return redirect(TOKENS)
