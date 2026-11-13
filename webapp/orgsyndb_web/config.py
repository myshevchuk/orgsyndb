"""The settings the environment decides, read without touching Django's
settings machinery."""

import base64
import binascii
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

WEBAPP = Path(__file__).resolve().parent.parent
DEBUG_SECRET_KEY = "django-insecure-orgsyndb-debug-only"
DEBUG_HOSTS = ["localhost", "127.0.0.1"]
TRUE = ("1", "true", "yes", "on")
FALSE = ("0", "false", "no", "off")
DEFAULT_URL = "http://localhost:8000"
DEFAULT_APP_INTERNAL_URL = "http://app:8000"
# The client id of Forgejo, the provider's one client.
FORGE_CLIENT_ID = "forgejo"


def flag(environ: Mapping[str, str], name: str, default: bool) -> bool:
    """Return the flag NAME of ENVIRON, or DEFAULT when it is unset or
    empty.

    The words are those ``orgsyndb-deploy`` accepts, in any case: ``1``,
    ``true``, ``yes`` and ``on`` for true, ``0``, ``false``, ``no`` and
    ``off`` for false. Raise ImproperlyConfigured naming NAME for any
    other word.
    """
    value = environ.get(name, "").strip().lower()
    if not value:
        return default
    if value in TRUE:
        return True
    if value in FALSE:
        return False
    raise ImproperlyConfigured(f"{name} must be true or false: {value}")


def database(url: str) -> dict[str, Any]:
    """Return Django's settings of the database named by URL.

    URL is ``postgres://<user>:<password>@<host>[:<port>]/<name>``, also
    with the scheme ``postgresql``, or ``sqlite:///<path>``. User name
    and password may be percent-encoded. Raise ImproperlyConfigured
    naming ``ORGSYNDB_DATABASE_URL`` for another scheme, or when the URL
    names no database.
    """
    name = "ORGSYNDB_DATABASE_URL"
    if url.startswith("sqlite:///"):
        path = url.removeprefix("sqlite:///")
        if not path:
            raise ImproperlyConfigured(f"{name} names no SQLite file: {url}")
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": path}
    parts = urlsplit(url)
    if parts.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured(
            f"{name} must start with postgres:// or sqlite:///: {url}")
    database_name = unquote(parts.path.lstrip("/"))
    if not database_name:
        raise ImproperlyConfigured(f"{name} names no database: {url}")
    try:
        port = parts.port
    except ValueError:
        raise ImproperlyConfigured(f"{name} has a malformed port: {url}"
                                   ) from None
    return {"ENGINE": "django.db.backends.postgresql",
            "NAME": database_name,
            "USER": unquote(parts.username or ""),
            "PASSWORD": unquote(parts.password or ""),
            "HOST": parts.hostname or "",
            "PORT": "" if port is None else str(port)}


def oidc_key(value: str) -> str:
    """Return the PEM text of the RSA private key that VALUE, the value of
    ``ORGSYNDB_OIDC_KEY``, holds in base64; return an empty text for an
    empty VALUE.

    Raise ImproperlyConfigured naming ``ORGSYNDB_OIDC_KEY`` when VALUE is
    not base64, or decodes to anything but a PEM-encoded RSA private key.
    """
    name = "ORGSYNDB_OIDC_KEY"
    if not value:
        return ""
    try:
        pem = base64.b64decode(value, validate=True).decode("ascii")
    except (binascii.Error, UnicodeDecodeError):
        raise ImproperlyConfigured(
            f"{name} is not base64; set it to the output of "
            "'openssl genpkey -algorithm RSA | base64 -w0'") from None
    from jwcrypto import jwk
    try:
        key = jwk.JWK.from_pem(pem.encode("ascii"))
    except (ValueError, TypeError):
        key = None
    if key is None or key.get("kty") != "RSA" or not key.has_private:
        raise ImproperlyConfigured(
            f"{name} holds no PEM-encoded RSA private key")
    return pem


def pkce_required(client_id: str) -> bool:
    """Tell whether the client CLIENT_ID must send a PKCE code challenge:
    every client but Forgejo, whose sign-in sends none, must."""
    return client_id != FORGE_CLIENT_ID


