"""The application's user model and the accounts' access tokens."""

import functools
import hashlib
import logging
import secrets
from datetime import datetime
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from orgsyndb_web import lock
from orgsyndb_web.lock import LockedQuerySet


USER_NAME = r"\A[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*\Z"

# The user names Forgejo 15 reserves for itself, and the patterns of
# those it refuses, from reservedUsernames and reservedUserPatterns in
# models/user/user.go of Forgejo 15.0.11. Forgejo compares them in lower
# case.
FORGEJO_RESERVED_NAMES = frozenset({
    ".", "..", "-", ".well-known",
    "api", "metrics", "v2",
    "assets", "attachments",
    "avatar", "avatars", "repo-avatars",
    "captcha", "login", "org", "repo", "user",
    "admin", "explore", "issues", "pulls", "milestones", "notifications",
    "report_abuse",
    "favicon.ico", "manifest.json", "robots.txt", "sitemap.xml",
    "ssh_info", "swagger.v1.json",
    "ghost", "gitea-actions", "forgejo-actions",
})
FORGEJO_RESERVED_SUFFIXES = (".keys", ".gpg", ".rss", ".atom", ".png")
# The name of the Forgejo admin account the application uses.
FORGE_ADMIN_NAME = "orgsyndb"

log = logging.getLogger(__name__)


def validate_unreserved(value: str) -> None:
    """Raise ValidationError when the user name VALUE is, in any case,
    one Forgejo 15 reserves, ends in a suffix Forgejo refuses, or is
    ``orgsyndb``."""
    name = value.lower()
    if (name in FORGEJO_RESERVED_NAMES or name == FORGE_ADMIN_NAME
            or name.endswith(FORGEJO_RESERVED_SUFFIXES)):
        raise ValidationError(
            _("This user name is reserved for Forgejo."), code="reserved")


# The fields of an account the registry snapshot carries, as its user
# name and its name.
SNAPSHOT_FIELDS = frozenset({"username", "first_name", "last_name"})
# The fields of an account its Forgejo account follows.
FORGE_FIELDS = ("is_active", "email", "username", "first_name",
                "last_name")
EMAIL_TAKEN = "email_taken"
USERNAME_TAKEN = "username_taken"
# The field each code of a constraint's error belongs to.
CONSTRAINT_FIELDS = {EMAIL_TAKEN: "email", USERNAME_TAKEN: "username"}


class AccountManager(UserManager.from_queryset(LockedQuerySet)):
    """Django's manager of users, whose bulk writes take the import
    lock as ``LockedQuerySet`` states."""


