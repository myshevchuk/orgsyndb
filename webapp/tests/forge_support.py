"""Helpers of the tests of the Forgejo sign-in and Forgejo accounts
(web-app: OpenID provider, Forgejo accounts).

``FakeForgejo`` answers the part of Forgejo 15's admin API the lab
application uses, as Forgejo does:

- ``GET /api/v1/admin/users``, with basic authentication as
  ``orgsyndb``, answers a JSON list of users, each ``{id, login,
  login_name, source_id, email, full_name, prohibit_login}``. The query
  ``login_name`` and ``source_id`` filter it; ``page`` (from 1) and
  ``limit`` page it, a missing ``limit`` meaning 30 and none above 50
  being given. The source ``lab`` has ``source_id`` 1, a local account 0.
- ``PATCH /api/v1/admin/users/<login>`` takes a JSON object that must
  carry the account's own ``login_name`` and ``source_id`` (422
  otherwise) and may carry ``prohibit_login``, ``email`` and
  ``full_name``, which it sets; it answers the account. An email that
  another account holds, regardless of case, is refused with 422 and
  changes nothing, as Forgejo takes each address once.
- A request with other credentials is answered 401, a path or method
  besides these 404 or 405.

Every request is recorded in ``calls``, those with wrong credentials
too. Nothing here imports the application at module level; the
functions that need it import it when they are called.
"""

import base64
import functools
import json
import socket
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from django.core.management import call_command
from django.test import TestCase, TransactionTestCase, override_settings

LAB = 1
LOCAL = 0
ADMIN_LOGIN = "orgsyndb"
ADMIN_PASSWORD = "forge-admin-password"
CLIENT_SECRET = "forgejo-client-secret"
PUBLIC_URL = "http://localhost:8080"
REDIRECT = f"{PUBLIC_URL}/git/user/oauth2/lab/callback"
WARNING = ("Forgejo wurde nicht aktualisiert; manage.py forge_accounts "
           "gleicht es ab.")
WARNING_EN = ("Forgejo was not updated; manage.py forge_accounts brings "
              "it in line.")
LOGIN = "/lab/accounts/login/"


@dataclass
class Call:
    """A request the fake received: its METHOD, PATH (without the
    query), QUERY, JSON BODY (None when there was none) and the user
    name it authenticated with (None when it sent none)."""

    method: str
    path: str
    query: dict[str, list[str]]
    body: Any
    user: str | None
    authorized: bool


@dataclass
class FakeForgejo:
    """A Forgejo admin API on 127.0.0.1, in a thread; use as a context
    manager or call ``start`` and ``stop``.

    ``refuse`` makes every authorized PATCH answer that status without
    changing anything.
    """

    password: str = ADMIN_PASSWORD
    refuse: int | None = None
    users: list[dict[str, Any]] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.lock = threading.Lock()
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        """The address to give as ``ORGSYNDB_FORGE_URL``."""
        assert self.server is not None, "the fake is not started"
        return f"http://127.0.0.1:{self.server.server_address[1]}/api/v1"

    def add_user(self, login: str, login_name: str, source_id: int = LAB,
                 email: str = "", full_name: str = "",
                 prohibit_login: bool = False) -> dict[str, Any]:
        """Add an account and return it; its ``id`` is the next number."""
        user = {"id": len(self.users) + 1, "login": login,
                "login_name": login_name, "source_id": source_id,
                "email": email, "full_name": full_name,
                "prohibit_login": prohibit_login}
        self.users.append(user)
        return user

    def user(self, login: str) -> dict[str, Any]:
        """Return the account with the login LOGIN."""
        return next(u for u in self.users if u["login"] == login)

    def sole_patch(self, case: TransactionTestCase) -> Call:
        """Return the one PATCH request received; fail CASE when there
        were none or several."""
        found = self.patches()
        case.assertEqual(len(found), 1, f"PATCH requests: {found}")
        return found[0]

    def patches(self) -> list[Call]:
        """Return the PATCH requests received, authorized or not."""
        return [c for c in self.calls if c.method == "PATCH"]

    def start(self) -> "FakeForgejo":
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def answer(self, status: int, payload: Any,
                       headers: dict[str, str] | None = None) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

            def credentials(self) -> tuple[str | None, bool]:
                header = self.headers.get("Authorization", "")
                scheme, _space, given = header.partition(" ")
                if scheme != "Basic":
                    return None, False
                try:
                    text = base64.b64decode(given).decode("utf-8")
                except ValueError:
                    return None, False
                user, _colon, password = text.partition(":")
                return user, (user == ADMIN_LOGIN
                              and password == fake.password)

            def handle_any(self) -> None:
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = None
                user, authorized = self.credentials()
                call = Call(self.command, parts.path, parse_qs(parts.query),
                            body, user, authorized)
                with fake.lock:
                    fake.calls.append(call)
                    if not authorized:
                        self.answer(401, {"message": "invalid credentials"},
                                    {"WWW-Authenticate": "Basic"})
                    else:
                        self.route(call, raw)

            def route(self, call: Call, raw: bytes) -> None:
                base = "/api/v1/admin/users"
                if call.path == base and call.method == "GET":
                    self.listing(call)
                elif call.path.startswith(base + "/") and (
                        call.method == "PATCH"):
                    self.patch(call, unquote(call.path[len(base) + 1:]),
                               raw)
                elif call.path == base or call.path.startswith(base + "/"):
                    self.answer(405, {"message": "method not allowed"})
                else:
                    self.answer(404, {"message": "not found"})

            def listing(self, call: Call) -> None:
                found = fake.users
                for key in ("login_name", "source_id"):
                    if key in call.query:
                        wanted = call.query[key][0]
                        found = [u for u in found
                                 if str(u[key]) == wanted]
                limit = min(int(call.query.get("limit", ["30"])[0]), 50)
                page = max(int(call.query.get("page", ["1"])[0]), 1)
                shown = found[(page - 1) * limit:page * limit]
                self.answer(200, shown,
                            {"X-Total-Count": str(len(found))})

            def patch(self, call: Call, login: str, raw: bytes) -> None:
                target = next((u for u in fake.users
                               if u["login"] == login), None)
                body = call.body
                if target is None:
                    self.answer(404, {"message": "user does not exist"})
                elif not isinstance(body, dict) or (
                        body.get("login_name") != target["login_name"]
                        or body.get("source_id") != target["source_id"]):
                    self.answer(422, {"message": "login_name and "
                                      "source_id are required"})
                elif fake.refuse is not None:
                    self.answer(fake.refuse, {"message": "refused"})
                elif "email" in body and any(
                        u is not target
                        and u["email"].lower() == str(body["email"]).lower()
                        for u in fake.users):
                    self.answer(422, {"message": "e-mail already in use"})
                else:
                    for key in ("prohibit_login", "email", "full_name"):
                        if key in body:
                            target[key] = body[key]
                    self.answer(200, target)

            do_GET = do_PATCH = do_POST = do_PUT = do_DELETE = handle_any

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()
        return self

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread is not None:
            self.thread.join(5)
            self.thread = None

    def __enter__(self) -> "FakeForgejo":
        return self.start()

    def __exit__(self, *exc: Any) -> None:
        self.stop()


