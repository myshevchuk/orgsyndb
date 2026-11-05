"""The inventory: items counted in containers, their movements, delivery
notes, entered consumption, and bulk lots with their own movements.

Counts and amounts change only through ``inventory.bookings``.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from orgsyndb_web.history import RecordedHistory

END_PRODUCTS = "end-products"
INVENTORIES = [(END_PRODUCTS, _("End products"))]


class Unit(models.TextChoices):
    MG = "mg", "mg"
    UMOL = "umol", "µmol"
    G = "g", "g"
    MMOL = "mmol", "mmol"


# Each unit's factor to its base unit, and that base unit: mg for masses,
# µmol for amounts of substance.
FACTOR = {Unit.MG: 1, Unit.G: 1000, Unit.UMOL: 1, Unit.MMOL: 1000}
BASE_UNIT = {Unit.MG: Unit.MG, Unit.G: Unit.MG, Unit.UMOL: Unit.UMOL,
             Unit.MMOL: Unit.UMOL}
SHOWN_PLACES = Decimal("0.001")


class Level(models.TextChoices):
    OUT = "out", pgettext_lazy("level", "out")
    CRITICAL = "critical", pgettext_lazy("level", "critical")
    LOW = "low", pgettext_lazy("level", "low")
    WATCH = "watch", pgettext_lazy("level", "watch")


# The levels from the most urgent on.
LEVEL_ORDER = {Level.OUT: 0, Level.CRITICAL: 1, Level.LOW: 2, Level.WATCH: 3}


class Item(models.Model):
    """An article in one container size, counted in whole containers.

    The article number, size and unit identify the item within its
    inventory and are fixed once it exists. The quantity changes only by
    movements; the change history covers the other fields.
    """

    inventory = models.CharField(_("Inventory"), max_length=30,
                                 choices=INVENTORIES, default=END_PRODUCTS)
    article_number = models.CharField(_("Article no."), max_length=30)
    name = models.CharField(_("Name"), max_length=200)
    category = models.CharField(_("Category"), max_length=100, blank=True)
    size = models.DecimalField(
        _("Size"), max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))])
    unit = models.CharField(_("Unit"), max_length=4, choices=Unit.choices)
    quantity = models.PositiveIntegerField(_("Stock"), default=0)
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)

    history = RecordedHistory(excluded_fields=["quantity"])

    class Meta:
        ordering = ["article_number", "unit", "size"]
        verbose_name = _("item")
        verbose_name_plural = _("items")
        constraints = [
            models.UniqueConstraint(
                fields=["inventory", "article_number", "size", "unit"],
                name="inventory_item_identity"),
            models.CheckConstraint(condition=Q(size__gt=0),
                                   name="inventory_item_size_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.article_number} {self.container} {self.name}"

    @property
    def container(self) -> str:
        """The size with its unit, without trailing zeros and in the
        number format of the active language, as ``2,5 mg`` in
        German."""
        return f"{number_format(plain(self.size))} {Unit(self.unit).label}"

    def sort_key(self) -> tuple[str, str, Decimal]:
        """The item's place in the item list: by article number, then
        unit, then size."""
        return (self.article_number, self.unit, self.size)


class DeliveryNote(models.Model):
    """A delivery note (``Lieferschein``) and its lines.

    A current note books one delivery movement per line; a historical
    note records deliveries made before they could be booked and changes
    no quantity. A historical note is reversed whole, by its REVERSED
    flag; a current note's lines are reversed through their movements.
    The date, the kind and the lines are fixed once the note exists.
    """

    number = models.CharField(_("Number"), max_length=30, unique=True,
                              null=True, blank=True)
    date = models.DateField(_("Date"))
    recipient = models.CharField(_("Recipient"), max_length=100,
                                 blank=True)
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)
    historical = models.BooleanField(_("Entered later"), default=False)
    reversed = models.BooleanField(_("Reversed"), default=False)
    reversal_note = models.TextField(_("Note of the reversal"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Created by"),
        on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    history = RecordedHistory()

    class Meta:
        ordering = ["-date", "-created_at", "-id"]
        verbose_name = _("delivery note")
        verbose_name_plural = _("delivery notes")

    def __str__(self) -> str:
        return self.number or f"#{self.pk}"


class DeliveryLine(models.Model):
    """A line of a delivery note: COUNT containers of ITEM."""

    delivery_note = models.ForeignKey(
        DeliveryNote, on_delete=models.PROTECT, related_name="lines",
        verbose_name=_("delivery note"))
    item = models.ForeignKey(Item, on_delete=models.PROTECT,
                             related_name="delivery_lines",
                             verbose_name=_("item"))
    count = models.PositiveIntegerField(
        _("Count"), validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["id"]
        verbose_name = _("line")
        verbose_name_plural = _("lines")
        constraints = [
            models.UniqueConstraint(fields=["delivery_note", "item"],
                                    name="inventory_line_item_once"),
        ]

    def __str__(self) -> str:
        return f"{self.count} × {self.item}"


class Lot(models.Model):
    """A bulk lot of an article number, not yet aliquoted.

    The amount is kept in the base unit of the lot's unit, mg or µmol,
    and changes only by the lot's movements. A lot at zero is used up.
    The article number and the unit are fixed once the lot exists.
    """

    inventory = models.CharField(_("Inventory"), max_length=30,
                                 choices=INVENTORIES, default=END_PRODUCTS)
    article_number = models.CharField(_("Article no."), max_length=30)
    unit = models.CharField(_("Unit"), max_length=4, choices=Unit.choices)
    amount = models.DecimalField(_("Amount"), max_digits=18,
                                 decimal_places=6, default=0)
    batch = models.CharField(_("Batch"), max_length=100, blank=True)
    location = models.CharField(_("Location"), max_length=100, blank=True)
    made_on = models.DateField(_("Date"), null=True, blank=True)
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)

    history = RecordedHistory(excluded_fields=["amount"])

    class Meta:
        ordering = ["article_number", "id"]
        verbose_name = _("bulk lot")
        verbose_name_plural = _("bulk lots")
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0),
                                   name="inventory_lot_amount_not_negative"),
        ]

    def __str__(self) -> str:
        label = self.batch or f"#{self.pk}"
        return f"{self.article_number} {label}"

    @property
    def shown_amount(self) -> Decimal:
        """The amount in the lot's unit, rounded half up to three
        places."""
        return shown(self.amount, self.unit)

    @property
    def unit_label(self) -> str:
        """The lot's unit as it is shown, such as ``µmol``."""
        return str(Unit(self.unit).label)


