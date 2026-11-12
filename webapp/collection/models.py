"""The imported rows: the imports the builder reported, and the
procedures with their authors, scope entries and sequences of the
collection as the accepted imports left them.

Only the manifest view and the demo data command write these rows,
both through ``collection.importing``. An
import never deletes a procedure, scope entry or sequence: one that is
gone from the collection is marked withdrawn. A substance, reaction type
or scope entry that a row names cannot be deleted.
"""

from django.conf import settings
from django.core.validators import (MaxValueValidator, MinValueValidator,
                                    RegexValidator)
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from registry.models import Substance
from vocabulary.models import ReactionType

KEY_LENGTH = 50
RELEASE_LENGTH = 200

commit_rule = RegexValidator(
    r"^[0-9a-f]{40}$", _("Enter 40 lower-case hexadecimal digits."))
digest_rule = RegexValidator(
    r"^[0-9a-f]{64}$", _("Enter 64 lower-case hexadecimal digits."))


class Outcome(models.TextChoices):
    ACCEPTED = "accepted", _("Accepted")
    REFUSED = "refused", _("Refused")


class Trigger(models.TextChoices):
    COMMIT = "commit", _("Commit")
    REGISTRY = "registry", _("Registry")
    TOOLING = "tooling", _("Tooling")
    CATCH_UP = "catch-up", _("Catch-up")


class Language(models.TextChoices):
    DE = "de", "de"
    EN = "en", "en"


class Source(models.TextChoices):
    ORG = "org", "Org"
    MD = "md", "Markdown"


class Role(models.TextChoices):
    SUBSTRATE = "substrate", _("Substrate")
    PRODUCT = "product", _("Product")


def from_one(name: str) -> models.CheckConstraint:
    """Return the constraint, named NAME, that keeps ``position`` at 1
    or above."""
    return models.CheckConstraint(condition=Q(position__gte=1), name=name)


class Import(models.Model):
    """One build the builder reported, accepted or refused.

    An accepted import has the ``release`` the builder staged and the
    site's ``language``, and no ``errors``; a refused one has neither,
    and its errors one per line. ``base`` is the accepted import the
    build was made after, or None.
    """

    build = models.UUIDField(_("Build"), unique=True)
    commit = models.CharField(_("Commit"), max_length=40,
                              validators=[commit_rule])
    committed_at = models.DateTimeField(_("Committed"))
    base = models.ForeignKey("self", verbose_name=_("Base"), null=True,
                             blank=True, on_delete=models.PROTECT,
                             related_name="+")
    snapshot = models.CharField(_("Registry digest"), max_length=64,
                                validators=[digest_rule])
    tooling = models.CharField(_("Tooling"), max_length=40,
                               validators=[commit_rule])
    release = models.CharField(_("Release"), max_length=RELEASE_LENGTH,
                               blank=True)
    language = models.CharField(_("Language"), max_length=2,
                                choices=Language.choices, blank=True)
    outcome = models.CharField(_("Outcome"), max_length=10,
                               choices=Outcome.choices)
    trigger = models.CharField(_("Trigger"), max_length=10,
                               choices=Trigger.choices)
    errors = models.TextField(_("Errors"), blank=True)
    received_at = models.DateTimeField(_("Received"), auto_now_add=True)

    class Meta:
        ordering = ["-received_at", "-pk"]
        verbose_name = _("import")
        verbose_name_plural = _("imports")
        constraints = [
            models.CheckConstraint(
                condition=Q(outcome="accepted", errors="")
                & ~Q(release="") & ~Q(language="")
                | Q(outcome="refused", release="", language="")
                & ~Q(errors=""),
                name="collection_import_outcome"),
        ]

    def __str__(self) -> str:
        return f"{self.commit[:10]} ({self.outcome})"


class Procedure(models.Model):
    """A procedure of the collection, by its ID, as the accepted import
    ``last_import`` created it or last changed it.

    A ``general`` procedure has scope entries a step names by their
    position; a specific one has one entry.
    """

    key = models.CharField(_("ID"), max_length=KEY_LENGTH, unique=True)
    source = models.CharField(_("Source format"), max_length=3,
                              choices=Source.choices)
    title = models.TextField(_("Title"))
    title_de = models.TextField(_("German title"), blank=True)
    reaction_type = models.ForeignKey(
        ReactionType, verbose_name=_("Reaction type"),
        on_delete=models.PROTECT, related_name="procedures")
    general = models.BooleanField(_("General"))
    last_import = models.ForeignKey(
        Import, verbose_name=_("Last import"), on_delete=models.PROTECT,
        related_name="+")
    withdrawn = models.BooleanField(_("Withdrawn"), default=False)

    class Meta:
        ordering = ["key"]
        verbose_name = _("procedure")
        verbose_name_plural = _("procedures")

    def __str__(self) -> str:
        return self.key


