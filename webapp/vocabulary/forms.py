"""The forms of the vocabularies' terms, and the choice fields that offer
terms in the order of their vocabulary's page."""

from typing import Any

from django import forms
from django.forms.models import ModelChoiceIterator, ModelChoiceIteratorValue

from vocabulary.models import Term, descendants, is_tree, tree_order

# The indent of a term's label per level of depth in a choice.
INDENT = " "


class TreeIterator(ModelChoiceIterator):
    """The choices of a term field: the empty choice, when the field has
    one, then the terms of its queryset in tree order, each label
    indented by the term's depth."""

    def __iter__(self) -> Any:
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        for term, depth in tree_order(self.queryset):
            yield (ModelChoiceIteratorValue(self.field.prepare_value(term),
                                            term),
                   INDENT * depth + self.field.label_from_instance(term))


class TermChoiceField(forms.ModelChoiceField):
    """A choice of one term by its key, offered in tree order by its
    label in the active language."""

    iterator = TreeIterator

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(to_field_name="key", **kwargs)

    def label_from_instance(self, obj: Any) -> str:
        return obj.shown_label


class TermsChoiceField(forms.ModelMultipleChoiceField):
    """A choice of several terms by their keys, offered in tree order by
    their labels in the active language."""

    iterator = TreeIterator

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(to_field_name="key", **kwargs)

    def label_from_instance(self, obj: Any) -> str:
        return obj.shown_label


def term_form(model: type[Term], instance: Term | None = None,
              data: Any = None) -> forms.ModelForm:
    """Return the form of a new term of MODEL, or of INSTANCE, bound to
    DATA when given.

    The key is entered on the new form only and is fixed afterwards. The
    parent of a tree's term is a choice of its vocabulary's terms, the
    term itself and those filed under it left out, or none.
    """
    fields = ["label", "label_de"]
    if instance is None:
        fields.insert(0, "key")
    if is_tree(model):
        fields.append("parent")

    form = forms.modelform_factory(model, fields=fields)(
        data, instance=instance)
    if is_tree(model):
        terms = model.objects.all()
        if instance is not None:
            terms = terms.exclude(pk__in=[
                instance.pk, *(term.pk for term in descendants(instance))])
        parent = form.fields["parent"]
        form.fields["parent"] = TermChoiceField(
            queryset=terms, required=False, empty_label="–",
            label=parent.label, help_text=parent.help_text)
        if instance is not None and instance.parent is not None:
            form.initial["parent"] = instance.parent.key
    return form
