"""The OpenID Connect provider for Forgejo: its claims, its discovery
document, its authorization page and its URLs under /lab/o/."""

import functools
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import path, reverse
from oauth2_provider import views as toolkit
from oauth2_provider.oauth2_validators import OAuth2Validator

# The scopes the provider offers, and the claims it gives under them.
SCOPES = ["openid", "profile", "email"]
CLAIMS = ["sub", "nickname", "preferred_username", "name", "email"]


def active(user: Any) -> bool:
    """Tell whether USER is an account that is active now."""
    return user is not None and getattr(user, "is_active", False)


class ClaimsValidator(OAuth2Validator):
    """The toolkit's validator, which refuses a code, a refresh token or
    an access token of an account deactivated since it was issued, and
    whose ID tokens and user info carry,
    besides ``sub``, the account's primary key as text, ``nickname``
    and ``preferred_username``, both the user name, and ``name``, the
    display name, under the scope ``profile``, and ``email``, the
    account's email address, under the scope ``email``."""

    def validate_code(self, client_id: str, code: str, client: Any,
                      request: Any, *args: Any, **kwargs: Any) -> bool:
        """Accept the authorization CODE as the toolkit does, and only
        while the account it was issued to is active."""
        return (super().validate_code(client_id, code, client, request,
                                      *args, **kwargs)
                and active(request.user))

    def validate_refresh_token(self, refresh_token: str, client: Any,
                               request: Any, *args: Any,
                               **kwargs: Any) -> bool:
        """Accept REFRESH_TOKEN as the toolkit does, and only while the
        account it was issued to is active."""
        return (super().validate_refresh_token(refresh_token, client,
                                               request, *args, **kwargs)
                and active(request.user))

    def validate_bearer_token(self, token: str, scopes: Any,
                              request: Any) -> bool:
        """Accept the access TOKEN as the toolkit does, and only while
        the account it was issued to is active."""
        return (super().validate_bearer_token(token, scopes, request)
                and active(request.user))

    def get_additional_claims(self, request: Any) -> dict[str, str]:
        """Return the claims of the account REQUEST is made for."""
        user = request.user
        return {"nickname": user.get_username(),
                "preferred_username": user.get_username(),
                "name": user.display_name, "email": user.email}


def provider_on() -> bool:
    """Tell whether the provider is on: whether the settings hold an
    OpenID key."""
    return bool(settings.OAUTH2_PROVIDER.get("OIDC_RSA_PRIVATE_KEY"))


View = Callable[..., HttpResponse]


def when_on(view: View) -> View:
    """Return VIEW, answering 404 instead, before anything else, while
    the provider is off."""
    @functools.wraps(view)
    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any
                ) -> HttpResponse:
        if not provider_on():
            raise Http404("The OpenID provider is off.")
        return view(request, *args, **kwargs)
    return wrapped


def discovery(request: HttpRequest) -> JsonResponse:
    """Answer the provider's discovery document.

    The issuer is ``OIDC_ISS_ENDPOINT``; the authorization endpoint,
    which the person's browser reaches, is under ``ORGSYNDB_URL``; the
    token, user-info and keys endpoints, which only Forgejo's server
    calls, are under ``ORGSYNDB_APP_INTERNAL_URL``. The document is the
    same whichever host it is requested through.
    """
    public = settings.ORGSYNDB_URL
    internal = settings.ORGSYNDB_APP_INTERNAL_URL
    response = JsonResponse({
        "issuer": settings.OAUTH2_PROVIDER["OIDC_ISS_ENDPOINT"],
        "authorization_endpoint":
            public + reverse("oauth2_provider:authorize"),
        "token_endpoint": internal + reverse("oauth2_provider:token"),
        "userinfo_endpoint":
            internal + reverse("oauth2_provider:user-info"),
        "jwks_uri": internal + reverse("oauth2_provider:jwks-info"),
        "scopes_supported": SCOPES,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post", "client_secret_basic"],
        "claims_supported": CLAIMS,
    })
    response["Access-Control-Allow-Origin"] = "*"
    return response


class AuthorizationView(toolkit.AuthorizationView):
    """The toolkit's authorization endpoint, which first needs a
    signed-in account, as the toolkit's does, and then answers an
    account without an email address with the page ``No access to
    Forgejo`` (status 403), issuing no code and redirecting nowhere."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any
                 ) -> HttpResponse:
        user = request.user
        if user.is_authenticated and not user.email:
            return render(request, "accounts/no_forge_access.html",
                          status=403)
        return super().dispatch(request, *args, **kwargs)


app_name = "oauth2_provider"
urlpatterns = [
    path("authorize/", when_on(AuthorizationView.as_view()),
         name="authorize"),
    path("token/", when_on(toolkit.TokenView.as_view()), name="token"),
    path("userinfo/", when_on(toolkit.UserInfoView.as_view()),
         name="user-info"),
    path(".well-known/openid-configuration", when_on(discovery),
         name="oidc-connect-discovery-info"),
    path(".well-known/jwks.json", when_on(toolkit.JwksInfoView.as_view()),
         name="jwks-info"),
]
