"""The forms of the inventory's bookings and records.

The booking forms validate what a person typed; the bookings in
``inventory.bookings`` then decide, and a refusal they raise is shown at
the field it names by ``show_refusal``.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseForm
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from inventory.bookings import Refused
from inventory.figures import to_base
from inventory.models import (FACTOR, Batch, BatchStock, DeliveryNote, Item,
                              Source, Unit, Vessel)
from journal.entries import entry_for, named
from registry.forms import SubstanceKeyField, decimal_field
from tasks.models import TaskStep

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
ARTICLE_NUMBER = forms.TextInput(attrs={"autocomplete": "off"})
CATEGORY = forms.TextInput(attrs={"list": "categories",
                                  "autocomplete": "off"})
COMPARTMENT = forms.TextInput(attrs={"list": "compartments",
                                     "autocomplete": "off"})
BOX = forms.TextInput(attrs={"list": "boxes", "autocomplete": "off"})
STOCKED_ON_HELP = _("The day the item entered the end-product stock; "
                    "left empty, the opening count sets it when it is "
                    "above zero.")
ARTICLE_NUMBER_HELP = _("The number of the article's delivery notes; "
                        "left empty until it is first delivered. Saved "
                        "on the article, for every size of it.")
CATEGORY_HELP = _("Saved on the article, for every size of it.")
NOTE = forms.Textarea(attrs={"rows": 3})
ROWS = 10
UNKNOWN = _("unknown")


def show_refusal(form: BaseForm, refused: Refused,
                 rows: list[int] | None = None) -> None:
    """Add the errors of REFUSED to FORM, each at the field it names.

    For a refusal that concerns a line of a delivery note, ROWS maps the
    line's position to the row of the form that holds it, and the error
    goes to that row's field, such as ``count_3``. An error at a name
    the form lacks goes to the form as a whole.
    """
    if not hasattr(refused, "error_dict"):
        form.add_error(None, refused.messages)
        return
    for name, errors in refused.error_dict.items():
        if refused.line is not None and rows is not None:
            name = f"{name}_{rows[refused.line]}"
        form.add_error(name if name in form.fields else None,
                       [message for error in errors
                        for message in error.messages])


def not_in_future(day: Any) -> None:
    """Refuse a DAY after today."""
    if day and day > timezone.localdate():
        raise forms.ValidationError(_("The date may not lie in the future."))


@dataclass(frozen=True)
class SubstanceGroup:
    """The heading of the batches of one substance in a batch choice:
    the substance's KEY and its LABEL, its name in the active
    language."""

    key: str
    label: str


class BatchChoices(forms.models.ModelChoiceIterator):
    """The choices of a ``BatchField``: the empty choice, then the
    batches grouped by their substance, each group headed by a
    ``SubstanceGroup``, in the order of the substances' keys."""

    def __iter__(self) -> Iterator[Any]:
        if self.field.empty_label is not None:
            yield "", self.field.empty_label
        groups: dict[str, tuple[SubstanceGroup, list[Any]]] = {}
        for batch in self.queryset.select_related("substance").order_by(
                "substance__key", "pk"):
            substance = batch.substance
            group = groups.setdefault(substance.key, (SubstanceGroup(
                substance.key, substance.shown_name), []))
            group[1].append(self.choice(batch))
        for group, options in groups.values():
            yield group, options


class BatchSelect(forms.Select):
    """A drop-down list whose options are grouped by substance: each
    ``optgroup`` carries its substance's key as ``data-substance``,
    which the page's script reads (``lab.js``)."""

    template_name = "inventory/batch_select.html"


class BatchField(forms.ModelChoiceField):
    """A choice among batches, grouped by their substance and shown as
    ``Batch.__str__`` shows them. FOR names the control whose substance
    the batch must belong to, which the page's script reads to offer
    that substance's batches alone; the form checks the match itself."""

    iterator = BatchChoices

    def __init__(self, *, queryset: Any, follows: str, label: Any,
                 required: bool = False, empty_label: Any = "",
                 aria_label: Any = None, **kwargs: Any) -> None:
        attrs = {"data-batch-for": follows}
        if aria_label:
            attrs["aria-label"] = aria_label
        super().__init__(queryset=queryset, required=required, label=label,
                         empty_label=empty_label, to_field_name=None,
                         widget=BatchSelect(attrs=attrs), **kwargs)


