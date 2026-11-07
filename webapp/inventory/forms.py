"""The forms of the inventory's bookings and records.

The booking forms validate what a person typed; the bookings in
``inventory.bookings`` then decide, and a refusal they raise is shown at
the field it names by ``show_refusal``.
"""

from decimal import Decimal
from typing import Any

from django import forms
from django.forms import BaseForm
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from inventory.bookings import Refused
from inventory.models import END_PRODUCTS, DeliveryNote, Item, Lot

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
ARTICLE_NUMBER = forms.TextInput(attrs={"list": "article-numbers",
                                        "autocomplete": "off"})
STOCKED_ON_HELP = _("The day the item entered the end-product stock; "
                    "left empty, the opening count sets it when it is "
                    "above zero.")
ARTICLE_NUMBER_HELP = _("The number of the article's delivery notes; "
                        "left empty until it is first delivered. It "
                        "links the item to the compound of the "
                        "collection with this number.")
NOTE = forms.Textarea(attrs={"rows": 3})
ROWS = 10


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


def decimal_field(label: Any, **kwargs: Any) -> forms.DecimalField:
    """Return a decimal field that reads and shows the decimal separator
    of the active language and accepts a decimal point too."""
    return forms.DecimalField(label=label, localize=True,
                              widget=forms.TextInput(
                                  attrs={"inputmode": "decimal"}),
                              **kwargs)


class ItemForm(forms.ModelForm):
    """A new item with its opening count. The size, in up to three
    places, must be above zero."""

    size = decimal_field(_("Size"), max_digits=10, decimal_places=3)
    quantity = forms.IntegerField(label=_("Opening count"), min_value=0)

    class Meta:
        model = Item
        fields = ["article_number", "name", "category", "size", "unit",
                  "quantity", "stocked_on", "note"]
        widgets = {
            "article_number": ARTICLE_NUMBER,
            "category": forms.TextInput(attrs={"list": "categories",
                                               "autocomplete": "off"}),
            "stocked_on": DATE,
            "note": NOTE,
        }
        help_texts = {"article_number": ARTICLE_NUMBER_HELP,
                      "stocked_on": STOCKED_ON_HELP}

    def clean_size(self) -> Decimal:
        """Return the size; refuse one of zero or less."""
        size = self.cleaned_data["size"]
        if size <= 0:
            raise forms.ValidationError(_("The size must be above zero."))
        return size

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
    """The fields of an item that may change, and, for an item without
    an article number, the article number, which the form does not save:
    ``article_number`` in its cleaned data is the number entered or
    None."""

    class Meta:
        model = Item
        fields = ["name", "category", "status", "stocked_on", "note"]
        widgets = {
            "category": forms.TextInput(attrs={"list": "categories",
                                               "autocomplete": "off"}),
            "stocked_on": DATE,
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
        if self.instance.article_number is None:
            self.fields = {"article_number": forms.CharField(
                label=_("Article no."), max_length=30, required=False,
                empty_value=None, widget=ARTICLE_NUMBER,
                help_text=_("Entered once, when the item is first "
                            "delivered; fixed from then on.")),
                **self.fields}


class ItemChoiceField(forms.ModelChoiceField):
    """A choice among the items of ``end-products``, each shown as its
    article number, container and name."""

    def label_from_instance(self, obj: Any) -> str:
        return f"{obj.article_number} · {obj.container} · {obj.name}"


class NoteForm(forms.Form):
    """A delivery note with up to ten lines, each an item and a count;
    rows left empty are ignored, and a row with only one of the two is
    refused."""

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
        items = Item.objects.filter(inventory=END_PRODUCTS,
                                    article_number__isnull=False)
        for row in range(ROWS):
            self.fields[f"item_{row}"] = ItemChoiceField(
                queryset=items, required=False, label=_("Item"),
                empty_label="", widget=forms.Select(attrs={
                    "aria-label": _("Item %(row)s") % {"row": row + 1}}))
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

    def rows(self) -> list[tuple[Any, Any]]:
        """Return the bound fields of each row: its item and its
        count."""
        return [(self[f"item_{row}"], self[f"count_{row}"])
                for row in range(ROWS)]

    def clean_number(self) -> str:
        """Return the number stripped; refuse one another note has."""
        number = self.cleaned_data["number"].strip()
        if number and DeliveryNote.objects.filter(number=number).exists():
            raise forms.ValidationError(
                _("Another delivery note has this number."))
        return number

    def clean(self) -> dict[str, Any]:
        """Collect the rows that hold a line into ``lines``, pairs of an
        item and a count, and ``rows``, the row of each line; refuse a
        row with only an item or only a count, an item twice and a note
        without lines."""
        cleaned = super().clean()
        lines, rows, seen = [], [], set()
        for row in range(ROWS):
            item = cleaned.get(f"item_{row}")
            count = cleaned.get(f"count_{row}")
            typed = (self.data.get(f"item_{row}"),
                     self.data.get(f"count_{row}"))
            if f"item_{row}" in self.errors or f"count_{row}" in self.errors:
                continue
            if item is None and count is None:
                if typed[0] or typed[1]:
                    self.add_error(f"item_{row}", _("Choose an item."))
                continue
            if item is None:
                self.add_error(f"item_{row}", _("Choose an item."))
            elif count is None:
                self.add_error(f"count_{row}", _("Enter a count."))
            elif item.pk in seen:
                self.add_error(f"item_{row}",
                               _("The item is already in the note."))
            else:
                seen.add(item.pk)
                lines.append((item, count))
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
    """A filling of an item, from one of the open lots of its article or
    from none. The amount, in the lot's unit, may be left empty to take
    the proposal."""

    count = forms.IntegerField(label=_("Count"), min_value=1)
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    lot = forms.ModelChoiceField(queryset=Lot.objects.none(),
                                 label=_("Bulk lot"), required=False,
                                 empty_label="–")
    amount = decimal_field(_("Amount taken"), required=False,
                           help_text=_("In the unit of the lot; left empty, "
                                       "the proposed amount is taken."))
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           required=False, widget=NOTE)

    def __init__(self, *args: Any, item: Item, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        lot = self.fields["lot"]
        lot.queryset = Lot.objects.filter(
            inventory=item.inventory, article_number=item.article_number,
            amount__gt=0).order_by("made_on", "id")
        lot.label_from_instance = lot_label
        self.fields["date"].initial = timezone.localdate()


def lot_label(lot: Lot) -> str:
    """Return LOT as the filling form offers it: its batch, or its
    number, and the amount it holds."""
    return (f"{lot.batch or f'#{lot.pk}'} · "
            f"{number_format(lot.shown_amount)} {lot.unit_label}")


class CorrectionForm(forms.Form):
    """The count of an item's containers after counting, with a note."""

    count = forms.IntegerField(label=_("Count"), min_value=0)
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           widget=NOTE)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()


