"""Tests of the OpenID Connect provider for Forgejo (web-app: OpenID
provider; Permissions for the provider's paths)."""

from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from . import make_user, page_text
from .collection_support import accept
from .forge_support import (CLIENT_SECRET, LOGIN, REDIRECT, ProviderCase,
                            provider_off, provider_settings, rsa_key,
                            sign_in_as)

DISCOVERY = "/lab/o/.well-known/openid-configuration"
KEYS = "/lab/o/.well-known/jwks.json"
NO_ACCESS = "Kein Zugang zu Forgejo"


def grants() -> int:
    from oauth2_provider.models import Grant
    return Grant.objects.count()


def application():
    from oauth2_provider.models import Application
    return Application.objects.get(client_id="forgejo")


class DiscoveryTests(ProviderCase):
    """Scenario: Discovery."""

    def document(self, client: Client | None = None, **extra: str) -> dict:
        answer = (client or Client()).get(DISCOVERY, **extra)
        self.assertEqual(answer.status_code, 200)
        return answer.json()

    def test_the_document_names_the_issuer_and_the_endpoints(self) -> None:
        found = self.document()
        self.assertEqual(found["issuer"], "http://localhost:8080/lab/o")
        self.assertEqual(found["authorization_endpoint"],
                         "http://localhost:8080/lab/o/authorize/")
        self.assertEqual(found["token_endpoint"],
                         "http://app:8000/lab/o/token/")
        self.assertEqual(found["userinfo_endpoint"],
                         "http://app:8000/lab/o/userinfo/")
        self.assertEqual(found["jwks_uri"],
                         "http://app:8000/lab/o/.well-known/jwks.json")

    def test_the_scopes_include_openid_profile_and_email(self) -> None:
        found = self.document()
        self.assertTrue({"openid", "profile", "email"}
                        <= set(found["scopes_supported"]))

    def test_the_document_says_the_tokens_are_signed_with_rs256(
            self) -> None:
        self.assertIn("RS256",
                      self.document()["id_token_signing_alg_values_supported"])

    def test_it_needs_no_sign_in(self) -> None:
        """Requirement: Permissions (the provider's paths do not
        redirect)."""
        self.assertEqual(Client().get(DISCOVERY).status_code, 200)

    def test_it_is_the_same_whichever_host_asks(self) -> None:
        """Requirement: OpenID provider (the issuer is the same
        whichever host the token was requested through)."""
        public = self.document()
        for host in ("app:8000", "lab.example.org"):
            with self.subTest(host=host):
                self.assertEqual(self.document(HTTP_HOST=host), public)

    def test_the_addresses_follow_the_settings(self) -> None:
        with override_settings(**provider_settings(
                ORGSYNDB_URL="https://lab.example.org/",
                ORGSYNDB_APP_INTERNAL_URL="http://app.internal:9000")):
            found = self.document()
        self.assertEqual(found["issuer"], "https://lab.example.org/lab/o")
        self.assertEqual(found["authorization_endpoint"],
                         "https://lab.example.org/lab/o/authorize/")
        self.assertEqual(found["token_endpoint"],
                         "http://app.internal:9000/lab/o/token/")
        self.assertEqual(found["userinfo_endpoint"],
                         "http://app.internal:9000/lab/o/userinfo/")
        self.assertEqual(
            found["jwks_uri"],
            "http://app.internal:9000/lab/o/.well-known/jwks.json")

    def test_the_keys_hold_the_public_key(self) -> None:
        answer = Client().get(KEYS)
        self.assertEqual(answer.status_code, 200)
        moduli = {key["n"] for key in answer.json()["keys"]
                  if key["kty"] == "RSA"}
        self.assertEqual(
            moduli, {rsa_key().export_public(as_dict=True)["n"]})