def closed_forge_url() -> str:
    """Return an ``ORGSYNDB_FORGE_URL`` whose port nothing listens on."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}/api/v1"


def configured(url: str, password: str = ADMIN_PASSWORD) -> Any:
    """Return a context manager that gives the application the Forgejo
    API at URL and the admin password PASSWORD."""
    return override_settings(ORGSYNDB_FORGE_URL=url,
                             ORGSYNDB_FORGE_PASSWORD=password)


class ForgeCase(TransactionTestCase):
    """A test case with a running fake Forgejo that the application is
    configured to use, a staff user ``boss`` signed in, and the
    accounts ``tbauer`` (active, with the address ``tbauer@example.org``)
    and ``aschmidt``, each with its Forgejo account, whose login name is
    the lab account's primary key.

    Its transactions commit, as a running site's do, so that what the
    application does once a save has committed happens within the
    test."""

    def setUp(self) -> None:
        self.fake = FakeForgejo()
        self.fake.start()
        self.addCleanup(self.fake.stop)
        self.enterContext(configured(self.fake.url))
        from . import make_user
        self.boss = make_user("boss", "BO", "Berta", "Boss", is_staff=True,
                              is_superuser=True)
        self.tb = make_user("tbauer", "TB", "Tobias", "Bauer",
                            email="tbauer@example.org")
        self.asc = make_user("aschmidt", "AS", "Anna", "Schmidt",
                             email="aschmidt@example.org")
        self.forge_tb = self.fake.add_user(
            "tbauer", str(self.tb.pk), email="tbauer@example.org",
            full_name="Tobias Bauer")
        self.forge_as = self.fake.add_user(
            "aschmidt", str(self.asc.pk), email="aschmidt@example.org",
            full_name="Anna Schmidt")
        self.client.force_login(self.boss)

    def change_url(self, user: Any) -> str:
        return f"/lab/admin/accounts/user/{user.pk}/change/"

    def admin_change(self, user: Any, **over: Any) -> Any:
        """Post the admin's change form of USER as it stands with the
        values OVER; a value None leaves the control out, as an
        unchecked box does. Follow the redirect and return the page."""
        from . import page
        from .test_accounts import form_data
        data = form_data(page(self.client.get(self.change_url(user))))
        for name, value in over.items():
            if value is None:
                data.pop(name, None)
            else:
                data[name] = value
        return self.client.post(self.change_url(user), data, follow=True)

    def page_html(self, response: Any) -> str:
        import html
        return html.unescape(response.content.decode("utf-8"))


# ---------------------------------------------------------------------------
# The OpenID provider


@functools.cache
def rsa_key() -> Any:
    """A 2048-bit RSA key, made once per process."""
    from jwcrypto import jwk
    return jwk.JWK.generate(kty="RSA", size=2048)


@functools.cache
def key_pem() -> bytes:
    return rsa_key().export_to_pem(private_key=True, password=None)


def public_pem() -> bytes:
    """The PEM of the test key's public half."""
    return rsa_key().export_to_pem(private_key=False, password=None)