class ItemSelect(forms.Select):
    """A drop-down list of items whose options carry their substance's
    key as ``data-substance``."""

    def create_option(self, name: str, value: Any, label: Any,
                      selected: bool, index: int, subindex: int | None = None,
                      attrs: dict[str, Any] | None = None
                      ) -> dict[str, Any]:
        """Return the option as the base class does, with the substance
        of an item's option as ``data-substance``."""
        option = super().create_option(name, value, label, selected, index,
                                       subindex, attrs)
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-substance"] = instance.substance.key
        return option


class ItemForm(forms.ModelForm):
    """A new item with its opening count, of the substance named by its
    key. The article number and the category are the article's: they
    make the substance's article when it has none, and otherwise are
    checked against it and saved on it by the booking. The size, in up
    to three places, must be above zero. The opening count is of the
    BATCH chosen, of a batch of the substance, or of unknown batch when
    none is chosen."""

    substance = SubstanceKeyField()
    article_number = forms.CharField(
        label=_("Article no."), max_length=30, required=False,
        widget=ARTICLE_NUMBER, help_text=ARTICLE_NUMBER_HELP)
    category = forms.CharField(label=_("Category"), max_length=100,
                               required=False, widget=CATEGORY,
                               help_text=CATEGORY_HELP)
    size = decimal_field(_("Size"), max_digits=10, decimal_places=3)
    quantity = forms.IntegerField(label=_("Opening count"), min_value=0)
    batch = BatchField(
        queryset=Batch.objects.all(), follows="substance", label=_("Batch"),
        empty_label=UNKNOWN,
        help_text=_("The batch the opening count is of; left empty, it is "
                    "of unknown batch."))

    class Meta:
        model = Item
        fields = ["size", "unit", "quantity", "stocked_on", "compartment",
                  "box", "note"]
        widgets = {
            "stocked_on": DATE,
            "compartment": COMPARTMENT,
            "box": BOX,
            "note": NOTE,
        }
        help_texts = {"stocked_on": STOCKED_ON_HELP}

    field_order = ["substance", "article_number", "category", "size",
                   "unit", "quantity", "batch", "stocked_on", "compartment",
                   "box", "note"]

    def clean_size(self) -> Decimal:
        """Return the size; refuse one of zero or less."""
        size = self.cleaned_data["size"]
        if size <= 0:
            raise forms.ValidationError(_("The size must be above zero."))
        return size

    def clean(self) -> dict[str, Any]:
        """Refuse a batch of another substance than the one named, at the
        batch."""
        cleaned = super().clean()
        batch, substance = cleaned.get("batch"), cleaned.get("substance")
        if batch is not None and substance is not None \
                and batch.substance_id != substance.pk:
            self.add_error("batch", _("The batch is of another substance."))
        return cleaned

    def validate_unique(self) -> None:
        """Leave the identity of article, size and unit to the booking,
        which refuses it at the size."""


class MetadataForm(forms.ModelForm):
    """A form of the fields of a record that may change, which saves
    those fields alone, so that a count, an amount or a state a booking
    changed after the record was loaded stays as the booking left it."""

    def save(self, commit: bool = True) -> Any:
        """Return the record with the form's values; with COMMIT, save
        the form's fields of it and no other."""
        record = super().save(commit=False)
        if commit:
            record.save(update_fields=self._meta.fields)
        return record


