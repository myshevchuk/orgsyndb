"""The settings the environment decides, read without touching Django's
settings machinery."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

WEBAPP = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = "/var/lib/orgsyndb/current/index.json"
DEBUG_SECRET_KEY = "django-insecure-orgsyndb-debug-only"
DEBUG_HOSTS = ["localhost", "127.0.0.1"]
TRUE = ("1", "true", "yes", "on")
FALSE = ("0", "false", "no", "off")


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


def settings_from(environ: Mapping[str, str]) -> dict[str, Any]:
    """Return the settings ENVIRON decides, by their Django names.

    The result holds ``DEBUG`` from ``ORGSYNDB_DEBUG``, ``SECRET_KEY``
    from ``ORGSYNDB_SECRET_KEY``, ``ALLOWED_HOSTS`` from the
    comma-separated ``ORGSYNDB_ALLOWED_HOSTS``, ``DATABASES`` from
    ``ORGSYNDB_DATABASE_URL`` (by default the SQLite file
    ``webapp/db.sqlite3``), ``ORGSYNDB_INDEX``, the path of the
    collection index, and ``ORGSYNDB_DEMO`` from the flag of that name,
    which permits writing the demo data. With debug on, the secret key
    and the host list may be left out; the hosts are then ``localhost``
    and ``127.0.0.1``.
    Raise ImproperlyConfigured naming the variable when the secret key or
    the host list is missing outside debug, or a flag or the database URL
    is malformed.
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
        "ORGSYNDB_INDEX": (environ.get("ORGSYNDB_INDEX", "").strip()
                           or DEFAULT_INDEX),
        "ORGSYNDB_DEMO": flag(environ, "ORGSYNDB_DEMO", False),
    }