class LotMovement(models.Model):
    """A change of a lot's amount: AMOUNT in the lot's base unit, and
    AMOUNT_AFTER, the lot's amount once it was booked."""

    class Kind(models.TextChoices):
        OPENING = "opening", _("Opening amount")
        FILLING = "filling", _("Filling")
        CORRECTION = "correction", _("Correction")
        REVERSAL = "reversal", _("Reversal")

    lot = models.ForeignKey(Lot, on_delete=models.CASCADE,
                            related_name="movements",
                            verbose_name=_("bulk lot"))
    kind = models.CharField(_("Kind"), max_length=10, choices=Kind.choices)
    amount = models.DecimalField(_("Amount"), max_digits=18,
                                 decimal_places=6)
    amount_after = models.DecimalField(_("Amount after"), max_digits=18,
                                       decimal_places=6)
    date = models.DateField(_("Date"))
    booked_at = models.DateTimeField(_("Booked at"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("User"),
                             on_delete=models.PROTECT, related_name="+")
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("bulk movement")
        verbose_name_plural = _("bulk movements")

    def __str__(self) -> str:
        return f"{self.lot} {self.get_kind_display()}"


class Movement(models.Model):
    """A change of an item's quantity.

    COUNT is the containers moved, or for an opening count or a
    correction the quantity entered; QUANTITY_AFTER is the item's
    quantity once the movement was booked. DATE is the day it took
    place, BOOKED_AT the time it was booked. A delivery names its
    DELIVERY_NOTE; a filling from a lot, and the reversal of one, name
    the lot's movement as BULK_MOVEMENT; a reversal names the movement it
    REVERSES, which is reversed at most once.
    """

    class Kind(models.TextChoices):
        OPENING = "opening", _("Opening count")
        DELIVERY = "delivery", _("Delivery")
        FILLING = "filling", _("Filling")
        CORRECTION = "correction", _("Correction")
        REVERSAL = "reversal", _("Reversal")

    item = models.ForeignKey(Item, on_delete=models.CASCADE,
                             related_name="movements",
                             verbose_name=_("item"))
    kind = models.CharField(_("Kind"), max_length=10, choices=Kind.choices)
    count = models.PositiveIntegerField(_("Count"))
    quantity_after = models.PositiveIntegerField(_("Stock after"))
    date = models.DateField(_("Date"))
    booked_at = models.DateTimeField(_("Booked at"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             verbose_name=_("User"),
                             on_delete=models.PROTECT, related_name="+")
    note = models.TextField(pgettext_lazy("inventory", "Note"), blank=True)
    delivery_note = models.ForeignKey(
        DeliveryNote, verbose_name=_("delivery note"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="movements")
    bulk_movement = models.OneToOneField(
        LotMovement, verbose_name=_("bulk movement"),
        on_delete=models.PROTECT, null=True, blank=True,
        related_name="item_movement")
    reverses = models.OneToOneField(
        "self", verbose_name=_("Reverses"), on_delete=models.PROTECT,
        null=True, blank=True, related_name="reversal")

    class Meta:
        ordering = ["-id"]
        verbose_name = _("movement")
        verbose_name_plural = _("movements")

    def __str__(self) -> str:
        return f"{self.item} {self.get_kind_display()} {self.count}"

    @property
    def reversible(self) -> bool:
        """Whether the movement is a delivery or a filling."""
        return self.kind in (self.Kind.DELIVERY, self.Kind.FILLING)


class EnteredConsumption(models.Model):
    """The consumption of an item in a quarter as entered for the time
    before the application: COUNT containers in quarter QUARTER, 1 to 4,
    of YEAR."""

    item = models.ForeignKey(Item, on_delete=models.CASCADE,
                             related_name="entered_consumption",
                             verbose_name=_("item"))
    year = models.PositiveSmallIntegerField(_("Year"))
    quarter = models.PositiveSmallIntegerField(
        _("Quarter"), validators=[MinValueValidator(1),
                                  MaxValueValidator(4)])
    count = models.PositiveIntegerField(_("Count"))
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Entered by"),
        on_delete=models.PROTECT, related_name="+")
    entered_at = models.DateTimeField(_("Entered at"))

    class Meta:
        ordering = ["year", "quarter"]
        verbose_name = _("entered consumption")
        verbose_name_plural = _("entered consumption")
        constraints = [
            models.UniqueConstraint(fields=["item", "year", "quarter"],
                                    name="inventory_entered_once"),
            models.CheckConstraint(
                condition=Q(quarter__gte=1, quarter__lte=4),
                name="inventory_entered_quarter"),
        ]

    def __str__(self) -> str:
        return f"{self.item} Q{self.quarter} {self.year}: {self.count}"


def plain(value: Decimal) -> Decimal:
    """Return VALUE without trailing zeros and never in exponent form, so
    that ``10.000`` becomes ``10`` and ``2.500`` becomes ``2.5``."""
    if value == value.to_integral_value():
        return value.quantize(Decimal(1))
    return value.normalize()


def shown(amount: Decimal, unit: str) -> Decimal:
    """Return AMOUNT, kept in the base unit of UNIT, in UNIT itself,
    rounded half up to three places and without trailing zeros."""
    return plain((Decimal(amount) / FACTOR[unit]).quantize(
        SHOWN_PLACES, ROUND_HALF_UP))
