"""The forms of the registry's substances, and the field by which other
forms name a substance."""

from typing import Any

from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from inventory.models import plain
from registry.models import Substance, SubstanceClass
from vocabulary.forms import TermChoiceField, TermsChoiceField
from vocabulary.models import ChemicalClass, Group

# The id of the datalist that offers every substance's key.
DATALIST = "substances"


class SubstanceKeyField(forms.CharField):
    """A substance named by its key, offered through the datalist of
    every substance's key labelled with its name.

    The cleaned value is the substance, or None for an empty optional
    field; a key no substance has is an error at the field.
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("label", _("Substance"))
        kwargs.setdefault("max_length", 100)
        kwargs.setdefault("widget", forms.TextInput(attrs={
            "list": DATALIST, "autocomplete": "off"}))
        super().__init__(**kwargs)

    def prepare_value(self, value: Any) -> Any:
        """Return VALUE as the field shows it: a substance, or the ID of
        one, by its key, and any other value as it is."""
        if isinstance(value, Substance):
            return value.key
        if isinstance(value, int):
            return Substance.objects.filter(pk=value).values_list(
                "key", flat=True).first() or ""
        return super().prepare_value(value)

    def clean(self, value: Any) -> Substance | None:
        """Return the substance whose key VALUE is, stripped; None for an
        empty value of an optional field."""
        key = super().clean(value)
        if not key:
            return None
        found = Substance.objects.filter(key=key.strip()).first()
        if found is None:
            raise forms.ValidationError(
                _("No substance has the key %(key)s."),
                code="invalid_choice", params={"key": key})
        return found


def decimal_field(label: Any, **kwargs: Any) -> forms.DecimalField:
    """Return a decimal field that reads and shows the decimal separator
    of the active language and accepts a decimal point too."""
    return forms.DecimalField(label=label, localize=True,
                              widget=forms.TextInput(
                                  attrs={"inputmode": "decimal"}),
                              **kwargs)


class SubstanceForm(forms.ModelForm):
    """A substance with its chemical classes, at least one of them.

    The key is entered when the substance is created and is fixed
    afterwards: the form of an existing substance has no key. The group
    and the classes are offered in the order of their vocabularies'
    pages. Saving replaces the substance's classes by those checked.
    """

    group = TermChoiceField(queryset=Group.objects.all(), label=_("Group"),
                            empty_label="–")
    chemical_classes = TermsChoiceField(
        queryset=ChemicalClass.objects.all(), label=_("Chemical classes"),
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": _("Check at least one class.")})
    mw = decimal_field(_("Molar mass"), required=False, max_digits=10,
                       decimal_places=3, help_text=_("In g/mol."))

    class Meta:
        model = Substance
        fields = ["key", "name", "name_de", "short_name", "group", "formula",
                  "mw", "smiles", "cas", "note"]
        widgets = {"smiles": forms.TextInput,
                   "note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None:
            del self.fields["key"]
            if self.instance.mw is not None:
                self.initial["mw"] = plain(self.instance.mw)
            self.initial["group"] = self.instance.group.key
            self.initial["chemical_classes"] = list(
                self.instance.chemical_classes.values_list("key",
                                                           flat=True))
        order = ["key", "name", "name_de", "short_name", "group",
                 "chemical_classes", "formula", "mw", "smiles", "cas",
                 "note"]
        self.order_fields(order)

    def save(self, commit: bool = True) -> Substance:
        """Return the substance with the form's values; with COMMIT, save
        it with exactly the classes checked."""
        substance = super().save(commit=False)
        if commit:
            with transaction.atomic():
                substance.save()
                chosen = set(self.cleaned_data["chemical_classes"])
                substance.classes.exclude(
                    chemical_class__in=chosen).delete()
                held = set(substance.chemical_classes.all())
                for term in sorted(chosen - held, key=lambda term: term.key):
                    SubstanceClass.objects.create(substance=substance,
                                                  chemical_class=term)
        return substance