def forge_settings(environ: Mapping[str, str]) -> dict[str, Any]:
    """Return the settings of the OpenID provider and of Forgejo's API
    that ENVIRON decides, by their Django names.

    The result holds ``ORGSYNDB_URL``, the address people reach the site
    at, by default ``http://localhost:8000``, and
    ``ORGSYNDB_APP_INTERNAL_URL``, the application's address on the
    servers' network, by default ``http://app:8000``, both without a
    trailing slash; ``ORGSYNDB_FORGE_URL``, the address of Forgejo's API,
    ``ORGSYNDB_FORGE_PASSWORD``, the password of its admin account
    ``orgsyndb``, and ``ORGSYNDB_FORGE_CLIENT_SECRET``, Forgejo's client
    secret, each empty when unset; and ``OAUTH2_PROVIDER``, the settings
    of django-oauth-toolkit, whose ``OIDC_RSA_PRIVATE_KEY`` is the PEM
    text of ``ORGSYNDB_OIDC_KEY``, empty when it is unset, which turns
    the provider off. The issuer is ``<ORGSYNDB_URL>/lab/o``.
    Raise ImproperlyConfigured naming ``ORGSYNDB_OIDC_KEY`` when the key
    is malformed, as ``oidc_key`` does.
    """
    def text(name: str) -> str:
        return environ.get(name, "").strip()

    url = (text("ORGSYNDB_URL") or DEFAULT_URL).rstrip("/")
    internal = (text("ORGSYNDB_APP_INTERNAL_URL")
                or DEFAULT_APP_INTERNAL_URL).rstrip("/")
    return {
        "ORGSYNDB_URL": url,
        "ORGSYNDB_APP_INTERNAL_URL": internal,
        "ORGSYNDB_FORGE_URL": text("ORGSYNDB_FORGE_URL").rstrip("/"),
        "ORGSYNDB_FORGE_PASSWORD": text("ORGSYNDB_FORGE_PASSWORD"),
        "ORGSYNDB_FORGE_CLIENT_SECRET": text(
            "ORGSYNDB_FORGE_CLIENT_SECRET"),
        "OAUTH2_PROVIDER": {
            "OIDC_ENABLED": True,
            "OIDC_RSA_PRIVATE_KEY": oidc_key(text("ORGSYNDB_OIDC_KEY")),
            "OIDC_ISS_ENDPOINT": f"{url}/lab/o",
            "OAUTH2_VALIDATOR_CLASS": "accounts.oidc.ClaimsValidator",
            "SCOPES": {"openid": "OpenID Connect", "profile": "Profile",
                       "email": "Email address"},
            "DEFAULT_SCOPES": ["openid"],
            "PKCE_REQUIRED": pkce_required,
            "OIDC_RESPONSE_TYPES_SUPPORTED": ["code"],
        },
    }


def settings_from(environ: Mapping[str, str]) -> dict[str, Any]:
    """Return the settings ENVIRON decides, by their Django names.

    The result holds ``DEBUG`` from ``ORGSYNDB_DEBUG``, ``SECRET_KEY``
    from ``ORGSYNDB_SECRET_KEY``, ``ALLOWED_HOSTS`` from the
    comma-separated ``ORGSYNDB_ALLOWED_HOSTS``, ``DATABASES`` from
    ``ORGSYNDB_DATABASE_URL`` (by default the SQLite file
    ``webapp/db.sqlite3``), ``ORGSYNDB_DEMO`` from the flag of that name,
    which permits writing the demo data, and ``ORGSYNDB_BUILDER_TOKEN``,
    the token the builder signs its manifests with, empty when unset,
    which turns the manifest path off, and the settings
    ``forge_settings`` makes. With debug on, the secret key
    and the host list may be left out; the hosts are then ``localhost``
    and ``127.0.0.1``.
    Raise ImproperlyConfigured naming the variable when the secret key or
    the host list is missing outside debug, or a flag, the database URL
    or the OpenID key is malformed.
    """
    debug = flag(environ, "ORGSYNDB_DEBUG", False)
    secret_key = environ.get("ORGSYNDB_SECRET_KEY", "").strip()
    if not secret_key:
        if not debug:
            raise ImproperlyConfigured(
                "ORGSYNDB_SECRET_KEY is not set; set it to a long random "
                "text, or set ORGSYNDB_DEBUG=true for development")
        secret_key = DEBUG_SECRET_KEY
    hosts = [host.strip() for host in
             environ.get("ORGSYNDB_ALLOWED_HOSTS", "").split(",")
             if host.strip()]
    if not hosts:
        if not debug:
            raise ImproperlyConfigured(
                "ORGSYNDB_ALLOWED_HOSTS is not set; list the host names "
                "the site is reached by, separated by commas")
        hosts = list(DEBUG_HOSTS)
    url = (environ.get("ORGSYNDB_DATABASE_URL", "").strip()
           or f"sqlite:///{WEBAPP / 'db.sqlite3'}")
    return {
        "DEBUG": debug,
        "SECRET_KEY": secret_key,
        "ALLOWED_HOSTS": hosts,
        "DATABASES": {"default": database(url)},
        "ORGSYNDB_DEMO": flag(environ, "ORGSYNDB_DEMO", False),
        "ORGSYNDB_BUILDER_TOKEN": environ.get("ORGSYNDB_BUILDER_TOKEN",
                                              "").strip(),
        **forge_settings(environ),
    }
