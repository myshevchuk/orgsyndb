"""The planning parameters: the assumptions every forecast is made
under."""

from django.core.exceptions import ValidationError
from django.core.validators import (BaseValidator, MaxValueValidator,
                                    MinValueValidator)
from django.db import models
from django.utils.translation import gettext_lazy as _

from orgsyndb_web.history import RecordedHistory
from planning.forecast import z_of


def within(low: float, high: float | None = None) -> list[BaseValidator]:
    """Return the validators of a value from LOW to HIGH, both
    included, or from LOW on without HIGH."""
    found: list[BaseValidator] = [MinValueValidator(low)]
    if high is not None:
        found.append(MaxValueValidator(high))
    return found


class Parameters(models.Model):
    """The planning parameters, one record kept with its history.

    Without a stored record the field defaults apply; see ``current``.
    """

    certainty = models.FloatField(
        _("Certainty"), default=0.95, validators=within(0.5, 0.999),
        help_text=_("The probability with which a stock is to last its "
                    "runway."))
    buffer_days = models.IntegerField(
        _("Buffer in days"), default=28, validators=within(0, 365),
        help_text=_("The time from a synthesis's end until its product "
                    "can be delivered, for QC, filling and the "
                    "unforeseen."))
    default_synthesis_days = models.IntegerField(
        _("Default synthesis time in days"), default=21,
        validators=within(1, 730),
        help_text=_("Counts until an article has three past syntheses."))
    history_quarters = models.IntegerField(
        _("History in quarters"), default=12, validators=within(4, 40))
    min_orders = models.IntegerField(
        _("Minimum orders"), default=6, validators=within(3, 100),
        help_text=_("The orders the order model needs; with fewer, the "
                    "quarterly totals give a rough forecast."))
    high_days = models.IntegerField(
        _("High priority below days"), default=14, validators=within(0))
    medium_days = models.IntegerField(
        _("Medium priority below days"), default=56, validators=within(0))
    target_days = models.IntegerField(
        _("Target coverage in days"), default=365,
        validators=within(30, 1095),
        help_text=_("How long a new synthesis is to last beyond its "
                    "synthesis time and the buffer."))

    history = RecordedHistory()

    class Meta:
        verbose_name = _("planning parameters")
        verbose_name_plural = _("planning parameters")

    def __str__(self) -> str:
        return str(_("Planning parameters"))

    @classmethod
    def current(cls) -> "Parameters":
        """Return the stored record, or an unsaved one holding the
        defaults when none is stored."""
        return cls.objects.order_by("pk").first() or cls()

    @property
    def z(self) -> float:
        """The quantile of the standard normal distribution at the
        certainty."""
        return z_of(self.certainty)

    def clean(self) -> None:
        """Check that the high band lies below the medium band; raise
        ValidationError at ``medium_days`` otherwise."""
        if (self.high_days is not None and self.medium_days is not None
                and self.high_days >= self.medium_days):
            raise ValidationError({"medium_days": _(
                "The medium band must lie above the high band.")})