class User(AbstractUser):
    """A person who signs in or is named on records.

    USERNAME is at most 40 ASCII letters and digits, with single ``.``,
    ``-`` or ``_`` between them, the user names Forgejo accepts, unique
    regardless of case, and none that Forgejo reserves
    (``validate_unreserved``). Procedure files name their authors by it,
    so the admin offers no way to change it once the account exists. INITIALS, one to five letters or digits,
    name the user in lists; they are stored in upper case and unique
    regardless of case. EMAIL may be empty and is otherwise unique
    regardless of case. An account without a usable password cannot
    sign in and can still be named on records.

    Once a save of an account whose ``is_active``, email or display
    name changed has committed, its Forgejo account is set in line with
    the account as stored (``accounts.forge``); ``forge_failed`` then
    tells whether that failed.
    """

    username = models.CharField(
        _("username"), max_length=40, unique=True,
        validators=[RegexValidator(
            USER_NAME,
            _("Enter at most 40 letters or digits, with single dots, "
              "hyphens or underscores between them.")),
            validate_unreserved],
        help_text=_("At most 40 letters or digits, with single dots, "
                    "hyphens or underscores between them. It cannot be "
                    "changed later."),
        error_messages={
            "unique": _("A user with that username already exists.")})
    initials = models.CharField(
        _("initials"), max_length=5, unique=True,
        validators=[RegexValidator(
            r"^[A-Za-z0-9]{1,5}$",
            _("Enter one to five letters or digits."))],
        help_text=_("One to five letters or digits, shown in lists."),
        error_messages={"unique": _("Another account has these initials.")})

    REQUIRED_FIELDS = ["email", "initials"]

    objects = AccountManager()

    forge_failed = False

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"
        constraints = [
            models.UniqueConstraint(
                Lower("username"), name="accounts_user_username_unique",
                violation_error_code=USERNAME_TAKEN,
                violation_error_message=_(
                    "A user with that username already exists.")),
            models.UniqueConstraint(
                Lower("email"), name="accounts_user_email_unique",
                condition=~models.Q(email=""),
                violation_error_code=EMAIL_TAKEN,
                violation_error_message=_(
                    "Another account has this email address.")),
        ]

    @property
    def display_name(self) -> str:
        """The full name, or the user name when the full name is
        empty."""
        return self.get_full_name() or self.get_username()

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the account with its initials in upper case, under the
        import lock (``orgsyndb_web.lock``), since the registry
        snapshot's digest covers its user name and name, and wake the
        builder once the transaction commits (``orgsyndb_web.wake``); a
        save of only other fields, such as a sign-in's ``last_login``,
        takes no lock and wakes nothing. When a save of an existing
        account that changes its ``is_active``, email address or display
        name commits, its Forgejo account is set in line, as
        ``update_forge`` does; a save rolled back calls nothing."""
        self.initials = (self.initials or "").upper()
        fields = kwargs.get("update_fields")
        before = self.forge_state_saved(fields)
        if fields is not None and not SNAPSHOT_FIELDS & set(fields):
            super().save(*args, **kwargs)
        else:
            with transaction.atomic():
                lock.hold_covered()
                super().save(*args, **kwargs)
        self.forge_failed = False
        if before is not None:
            transaction.on_commit(functools.partial(self.update_forge,
                                                    before))

    def forge_state(self) -> tuple[Any, ...]:
        """Return the values of the account its Forgejo account
        follows."""
        return tuple(getattr(self, name) for name in FORGE_FIELDS)

    def forge_state_saved(self, fields: Any) -> tuple[Any, ...] | None:
        """Return ``forge_state`` of the account as saved, before a save
        of the fields FIELDS (None meaning every field); return None
        when that save cannot change it, the account is new, or Forgejo
        is not configured."""
        from accounts import forge
        if (self._state.adding or self.pk is None
                or not forge.configured()
                or (fields is not None
                    and not set(FORGE_FIELDS) & set(fields))):
            return None
        saved = type(self).objects.filter(pk=self.pk).values_list(
            *FORGE_FIELDS).first()
        return None if saved is None else tuple(saved)

    def update_forge(self, before: tuple[Any, ...]) -> None:
        """Set the Forgejo account in line with the account as stored
        now, when ``forge_state`` of that differs from BEFORE; on
        failure log it and set ``forge_failed``, leaving the account
        saved."""
        from accounts import forge
        stored = type(self).objects.filter(pk=self.pk).first()
        if stored is None or stored.forge_state() == before:
            return
        try:
            forge.push(stored)
        except forge.ForgeError as exc:
            log.warning("Forgejo account of %s not updated: %s",
                        stored.get_username(), exc)
            self.forge_failed = True

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        """Delete the account, as ``Model.delete`` does, under the
        import lock, and wake the builder once the transaction commits;
        return what it returns."""
        with transaction.atomic():
            lock.hold_covered()
            return super().delete(*args, **kwargs)

    def clean(self) -> None:
        """Normalize the account as ``AbstractUser.clean`` does, and
        put the initials in upper case."""
        super().clean()
        self.initials = (self.initials or "").upper()

    def validate_constraints(self, exclude: Any = None) -> None:
        """Validate the constraints as ``Model.validate_constraints``
        does, reporting a user name or an email address that another
        account has, regardless of case, on its own field."""
        try:
            super().validate_constraints(exclude)
        except ValidationError as exc:
            errors = exc.update_error_dict({})
            for error in errors.pop(NON_FIELD_ERRORS, []):
                field = CONSTRAINT_FIELDS.get(getattr(error, "code", None),
                                              NON_FIELD_ERRORS)
                errors.setdefault(field, []).append(error)
            raise ValidationError(errors) from None


# The text every access token begins with.
TOKEN_PREFIX = "osdb_"
# The number of random bytes of a token, 43 characters in URL-safe
# base64.
TOKEN_BYTES = 32


def current_time() -> datetime:
    """Return the current time, as ``django.utils.timezone.now`` gives
    it at the moment of the call."""
    return timezone.now()


def token_digest(token: str) -> str:
    """Return the SHA-256 digest of the access token TOKEN, 64
    lower-case hexadecimal digits."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccessToken(models.Model):
    """A personal access token, by which a program outside the browser
    acts as the account ``user``.

    The token itself is never stored, only its SHA-256 ``digest``, so it
    cannot be recovered from the row. Deleting the row revokes the
    token; deleting the account deletes its tokens. ``last_used_at`` is
    None until a request is made with the token.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("Account"),
                             on_delete=models.CASCADE,
                             related_name="access_tokens")
    name = models.CharField(_("Name"), max_length=100)
    digest = models.CharField(
        _("Digest"), max_length=64, unique=True,
        validators=[RegexValidator(
            r"\A[0-9a-f]{64}\Z",
            _("Enter 64 lower-case hexadecimal digits."))])
    created_at = models.DateTimeField(_("Created"), default=current_time)
    last_used_at = models.DateTimeField(_("Last used"), null=True,
                                        blank=True)

    class Meta:
        ordering = ["user", "created_at", "pk"]
        verbose_name = _("access token")
        verbose_name_plural = _("access tokens")

    def __str__(self) -> str:
        return self.name

    @classmethod
    def create_for(cls, user: Any, name: str) -> tuple["AccessToken", str]:
        """Create a token named NAME for the account USER; return the
        saved row and the token, ``osdb_`` followed by 43 URL-safe
        characters from a secure random source. The token is returned
        only here."""
        token = TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_BYTES)
        row = cls.objects.create(user=user, name=name,
                                 digest=token_digest(token))
        return row, token

    @classmethod
    def authenticate(cls, header: str) -> Any:
        """Return the account that the ``Authorization`` header value
        HEADER signs a request with, and record the time as the last
        use of its token; return None, recording nothing, unless HEADER
        is ``Bearer <token>`` with the token of an active account."""
        scheme, _space, given = header.partition(" ")
        if scheme != "Bearer" or not given:
            return None
        found = cls.objects.select_related("user").filter(
            digest=token_digest(given), user__is_active=True).first()
        if found is None:
            return None
        cls.objects.filter(pk=found.pk).update(last_used_at=timezone.now())
        return found.user