class SigningInTests(ProviderCase):
    """Scenario: Signing in to Forgejo."""

    def test_a_signed_in_account_is_sent_back_at_once_with_a_code(
            self) -> None:
        """Scenario: Signing in to Forgejo (the first answer); no
        consent page."""
        answer = self.authorize()
        self.assertEqual(answer.status_code, 302)
        target = urlsplit(answer["Location"])
        self.assertEqual(
            f"{target.scheme}://{target.netloc}{target.path}", REDIRECT)
        query = parse_qs(target.query)
        self.assertEqual(query["state"], ["st4te"])
        self.assertTrue(query["code"][0])
        self.assertEqual(grants(), 1)

    def test_a_second_request_passes_straight_through_too(self) -> None:
        for _ in range(2):
            self.assertEqual(self.authorize().status_code, 302)

    def test_the_id_token_is_signed_and_carries_the_claims(self) -> None:
        """Scenario: Signing in to Forgejo (the ID token)."""
        answer = self.sign_in_to_forgejo()
        header, claims = self.id_claims(answer["id_token"])
        self.assertEqual(header["alg"], "RS256")
        self.assertEqual(claims["iss"], "http://localhost:8080/lab/o")
        aud = claims["aud"]
        self.assertEqual([aud] if isinstance(aud, str) else aud,
                         ["forgejo"])
        self.assertEqual(claims["sub"], str(self.kl.pk))
        self.assertEqual(claims["nickname"], "klehmann")
        self.assertEqual(claims["preferred_username"], "klehmann")
        self.assertEqual(claims["name"], "Katrin Lehmann")
        self.assertEqual(claims["email"], "kl@example.org")

    def test_the_subject_is_the_primary_key_not_the_user_name(self) -> None:
        _header, claims = self.id_claims(
            self.sign_in_to_forgejo()["id_token"])
        self.assertIsInstance(claims["sub"], str)
        self.assertNotEqual(claims["sub"], "klehmann")

    def test_the_user_info_carries_the_same_claims(self) -> None:
        """Scenario: Signing in to Forgejo (as has the user info)."""
        answer = self.sign_in_to_forgejo()
        info = self.user_info(answer["access_token"])
        self.assertEqual(info.status_code, 200)
        found = info.json()
        self.assertEqual(found["sub"], str(self.kl.pk))
        self.assertEqual(found["nickname"], "klehmann")
        self.assertEqual(found["preferred_username"], "klehmann")
        self.assertEqual(found["name"], "Katrin Lehmann")
        self.assertEqual(found["email"], "kl@example.org")

    def test_the_id_token_names_the_authors_group(self) -> None:
        """Scenario: Signing in to Forgejo (the ID token carries
        `groups` `["authors"]`)."""
        _header, claims = self.id_claims(
            self.sign_in_to_forgejo()["id_token"])
        self.assertEqual(claims["groups"], ["authors"])

    def test_the_user_info_names_the_authors_group(self) -> None:
        """Scenario: Signing in to Forgejo (the user info carries
        `groups` `["authors"]`)."""
        answer = self.sign_in_to_forgejo()
        info = self.user_info(answer["access_token"])
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.json()["groups"], ["authors"])

    def test_groups_come_under_the_scope_profile(self) -> None:
        """Requirement: OpenID provider (`groups` under the scope
        `profile`)."""
        answer = self.sign_in_to_forgejo()
        self.assertIn("groups", self.id_claims(answer["id_token"])[1])
        code = self.code_of(self.authorize(scope="openid email"))
        answer = self.token(code)
        self.assertEqual(answer.status_code, 200, answer.content)
        _header, claims = self.id_claims(answer.json()["id_token"])
        self.assertNotIn("groups", claims)
        self.assertNotIn("nickname", claims)

    def test_every_account_is_an_author(self) -> None:
        """Requirement: OpenID provider (`groups`, the list
        `["authors"]` for every account)."""
        for name, initials, email in (("tbauer", "TB", "tb@example.org"),
                                      ("plain", "PL", "plain@example.org")):
            with self.subTest(account=name):
                self.client.force_login(
                    make_user(name, initials, email=email))
                answer = self.sign_in_to_forgejo()
                _header, claims = self.id_claims(answer["id_token"])
                self.assertEqual(claims["groups"], ["authors"])
                self.assertEqual(
                    self.user_info(answer["access_token"]).json()[
                        "groups"], ["authors"])

    def test_the_client_may_authenticate_with_a_basic_header(self) -> None:
        code = self.code_of(self.authorize())
        answer = self.token(code, basic=True)
        self.assertEqual(answer.status_code, 200, answer.content)
        self.assertIn("id_token", answer.json())

    def test_the_issuer_is_the_public_one_whichever_host_is_asked(
            self) -> None:
        """Requirement: OpenID provider (the issuer in every ID
        token)."""
        for host in ("app:8000", "testserver", "lab.example.org"):
            with self.subTest(host=host):
                answer = self.sign_in_to_forgejo(host=host)
                _header, claims = self.id_claims(answer["id_token"])
                self.assertEqual(claims["iss"], "http://localhost:8080/lab/o")

    def test_the_name_is_the_user_name_when_the_full_name_is_empty(
            self) -> None:
        plain = make_user("plain", "PL", email="plain@example.org")
        self.client.force_login(plain)
        _header, claims = self.id_claims(
            self.sign_in_to_forgejo()["id_token"])
        self.assertEqual(claims["name"], "plain")
        self.assertEqual(claims["sub"], str(plain.pk))

    def test_each_account_gets_its_own_claims(self) -> None:
        other = make_user("tbauer", "TB", "Tobias", "Bauer",
                          email="tb@example.org")
        self.client.force_login(other)
        _header, claims = self.id_claims(
            self.sign_in_to_forgejo()["id_token"])
        self.assertEqual((claims["sub"], claims["nickname"], claims["name"],
                          claims["email"]),
                         (str(other.pk), "tbauer", "Tobias Bauer",
                          "tb@example.org"))

    def test_no_code_challenge_is_needed(self) -> None:
        """Requirement: OpenID provider (the authorization code flow
        without PKCE)."""
        self.assertNotIn("code_challenge", self.authorize_url())
        self.assertEqual(self.authorize().status_code, 302)

    def test_a_wrong_secret_is_refused_with_401_and_no_token(self) -> None:
        """Scenario: A wrong secret."""
        code = self.code_of(self.authorize())
        answer = self.token(code, secret="another-secret")
        self.assertEqual(answer.status_code, 401)
        self.assertNotIn(b"access_token", answer.content)
        self.assertNotIn(b"id_token", answer.content)

    def test_a_wrong_secret_in_a_basic_header_is_refused_too(self) -> None:
        code = self.code_of(self.authorize())
        answer = self.token(code, secret="another-secret", basic=True)
        self.assertEqual(answer.status_code, 401)

    def test_no_secret_is_refused(self) -> None:
        code = self.code_of(self.authorize())
        answer = Client().post("/lab/o/token/", {
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": REDIRECT, "client_id": "forgejo"},
            HTTP_HOST="app:8000")
        self.assertEqual(answer.status_code, 401)
        self.assertNotIn(b"access_token", answer.content)

    def test_the_token_path_does_not_redirect_to_sign_in(self) -> None:
        """Requirement: Permissions (the token path authenticates the
        client)."""
        answer = Client().post("/lab/o/token/", {}, HTTP_HOST="app:8000")
        self.assertNotEqual(answer.status_code, 302)
        self.assertIn(answer.status_code, (400, 401))

    def test_the_user_info_path_needs_a_token_and_does_not_redirect(
            self) -> None:
        """Requirement: Permissions (the user-info path authenticates the
        token)."""
        for extra in ({}, {"HTTP_AUTHORIZATION": "Bearer not-a-token"}):
            with self.subTest(extra=extra):
                answer = Client().get("/lab/o/userinfo/", HTTP_HOST="app:8000",
                                      **extra)
                self.assertIn(answer.status_code, (400, 401, 403))
                self.assertNotIn(b"klehmann", answer.content)

    def test_a_signed_in_session_does_not_open_the_user_info(self) -> None:
        answer = self.client.get("/lab/o/userinfo/", HTTP_HOST="app:8000")
        self.assertIn(answer.status_code, (400, 401, 403))

    def test_another_redirect_address_gets_no_code(self) -> None:
        """Requirement: OpenID provider (the one redirect URI)."""
        answer = self.authorize(redirect_uri="https://evil.example/cb")
        self.assertNotEqual(answer.status_code, 302)
        self.assertEqual(grants(), 0)

    def test_an_unknown_client_gets_no_code(self) -> None:
        answer = self.authorize(client_id="someone-else")
        self.assertNotEqual(answer.status_code, 302)
        self.assertEqual(grants(), 0)


class AuthorizationAccessTests(ProviderCase):

    def test_without_a_sign_in_it_redirects_to_the_sign_in_page(self) -> None:
        """Scenario: Not signed in."""
        path = self.authorize_url()
        answer = Client().get(path)
        self.assertEqual(answer.status_code, 302)
        target = urlsplit(answer["Location"])
        self.assertEqual(target.path, LOGIN)
        self.assertEqual(parse_qs(target.query)["next"], [path])
        self.assertEqual(grants(), 0)

    def test_a_deactivated_account_authorizes_nothing(self) -> None:
        """Requirement: OpenID provider (an inactive account authorizes
        nothing)."""
        self.kl.is_active = False
        self.kl.save()
        answer = self.authorize()
        self.assertEqual(answer.status_code, 302)
        self.assertEqual(urlsplit(answer["Location"]).path, LOGIN)
        self.assertEqual(grants(), 0)

    def test_an_account_without_an_address_gets_the_page(self) -> None:
        """Scenario: An account without an address."""
        bare = make_user("bare", "BA", "Bea", "Bare")
        self.client.force_login(bare)
        answer = self.authorize()
        self.assertIn(answer.status_code, (200, 403))
        self.assertIn(NO_ACCESS, answer.content.decode("utf-8"))
        self.assertEqual(grants(), 0)

    def test_the_page_says_that_staff_must_give_an_address(self) -> None:
        bare = make_user("bare", "BA", "Bea", "Bare")
        self.client.force_login(bare)
        self.assertRegex(page_text(self.authorize()), r"(?i)e-?mail")

    def test_the_page_is_in_english_when_the_site_is(self) -> None:
        accept("en")
        bare = make_user("bare", "BA", "Bea", "Bare")
        self.client.force_login(bare)
        answer = self.authorize()
        self.assertIn("No access to Forgejo", answer.content.decode("utf-8"))
        self.assertEqual(grants(), 0)

    def test_an_account_without_an_address_is_sent_nowhere(self) -> None:
        bare = make_user("bare", "BA", "Bea", "Bare")
        self.client.force_login(bare)
        self.assertNotIn("Location", self.authorize())


class ProviderOffTests(TestCase):
    """Scenario: Provider off."""

    PATHS = ("/lab/o/.well-known/openid-configuration", "/lab/o/authorize/",
             "/lab/o/token/", "/lab/o/userinfo/",
             "/lab/o/.well-known/jwks.json", "/lab/o/")

    def test_every_path_answers_404_without_a_key(self) -> None:
        with provider_off():
            for path in self.PATHS:
                with self.subTest(path=path, method="GET"):
                    self.assertEqual(Client().get(path).status_code, 404)
                with self.subTest(path=path, method="POST"):
                    self.assertEqual(Client().post(path, {}).status_code,
                                     404)

    def test_the_authorization_path_answers_404_even_when_signed_in(
            self) -> None:
        with provider_off():
            self.client.force_login(make_user("kl", "KL",
                                              email="kl@example.org"))
            self.assertEqual(self.client.get(
                "/lab/o/authorize/?client_id=forgejo").status_code, 404)

    def test_the_provider_is_on_or_off_with_the_key_per_request(
            self) -> None:
        with override_settings(**provider_settings()):
            self.assertEqual(Client().get(DISCOVERY).status_code, 200)
            with provider_off():
                self.assertEqual(Client().get(DISCOVERY).status_code, 404)
            self.assertEqual(Client().get(DISCOVERY).status_code, 200)


class ForgeClientTests(TestCase):
    """Requirement: OpenID provider (`manage.py forge_client`)."""

    def run_command(self, **env: str) -> None:
        with override_settings(**provider_settings(**env)):
            call_command("forge_client")

    def exchange(self, secret: str, **env: str) -> int:
        """Authorize as a fresh account and post the code with SECRET;
        return the token endpoint's status."""
        with override_settings(**provider_settings(**env)):
            user = get_user_model().objects.filter(
                username="klehmann").first() or make_user(
                    "klehmann", "KL", "Katrin", "Lehmann",
                    email="kl@example.org")
            return sign_in_as(user, secret=secret).status_code

    def test_it_creates_the_client_forgejo(self) -> None:
        self.run_command()
        client = application()
        self.assertEqual(client.client_id, "forgejo")
        self.assertEqual(client.client_type, "confidential")
        self.assertEqual(client.authorization_grant_type,
                         "authorization-code")
        self.assertEqual(client.algorithm, "RS256")
        self.assertTrue(client.skip_authorization)
        self.assertEqual(client.redirect_uris.split(), [REDIRECT])

    def test_the_client_works_with_the_secret(self) -> None:
        self.run_command()
        self.assertEqual(self.exchange(CLIENT_SECRET), 200)

    def test_without_a_secret_it_does_nothing(self) -> None:
        from oauth2_provider.models import Application
        self.run_command(ORGSYNDB_FORGE_CLIENT_SECRET="")
        self.assertEqual(Application.objects.count(), 0)

    def test_without_a_secret_it_leaves_an_existing_client_alone(
            self) -> None:
        self.run_command()
        before = application().redirect_uris
        self.run_command(ORGSYNDB_FORGE_CLIENT_SECRET="",
                         ORGSYNDB_URL="https://other.example.org")
        self.assertEqual(application().redirect_uris, before)

    def test_run_again_it_updates_instead_of_adding(self) -> None:
        from oauth2_provider.models import Application
        self.run_command()
        first = application().pk
        self.run_command()
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(application().pk, first)

    def test_the_redirect_address_follows_the_public_address(self) -> None:
        self.run_command()
        self.run_command(ORGSYNDB_URL="https://lab.example.org/")
        self.assertEqual(
            application().redirect_uris.split(),
            ["https://lab.example.org/git/user/oauth2/lab/callback"])

    def test_it_restores_what_was_changed_by_hand(self) -> None:
        self.run_command()
        client = application()
        client.skip_authorization = False
        client.redirect_uris = "https://evil.example/cb"
        client.algorithm = "HS256"
        client.save()
        self.run_command()
        client = application()
        self.assertTrue(client.skip_authorization)
        self.assertEqual(client.redirect_uris.split(), [REDIRECT])
        self.assertEqual(client.algorithm, "RS256")

    def test_a_changed_secret_replaces_the_old_one(self) -> None:
        self.run_command(ORGSYNDB_FORGE_CLIENT_SECRET="the-old-secret")
        self.run_command(ORGSYNDB_FORGE_CLIENT_SECRET="the-new-secret")
        self.assertEqual(self.exchange("the-new-secret"), 200)
        self.assertEqual(self.exchange("the-old-secret"), 401)


class DeactivatedAfterIssueTests(ProviderCase):
    """Scenario: Deactivated after the code."""

    def deactivate(self) -> None:
        self.kl.is_active = False
        self.kl.save()

    def test_a_code_of_an_account_deactivated_since_is_refused(
            self) -> None:
        code = self.code_of(self.authorize())
        self.deactivate()
        answer = self.token(code)
        self.assertNotEqual(answer.status_code, 200)
        self.assertNotIn(b"access_token", answer.content)
        self.assertNotIn(b"id_token", answer.content)

    def test_the_user_info_of_an_earlier_access_token_is_refused(
            self) -> None:
        answer = self.sign_in_to_forgejo()
        self.deactivate()
        info = self.user_info(answer["access_token"])
        self.assertIn(info.status_code, (400, 401, 403))
        self.assertNotIn(b"klehmann", info.content)

    def test_a_refresh_token_of_an_account_deactivated_since_is_refused(
            self) -> None:
        answer = self.sign_in_to_forgejo()
        self.assertIn("refresh_token", answer)
        self.deactivate()
        refreshed = Client().post("/lab/o/token/", {
            "grant_type": "refresh_token",
            "refresh_token": answer["refresh_token"],
            "client_id": "forgejo", "client_secret": CLIENT_SECRET},
            HTTP_HOST="app:8000")
        self.assertNotEqual(refreshed.status_code, 200)
        self.assertNotIn(b"access_token", refreshed.content)

    def test_a_refresh_token_of_an_active_account_works(self) -> None:
        answer = self.sign_in_to_forgejo()
        refreshed = Client().post("/lab/o/token/", {
            "grant_type": "refresh_token",
            "refresh_token": answer["refresh_token"],
            "client_id": "forgejo", "client_secret": CLIENT_SECRET},
            HTTP_HOST="app:8000")
        self.assertEqual(refreshed.status_code, 200, refreshed.content)