def key_setting() -> str:
    """The key as ``ORGSYNDB_OIDC_KEY`` holds it: the PEM in base64 on
    one line."""
    return base64.b64encode(key_pem()).decode("ascii")


def provider_environ(**over: str) -> dict[str, str]:
    """The environment of a lab application that is an OpenID provider
    for Forgejo, with OVER on top."""
    return {"ORGSYNDB_URL": PUBLIC_URL, "ORGSYNDB_OIDC_KEY": key_setting(),
            "ORGSYNDB_FORGE_CLIENT_SECRET": CLIENT_SECRET, **over}


def provider_settings(**over: str) -> dict[str, Any]:
    """The Django settings that ``orgsyndb_web.config.forge_settings``
    makes of ``provider_environ(**over)``, with the host ``app``
    allowed besides the tests' hosts."""
    from django.conf import settings
    from orgsyndb_web.config import forge_settings
    return {**forge_settings(provider_environ(**over)),
            "ALLOWED_HOSTS": [*settings.ALLOWED_HOSTS, "app"]}


def provider_off() -> Any:
    """A context manager under which no OIDC key is set."""
    from orgsyndb_web.config import forge_settings
    return override_settings(**forge_settings({}))


def authorize_url(**over: str) -> str:
    """The authorization request Forgejo sends, with OVER on top."""
    from urllib.parse import urlencode
    query = {"client_id": "forgejo", "redirect_uri": REDIRECT,
             "response_type": "code", "scope": "openid profile email",
             "state": "st4te", **over}
    return "/lab/o/authorize/?" + urlencode(query)


def code_of(response: Any) -> str:
    """The code in the redirect that RESPONSE is."""
    from urllib.parse import parse_qs, urlsplit
    assert response.status_code == 302, response.status_code
    return parse_qs(urlsplit(response["Location"]).query)["code"][0]


def token_request(code: str, secret: str = CLIENT_SECRET,
                  host: str = "app:8000", basic: bool = False) -> Any:
    """Post the CODE to the token endpoint as Forgejo does, from a client
    of its own, from the HOST, with the SECRET in the body or, with
    BASIC, in a basic authentication header."""
    from django.test import Client
    data = {"grant_type": "authorization_code", "code": code,
            "redirect_uri": REDIRECT}
    extra: dict[str, str] = {"HTTP_HOST": host}
    if basic:
        pair = base64.b64encode(f"forgejo:{secret}".encode()).decode()
        extra["HTTP_AUTHORIZATION"] = f"Basic {pair}"
    else:
        data.update(client_id="forgejo", client_secret=secret)
    return Client().post("/lab/o/token/", data, **extra)


def sign_in_as(user: Any, **kwargs: Any) -> Any:
    """Sign USER in with a client of its own, authorize as Forgejo does
    and exchange the code; return the token answer."""
    from django.test import Client
    client = Client()
    client.force_login(user)
    return token_request(code_of(client.get(authorize_url())), **kwargs)


class ProviderCase(TestCase):
    """A test case under which the application is a provider for
    Forgejo: the key is set, ``forge_client`` has made the client, and
    ``klehmann`` (address ``kl@example.org``, name Katrin Lehmann) is
    signed in."""

    OVERRIDES: dict[str, str] = {}

    def setUp(self) -> None:
        self.enterContext(override_settings(
            **provider_settings(**self.OVERRIDES)))
        call_command("forge_client")
        from . import make_user
        self.kl = make_user("klehmann", "KL", "Katrin", "Lehmann",
                            email="kl@example.org")
        self.client.force_login(self.kl)

    def authorize_url(self, **over: str) -> str:
        return authorize_url(**over)

    def authorize(self, **over: str) -> Any:
        """Request the authorization endpoint, signed in as the
        account of ``self.client``."""
        return self.client.get(authorize_url(**over))

    def code_of(self, response: Any) -> str:
        return code_of(response)

    def token(self, code: str, **kwargs: Any) -> Any:
        return token_request(code, **kwargs)

    def sign_in_to_forgejo(self, **kwargs: Any) -> dict[str, Any]:
        """Authorize and exchange the code; return the token answer's
        JSON."""
        answer = token_request(code_of(self.authorize()), **kwargs)
        assert answer.status_code == 200, answer.content
        return answer.json()

    @staticmethod
    def id_claims(id_token: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Verify the signature of ID_TOKEN with the test key; return its
        header and its claims."""
        from jwcrypto import jwt
        token = jwt.JWT(jwt=id_token, key=rsa_key(), algs=["RS256"])
        return json.loads(token.header), json.loads(token.claims)

    @staticmethod
    def user_info(access_token: str, host: str = "app:8000") -> Any:
        from django.test import Client
        return Client().get(
            "/lab/o/userinfo/", HTTP_HOST=host,
            HTTP_AUTHORIZATION=f"Bearer {access_token}")