class ProcedureAuthor(models.Model):
    """An account credited as an author of a procedure, at its
    ``position`` among the procedure's authors, from 1; each account is
    an author of a procedure once."""

    procedure = models.ForeignKey(Procedure, verbose_name=_("procedure"),
                                  on_delete=models.CASCADE,
                                  related_name="authors")
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("Account"),
                             on_delete=models.PROTECT, related_name="+")
    position = models.PositiveIntegerField(
        _("Position"), validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["procedure__key", "position"]
        verbose_name = _("procedure author")
        verbose_name_plural = _("procedure authors")
        constraints = [
            models.UniqueConstraint(fields=["procedure", "user"],
                                    name="collection_procedureauthor_once"),
            models.UniqueConstraint(
                fields=["procedure", "position"],
                name="collection_procedureauthor_place"),
            from_one("collection_procedureauthor_position"),
        ]

    def __str__(self) -> str:
        return f"{self.procedure.key} {self.position}"


class ScopeEntry(models.Model):
    """An entry of a procedure's scope, identified within the procedure
    by its ``signature`` (``collection.importing.signature``);
    ``position`` is its place in the procedure's file, from 1."""

    procedure = models.ForeignKey(Procedure, verbose_name=_("procedure"),
                                  on_delete=models.CASCADE,
                                  related_name="entries")
    signature = models.TextField(_("Signature"))
    position = models.PositiveIntegerField(
        _("Position"), validators=[MinValueValidator(1)])
    withdrawn = models.BooleanField(_("Withdrawn"), default=False)

    class Meta:
        ordering = ["procedure__key", "position", "pk"]
        verbose_name = _("scope entry")
        verbose_name_plural = _("scope entries")
        constraints = [
            models.UniqueConstraint(fields=["procedure", "signature"],
                                    name="collection_scopeentry_once"),
            from_one("collection_scopeentry_position"),
        ]

    def __str__(self) -> str:
        return f"{self.procedure.key}: {self.signature}"


class EntrySubstance(models.Model):
    """A substance of a scope entry in one ROLE, at its ``position``
    among the entry's substances of that role, from 1; a product may
    have a ``yield_percent``."""

    entry = models.ForeignKey(ScopeEntry, verbose_name=_("scope entry"),
                              on_delete=models.CASCADE,
                              related_name="substances")
    substance = models.ForeignKey(Substance, verbose_name=_("substance"),
                                  on_delete=models.PROTECT,
                                  related_name="+")
    role = models.CharField(_("Role"), max_length=10, choices=Role.choices)
    yield_percent = models.FloatField(
        _("Yield (%)"), null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    position = models.PositiveIntegerField(
        _("Position"), validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["entry", "role", "position"]
        verbose_name = _("substance of a scope entry")
        verbose_name_plural = _("substances of scope entries")
        constraints = [
            models.UniqueConstraint(fields=["entry", "role", "substance"],
                                    name="collection_entrysubstance_once"),
            models.CheckConstraint(
                condition=Q(role="product")
                | Q(role="substrate", yield_percent__isnull=True),
                name="collection_entrysubstance_yield"),
            from_one("collection_entrysubstance_position"),
        ]

    def __str__(self) -> str:
        return f"{self.role} {self.substance_id}"


class Sequence(models.Model):
    """A synthesis sequence of the collection, by its ID, as the
    accepted import ``last_import`` created it or last changed it."""

    key = models.CharField(_("ID"), max_length=KEY_LENGTH, unique=True)
    title = models.TextField(_("Title"))
    title_de = models.TextField(_("German title"), blank=True)
    target = models.ForeignKey(Substance, verbose_name=_("Target"),
                               on_delete=models.PROTECT, related_name="+")
    last_import = models.ForeignKey(
        Import, verbose_name=_("Last import"), on_delete=models.PROTECT,
        related_name="+")
    withdrawn = models.BooleanField(_("Withdrawn"), default=False)

    class Meta:
        ordering = ["key"]
        verbose_name = _("sequence")
        verbose_name_plural = _("sequences")

    def __str__(self) -> str:
        return self.key


class Step(models.Model):
    """A step of a sequence, at its ``position`` from 1, naming the
    scope entry it carries out."""

    sequence = models.ForeignKey(Sequence, verbose_name=_("sequence"),
                                 on_delete=models.CASCADE,
                                 related_name="steps")
    position = models.PositiveIntegerField(
        _("Position"), validators=[MinValueValidator(1)])
    entry = models.ForeignKey(ScopeEntry, verbose_name=_("scope entry"),
                              on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["sequence", "position"]
        verbose_name = _("step")
        verbose_name_plural = _("steps")
        constraints = [
            models.UniqueConstraint(fields=["sequence", "position"],
                                    name="collection_step_once"),
            from_one("collection_step_position"),
        ]

    def __str__(self) -> str:
        return f"{self.sequence.key} {self.position}"


def latest_accepted() -> Import | None:
    """Return the latest accepted import, the accepted import received
    last, or None when none was accepted."""
    return Import.objects.filter(outcome=Outcome.ACCEPTED).order_by(
        "-received_at", "-pk").first()
