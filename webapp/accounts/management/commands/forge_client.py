"""``manage.py forge_client``: register Forgejo as the OpenID client."""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from oauth2_provider.models import get_application_model

from orgsyndb_web.config import FORGE_CLIENT_ID


class Command(BaseCommand):
    help = ("Create or update the OpenID client forgejo from "
            "ORGSYNDB_FORGE_CLIENT_SECRET; do nothing when it is unset.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Make the client ``forgejo`` exactly what the provider needs:
        confidential, the authorization code flow, ID tokens signed
        with RS256, the one redirect URI
        ``<ORGSYNDB_URL>/git/user/oauth2/lab/callback``, no consent page
        and the secret ``ORGSYNDB_FORGE_CLIENT_SECRET``. Leave every
        client alone when the secret is unset."""
        secret = settings.ORGSYNDB_FORGE_CLIENT_SECRET
        if not secret:
            self.stdout.write("ORGSYNDB_FORGE_CLIENT_SECRET is not set; "
                              "the client forgejo is left as it is.")
            return
        application = get_application_model()
        redirect = (f"{settings.ORGSYNDB_URL}"
                    "/git/user/oauth2/lab/callback")
        _client, created = application.objects.update_or_create(
            client_id=FORGE_CLIENT_ID, defaults={
                "name": "Forgejo",
                "client_type": application.CLIENT_CONFIDENTIAL,
                "authorization_grant_type":
                    application.GRANT_AUTHORIZATION_CODE,
                "algorithm": application.RS256_ALGORITHM,
                "redirect_uris": redirect,
                "post_logout_redirect_uris": "",
                "skip_authorization": True,
                "hash_client_secret": True,
                "client_secret": secret,
            })
        self.stdout.write(("Created" if created else "Updated")
                          + f" the client {FORGE_CLIENT_ID}: {redirect}")