class ItemEditForm(MetadataForm):
    """The fields of an item that may change, its article's category,
    and, while the article has no article number, the article number,
    which the form does not save: ``article_number`` in its cleaned data
    is the number entered or None.

    Saving saves the category on the article, for every size of it,
    when it differs from the article's.
    """

    category = forms.CharField(label=_("Category"), max_length=100,
                               required=False, widget=CATEGORY,
                               help_text=CATEGORY_HELP)

    class Meta:
        model = Item
        fields = ["status", "stocked_on", "compartment", "box", "note"]
        widgets = {
            "stocked_on": DATE,
            "compartment": COMPARTMENT,
            "box": BOX,
            "note": NOTE,
        }
        help_texts = {
            "status": _("A size not needed or being discontinued is "
                        "dormant: planning leaves it out."),
            "stocked_on": _("The day the item entered the end-product "
                            "stock; it is new in that calendar year."),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        article = self.instance.article
        self.initial.setdefault("category", article.category)
        fields = dict(self.fields)
        head = {"category": fields.pop("category")}
        if article.article_number is None:
            head = {"article_number": forms.CharField(
                label=_("Article no."), max_length=30, required=False,
                empty_value=None, widget=ARTICLE_NUMBER,
                help_text=_("Entered once, when the article is first "
                            "delivered; fixed from then on, and saved "
                            "on the article for every size of it.")),
                **head}
        self.fields = {**head, **fields}

    def save(self, commit: bool = True) -> Any:
        """Return the item with the form's values; with COMMIT, save the
        form's fields of it and the category on its article."""
        item = super().save(commit)
        if commit:
            from inventory.bookings import set_category
            set_category(getattr(item, "_history_user", None),
                         item.article, self.cleaned_data["category"])
        return item


class ItemChoiceField(forms.ModelChoiceField):
    """A choice among the items of ``end-products``, each shown as its
    article number, container and name, and where it is kept."""

    def label_from_instance(self, obj: Any) -> str:
        parts = [obj.article_number, obj.container, obj.name, obj.place]
        return " · ".join(part for part in parts if part)


class NoteForm(forms.Form):
    """A delivery note with up to ten lines, each an item, the batch it
    is delivered from and a count; rows left empty are ignored, and a row
    with only some of the three is refused at the field missing.

    A row's batches are those of the substances of the items the form
    offers, and the batch must be one of its item's substance. An item
    may be in several rows, once for each batch.
    """

    number = forms.CharField(label=_("Number"), max_length=30,
                             required=False)
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    recipient = forms.CharField(label=_("Recipient"), max_length=100,
                                required=False)
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           required=False, widget=NOTE)
    historical = forms.BooleanField(
        label=_("entered later – stock unchanged"), required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        items = Item.objects.filter(
            article__article_number__isnull=False).select_related(
                "article__substance")
        batches = Batch.objects.filter(
            substance_id__in=items.values("article_id"))
        for row in range(ROWS):
            self.fields[f"item_{row}"] = ItemChoiceField(
                queryset=items, required=False, label=_("Item"),
                empty_label="", widget=ItemSelect(attrs={
                    "aria-label": _("Item %(row)s") % {"row": row + 1}}))
            self.fields[f"batch_{row}"] = BatchField(
                queryset=batches, follows=f"item_{row}", label=_("Batch"),
                aria_label=_("Batch %(row)s") % {"row": row + 1})
            self.fields[f"count_{row}"] = forms.IntegerField(
                label=_("Count"), required=False, min_value=1,
                widget=forms.NumberInput(attrs={
                    "aria-label": _("Count %(row)s") % {"row": row + 1}}))
        self.fields["date"].initial = timezone.localdate()

    def head(self) -> list[Any]:
        """Return the bound fields of the note itself, without its
        rows."""
        return [self[name] for name in ("number", "date", "recipient",
                                        "note", "historical")]

    def rows(self) -> list[tuple[Any, Any, Any]]:
        """Return the bound fields of each row: its item, its batch and
        its count."""
        return [(self[f"item_{row}"], self[f"batch_{row}"],
                 self[f"count_{row}"]) for row in range(ROWS)]

    def clean_number(self) -> str:
        """Return the number stripped; refuse one another note has."""
        number = self.cleaned_data["number"].strip()
        if number and DeliveryNote.objects.filter(number=number).exists():
            raise forms.ValidationError(
                _("Another delivery note has this number."))
        return number

    def clean(self) -> dict[str, Any]:
        """Collect the rows that hold a line into ``lines``, triples of
        an item, a batch and a count, and ``rows``, the row of each line.

        Refuse a row that lacks its item, its batch or its count, at the
        field missing; a batch of another substance than the item's and
        an item with a batch twice, at the batch; and a note without
        lines.
        """
        cleaned = super().clean()
        lines, rows, seen = [], [], set()
        for row in range(ROWS):
            names = [f"{kind}_{row}" for kind in ("item", "batch", "count")]
            item, batch, count = (cleaned.get(name) for name in names)
            if any(name in self.errors for name in names):
                continue
            if item is None and batch is None and count is None:
                if any(self.data.get(name) for name in names):
                    self.add_error(names[0], _("Choose an item."))
                continue
            if item is None:
                self.add_error(names[0], _("Choose an item."))
                continue
            if count is None:
                self.add_error(names[2], _("Enter a count."))
            if batch is None:
                self.add_error(names[1], _("Choose a batch."))
            elif batch.substance_id != item.article_id:
                self.add_error(names[1],
                               _("The batch is of another substance."))
            elif (item.pk, batch.pk) in seen:
                self.add_error(names[1], _(
                    "The item and batch are already in the note."))
            elif count is not None:
                seen.add((item.pk, batch.pk))
                lines.append((item, batch, count))
                rows.append(row)
        if not lines and not self.errors:
            raise forms.ValidationError(
                _("A delivery note needs at least one line."))
        cleaned["lines"], cleaned["rows"] = lines, rows
        return cleaned


class NoteEditForm(MetadataForm):
    """The fields of a delivery note that may change: its number,
    recipient and note. An empty number is none."""

    class Meta:
        model = DeliveryNote
        fields = ["number", "recipient", "note"]
        widgets = {"note": NOTE}

    def clean_number(self) -> str | None:
        """Return the number stripped, or None for an empty one."""
        return (self.cleaned_data.get("number") or "").strip() or None


class ReversalForm(forms.Form):
    """The note a reversal needs."""

    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           widget=NOTE)