class ConsumptionForm(forms.Form):
    """An entered consumption value of a quarter; left empty, it removes
    the quarter's value."""

    year = forms.IntegerField(label=_("Year"), min_value=1, max_value=9999)
    quarter = forms.TypedChoiceField(
        label=_("Quarter"), coerce=int,
        choices=[("", "")] + [(q, f"Q{q}") for q in range(1, 5)])
    count = forms.IntegerField(
        label=_("Count"), min_value=0, required=False,
        help_text=_("Left empty, the quarter's value is removed."))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["year"].initial = timezone.localdate().year


class LotForm(forms.ModelForm):
    """A new bulk lot with its opening amount, in the lot's unit."""

    amount = decimal_field(_("Amount"), min_value=0)

    class Meta:
        model = Lot
        fields = ["article_number", "unit", "amount", "batch", "location",
                  "made_on", "note"]
        widgets = {
            "article_number": ARTICLE_NUMBER,
            "location": forms.TextInput(attrs={"list": "locations",
                                               "autocomplete": "off"}),
            "made_on": DATE,
            "note": NOTE,
        }


class LotEditForm(MetadataForm):
    """The fields of a bulk lot that may change."""

    class Meta:
        model = Lot
        fields = ["batch", "location", "made_on", "note"]
        widgets = {
            "location": forms.TextInput(attrs={"list": "locations",
                                               "autocomplete": "off"}),
            "made_on": DATE,
            "note": NOTE,
        }


class LotCorrectionForm(forms.Form):
    """A lot's amount after weighing, in its unit, with a note."""

    amount = decimal_field(_("Amount"), min_value=0)
    date = forms.DateField(label=_("Date"), widget=DATE,
                           validators=[not_in_future])
    note = forms.CharField(label=pgettext_lazy("inventory", "Note"),
                           widget=NOTE)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate()
