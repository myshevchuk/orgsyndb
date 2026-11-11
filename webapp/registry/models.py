"""The registry: the substances the lab's records refer to.

A substance is a compound, or a mixture or solution taken as one. Its
KEY is fixed once it exists; every other field may change. Its chemical
classes are rows of ``SubstanceClass``. A substance that a record refers
to cannot be deleted.
"""

import re
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from orgsyndb_web.history import RecordedHistory
from vocabulary.models import KEY_PATTERN, ChemicalClass, Group, german

CAS_PATTERN = re.compile(r"^\d{2,7}-\d{2}-\d$")

key_rule = RegexValidator(
    KEY_PATTERN, _("Enter lower-case letters and digits, joined by single "
                   "hyphens, such as cinnamic-acid."))


def cas_rule(value: str) -> None:
    """Refuse VALUE unless it is a CAS number of the form ``140-10-3``
    whose last digit is its check digit: the sum of the other digits,
    from the right, each times its position, modulo 10."""
    if not CAS_PATTERN.match(value):
        raise ValidationError(_("Enter a CAS number such as 140-10-3."),
                              code="invalid")
    digits = [int(digit) for digit in value if digit.isdigit()]
    total = sum(position * digit for position, digit
                in enumerate(reversed(digits[:-1]), start=1))
    if total % 10 != digits[-1]:
        raise ValidationError(_("The check digit of the CAS number does "
                                "not match."), code="invalid")


def above_zero(value: Decimal) -> None:
    """Refuse a VALUE of zero or less."""
    if value is not None and value <= 0:
        raise ValidationError(_("The molar mass must be above zero."),
                              code="min_value")


class Substance(models.Model):
    """A substance of the registry: a compound, or a mixture or solution
    taken as one, which articles, lots and tasks refer to."""

    key = models.CharField(_("Key"), max_length=100, unique=True,
                           validators=[key_rule])
    name = models.CharField(_("Name"), max_length=200)
    name_de = models.CharField(_("German name"), max_length=200,
                               blank=True)
    short_name = models.CharField(_("Short name"), max_length=50,
                                  blank=True)
    group = models.ForeignKey(Group, verbose_name=_("Group"),
                              on_delete=models.PROTECT,
                              related_name="substances")
    chemical_classes = models.ManyToManyField(
        ChemicalClass, verbose_name=_("Chemical classes"),
        through="SubstanceClass", related_name="substances")
    formula = models.CharField(_("Formula"), max_length=100, blank=True)
    mw = models.DecimalField(
        _("Molar mass"), max_digits=10, decimal_places=3, null=True,
        blank=True, validators=[above_zero],
        help_text=_("In g/mol."))
    smiles = models.TextField(_("SMILES"), blank=True)
    cas = models.CharField(_("CAS number"), max_length=12, blank=True,
                           validators=[cas_rule])
    note = models.TextField(_("Note"), blank=True)

    history = RecordedHistory()

    class Meta:
        ordering = ["key"]
        verbose_name = _("substance")
        verbose_name_plural = _("substances")
        constraints = [
            models.UniqueConstraint(
                fields=["cas"], condition=~Q(cas=""),
                name="registry_substance_cas_once",
                violation_error_code="unique",
                violation_error_message=_(
                    "Another substance has this CAS number.")),
        ]

    def __str__(self) -> str:
        return self.key

    @property
    def shown_name(self) -> str:
        """The name in the active language: ``name_de`` on a German site
        when the substance has one, else ``name``."""
        return self.name_de if german() and self.name_de else self.name

    @property
    def article_number(self) -> str | None:
        """The number of the substance's article, or None when it has no
        article or its article has no number."""
        try:
            return self.article.article_number
        except ObjectDoesNotExist:
            return None


class SubstanceClass(models.Model):
    """A chemical class of a substance: one row per substance and
    class. Its change history records each class given to or taken from
    a substance, and who did it."""

    substance = models.ForeignKey(Substance, verbose_name=_("substance"),
                                  on_delete=models.CASCADE,
                                  related_name="classes")
    chemical_class = models.ForeignKey(
        ChemicalClass, verbose_name=_("chemical class"),
        on_delete=models.PROTECT, related_name="substance_classes")

    history = RecordedHistory()

    class Meta:
        ordering = ["substance__key", "chemical_class__key"]
        verbose_name = _("chemical class of a substance")
        verbose_name_plural = _("chemical classes of substances")
        constraints = [
            models.UniqueConstraint(fields=["substance", "chemical_class"],
                                    name="registry_substanceclass_once"),
        ]

    def __str__(self) -> str:
        return f"{self.substance.key}: {self.chemical_class.key}"