class FillForm(forms.Form):
    """A filling of an item from one of the open vessels of its
    substance. The amount, in the vessel's unit, may be left empty to
    take the proposal."""

    count = forms.IntegerField(label=_("Count"), min_value=1)
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    vessel = forms.ModelChoiceField(queryset=Vessel.objects.none(),
                                    label=_("Vessel"), empty_label="–")
    amount = decimal_field(_("Amount taken"), required=False,
                           help_text=_("In the unit of the vessel; left "
                                       "empty, the proposed amount is "
                                       "taken."))
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           required=False, widget=NOTE)

    def __init__(self, *args: Any, item: Item, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        vessel = self.fields["vessel"]
        vessel.queryset = Vessel.objects.filter(
            batch__substance_id=item.article_id, amount__gt=0
            ).select_related("batch__substance__article").order_by(
                "batch__date", "id")
        vessel.label_from_instance = vessel_label
        self.fields["date"].initial = timezone.localdate()


def vessel_label(vessel: Vessel) -> str:
    """Return VESSEL as the filling form offers it: the vessel, its
    kind, its location where it has one, and the amount it holds,
    joined by `` · ``."""
    parts = [str(vessel), str(vessel.kind_label), vessel.location,
             f"{number_format(vessel.shown_amount)} {vessel.unit_label}"]
    return " · ".join(part for part in parts if part)


class CorrectionForm(forms.Form):
    """The count of one share of an item's containers after counting,
    with a note.

    The share is the one of unknown batch, which the empty choice of
    ``batch`` stands for and which is chosen by default, or one of the
    batches of ITEM's substance. Each choice shows the containers the
    item holds of it; a batch of another substance is refused at the
    batch.
    """

    count = forms.IntegerField(label=_("Count"), min_value=0)
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.none(), required=False, label=_("Batch"))
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           widget=NOTE)

    def __init__(self, *args: Any, item: Item, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        held = {stock.batch_id: stock.quantity
                for stock in BatchStock.objects.filter(item=item)}
        batch = self.fields["batch"]
        batch.queryset = Batch.objects.filter(
            substance_id=item.article_id).select_related("substance")
        batch.empty_label = f"{UNKNOWN} · {held.get(None, 0)}"
        batch.label_from_instance = lambda obj: \
            f"{obj} · {held.get(obj.pk, 0)}"
        self.fields["count"].initial = held.get(None, 0)
        self.fields["date"].initial = timezone.localdate()


class ConsumptionForm(forms.Form):
    """An entered consumption value of a quarter; left empty, it removes
    the quarter's value.

    FIXED, a pair of year and quarter, makes the form one for that
    quarter: its year and quarter are hidden fields, and a bound form
    takes them from FIXED whatever the data holds. STORED is the quarter's
    stored count, which the count starts at, or None.
    """

    year = forms.IntegerField(label=_("Year"), min_value=1, max_value=9999)
    quarter = forms.TypedChoiceField(
        label=_("Quarter"), coerce=int,
        choices=[("", "")] + [(q, f"Q{q}") for q in range(1, 5)])
    count = forms.IntegerField(
        label=_("Count"), min_value=0, required=False,
        help_text=_("Left empty, the quarter's value is removed."))

    def __init__(self, *args: Any, fixed: tuple[int, int] | None = None,
                 stored: int | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["year"].initial = timezone.localdate().year
        if fixed is None:
            return
        pinned = {"year": fixed[0], "quarter": fixed[1]}
        for name, value in pinned.items():
            self.fields[name].widget = forms.HiddenInput()
            self.fields[name].initial = value
        self.fields["count"].initial = stored
        if self.is_bound:
            self.data = self.data.copy()
            for name, value in pinned.items():
                self.data[name] = str(value)


LOCATION = forms.TextInput(attrs={"list": "locations",
                                  "autocomplete": "off"})


class EntryField(forms.CharField):
    """A lab notebook entry written ``<code>/<number>``, such as
    ``AE-2/8``. The cleaned value is the text stripped, empty for none;
    text that names no entry of a notebook the application has is an
    error at the field. Cleaning creates no entry."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("label", _("Lab notebook"))
        kwargs.setdefault("required", False)
        kwargs.setdefault("max_length", 30)
        kwargs.setdefault("widget", forms.TextInput(attrs={
            "autocomplete": "off", "placeholder": "AE-2/8"}))
        kwargs.setdefault("help_text", _(
            "The entry the batch is written down in, as <code>/<number>; "
            "it is created when it is first named."))
        super().__init__(**kwargs)

    def clean(self, value: Any) -> str:
        """Return the entry VALUE names as text; refuse one that
        ``journal.entries.named`` refuses."""
        text = super().clean(value)
        if text:
            try:
                named(text)
            except ValidationError as error:
                raise forms.ValidationError(error.messages) from error
        return text


def number_holder(number: str, own: int | None = None) -> Batch | None:
    """Return the made batch other than the one with ID OWN that has
    NUMBER regardless of case, or None."""
    return Batch.objects.filter(
        source=Source.MADE, number_key=number.casefold()
    ).exclude(pk=own).first() if number else None


class BatchForm(forms.Form):
    """A new batch of a substance named by its key, made in the lab
    unless the source chosen says bought.

    The amount, in the unit chosen, opens the batch's first vessel at
    the location given. For a batch made by the task STEP the form
    holds the step as a hidden field and the step's journal entry, when
    the step names one, in a field that cannot be changed, and the
    amount, its yield, is required.
    """

    substance = SubstanceKeyField()
    source = forms.ChoiceField(label=_("Source"), choices=Source.choices,
                               required=False)
    number = forms.CharField(label=_("Batch"), max_length=30,
                             required=False)
    journal_entry = EntryField()
    date = forms.DateField(label=_("Date"), widget=DATE, required=False,
                           validators=[not_in_future])
    supplier = forms.CharField(label=_("Supplier"), max_length=100,
                               required=False)
    supplier_article_number = forms.CharField(
        label=_("Supplier's article no."), max_length=50, required=False)
    supplier_batch = forms.CharField(label=_("Supplier's batch"),
                                     max_length=50, required=False)
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           required=False, widget=NOTE)
    amount = decimal_field(
        _("Amount"), required=False,
        help_text=_("Opens the batch's first vessel."))
    unit = forms.ChoiceField(label=_("Unit"), choices=Unit.choices,
                             required=False)
    location = forms.CharField(
        label=_("Location"), max_length=100, required=False,
        widget=LOCATION,
        help_text=_("Where the first vessel is stored; left empty for a "
                    "batch made by a step, the amount stays in its "
                    "flask."))

    def __init__(self, *args: Any, step: TaskStep | None = None,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.step = step
        self.fields["date"].initial = timezone.localdate()
        self.fields["unit"].initial = Unit.MG
        if step is None:
            return
        self.fields["step"] = forms.IntegerField(
            widget=forms.HiddenInput, required=False, initial=step.pk)
        self.fields["amount"].help_text = _(
            "The yield. It waits in the batch's flask unless a location "
            "is given.")
        if step.journal_entry_id is not None:
            field = self.fields["journal_entry"]
            field.disabled = True
            field.initial = str(step.journal_entry)
            field.help_text = _("The entry of the step.")

    def clean_source(self) -> str:
        """Return the source chosen, ``made`` when none is."""
        return self.cleaned_data.get("source") or Source.MADE

    def clean(self) -> dict[str, Any]:
        """Refuse an amount without its unit, and for a batch made by a
        step an amount that is missing."""
        cleaned = super().clean()
        amount = cleaned.get("amount")
        if amount is not None and not cleaned.get("unit") \
                and "unit" not in self.errors:
            self.add_error("unit", _("Choose the unit of the amount."))
        if self.step is not None and amount is None \
                and "amount" not in self.errors:
            self.add_error("amount", _("Enter the yield."))
        return cleaned


class BatchEditForm(forms.ModelForm):
    """The fields of a batch that may change: for a made batch its
    number, journal entry and yield, for a bought one the supplier, the
    supplier's article number and the supplier's batch, and for both the
    date and the note.

    The yield is given in YIELD_UNIT; ``save`` stores it in that unit's
    base unit. A number another made batch has regardless of case is
    refused at the number.
    """

    journal_entry = EntryField()
    yield_amount = decimal_field(_("Yield"), required=False, min_value=0)
    yield_unit = forms.ChoiceField(label=_("Unit"), choices=Unit.choices,
                                   required=False)

    class Meta:
        model = Batch
        fields = ["number", "supplier", "supplier_article_number",
                  "supplier_batch", "date", "note"]
        widgets = {"date": DATE, "note": NOTE}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        batch = self.instance
        if batch.source == Source.MADE:
            for name in ("supplier", "supplier_article_number",
                         "supplier_batch"):
                del self.fields[name]
            self.initial["journal_entry"] = str(batch.journal_entry) \
                if batch.journal_entry_id else ""
            self.initial["yield_amount"] = (
                (batch.yield_amount / FACTOR[batch.yield_unit]).normalize()
                if batch.yield_amount is not None else None)
            self.initial["yield_unit"] = batch.yield_unit or Unit.G
        else:
            for name in ("number", "journal_entry", "yield_amount",
                         "yield_unit"):
                del self.fields[name]

    def clean_number(self) -> str:
        """Return the number stripped; refuse one another made batch has
        regardless of case, naming that batch."""
        number = self.cleaned_data["number"].strip()
        holder = number_holder(number, self.instance.pk)
        if holder is not None:
            raise forms.ValidationError(
                _("Batch %(batch)s has this number."),
                params={"batch": holder})
        return number

    def clean(self) -> dict[str, Any]:
        """Set the yield of a made batch from the amount and unit
        entered, none for an empty amount; a submission that names
        neither field leaves the yield as it is. An amount without a
        unit is an error at the unit, and one that is not above zero an
        error at the amount."""
        cleaned = super().clean()
        if self.instance.source != Source.MADE or not (
                {"yield_amount", "yield_unit"} & set(self.data)):
            return cleaned
        amount = cleaned.get("yield_amount")
        unit = cleaned.get("yield_unit")
        if "yield_amount" in self.errors or "yield_unit" in self.errors:
            return cleaned
        if amount is None:
            self.instance.yield_amount, self.instance.yield_unit = None, ""
        elif not unit:
            self.add_error("yield_unit", _("Choose the unit of the yield."))
        elif amount <= 0 or to_base(amount, unit) <= 0:
            self.add_error("yield_amount", _("The yield must be above zero."))
        else:
            self.instance.yield_amount = to_base(amount, unit)
            self.instance.yield_unit = unit
        return cleaned

    def save(self, commit: bool = True) -> Batch:
        """Return the batch with the form's values; with COMMIT, save
        the form's fields of it and no other. The journal entry, given
        as text, is the entry ``journal.entries.entry_for`` returns."""
        batch = super().save(commit=False)
        if commit:
            fields = [name for name in self._meta.fields
                      if name in self.fields]
            if "journal_entry" in self.fields:
                text = self.cleaned_data["journal_entry"]
                batch.journal_entry = entry_for(text) if text else None
                fields.append("journal_entry")
            if batch.source == Source.MADE and (
                    {"yield_amount", "yield_unit"} & set(self.data)):
                fields += ["yield_amount", "yield_unit"]
            batch.save(update_fields=fields)
        return batch


class NewVesselForm(forms.Form):
    """A new stored vessel of a batch: its opening amount in the unit
    chosen, its location and its note."""

    amount = decimal_field(_("Amount"), min_value=0)
    unit = forms.ChoiceField(label=_("Unit"), choices=Unit.choices)
    location = forms.CharField(label=_("Location"), max_length=100,
                               required=False, widget=LOCATION)
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           required=False, widget=NOTE)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["unit"].initial = Unit.MG


class StepField(forms.ModelChoiceField):
    """A choice among the steps of the tasks that are planned or
    running, each shown as its task's number and product and the step's
    label (``TaskStep.label``)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            queryset=TaskStep.objects.filter(
                task__cancelled=False, task__failed=False,
                task__ended__isnull=True).select_related(
                    "task__substance", "entry__procedure").order_by(
                        "task_id", "position"),
            **kwargs)

    def label_from_instance(self, obj: Any) -> str:
        task = obj.task
        return f"{task.number} {task.substance.shown_name} · {obj.label}"


class WithdrawalForm(forms.Form):
    """An amount taken from a vessel into a step of a task that is
    planned or running, in the vessel's unit."""

    step = StepField(label=_("Task step"), empty_label="–")
    amount = decimal_field(_("Amount taken"))
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()


class TransferForm(forms.Form):
    """A transfer of an amount, in the unit of the source vessel, into a
    stored vessel of the same batch chosen in TARGET, or into a new
    vessel at LOCATION. Exactly one of the two is given."""

    amount = decimal_field(_("Amount"))
    target = forms.ModelChoiceField(
        queryset=Vessel.objects.none(), required=False,
        label=_("Target vessel"), empty_label="–")
    location = forms.CharField(
        label=_("Location of a new vessel"), max_length=100,
        required=False, widget=LOCATION)
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           required=False, widget=NOTE)

    def __init__(self, *args: Any, source: Vessel, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        target = self.fields["target"]
        target.queryset = Vessel.objects.filter(
            batch_id=source.batch_id, flask=False).exclude(
                pk=source.pk).select_related("batch").order_by("id")
        target.label_from_instance = vessel_label
        self.fields["date"].initial = timezone.localdate()

    def clean(self) -> dict[str, Any]:
        """Refuse a transfer that names neither a target vessel nor a
        location, and one that names both."""
        cleaned = super().clean()
        if "target" in self.errors or "location" in self.errors:
            return cleaned
        if cleaned.get("target") is None and not cleaned.get("location"):
            self.add_error("target", _(
                "Choose a vessel, or enter the location of a new one."))
        elif cleaned.get("target") is not None and cleaned.get("location"):
            self.add_error("location", _(
                "Leave the location empty when a vessel is chosen."))
        return cleaned


class VesselEditForm(MetadataForm):
    """The fields of a vessel that may change."""

    class Meta:
        model = Vessel
        fields = ["location", "note"]
        widgets = {"location": LOCATION, "note": NOTE}


class VesselCorrectionForm(forms.Form):
    """A vessel's amount after weighing, in its unit, with a note."""

    amount = decimal_field(_("Amount"), min_value=0)
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           widget=NOTE)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()
