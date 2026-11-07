"""The inventory in the admin, for corrections by staff.

Counts and amounts change only by bookings, so the admin shows
movements, the fixed fields and the quantities read-only, saves only
the fields it shows editable, restores no earlier version, adds no
record, and deletes no movement or delivery note. It deletes an item or
a lot only while its one movement is the opening, and an item only
while no delivery note has a line of it.
"""

from typing import Any

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Model, QuerySet
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse
from simple_history.admin import SimpleHistoryAdmin

from inventory import bookings
from inventory.models import (DeliveryLine, DeliveryNote, Item, Lot,
                              LotMovement, Movement)


def deletable(record: Item | Lot) -> bool:
    """Whether RECORD, an item or a lot, has no movement but its opening
    and, for an item, no line of a delivery note."""
    if record.movements.exclude(kind=Movement.Kind.OPENING).exists():
        return False
    return not (isinstance(record, Item) and record.delivery_lines.exists())


class RecordAdmin(SimpleHistoryAdmin):
    """The admin of a record whose counts, amounts and states change
    only by bookings: it shows the record's history but restores no
    version of it, and saves only the fields its form shows."""

    def revert_disabled(self, request: HttpRequest,
                        obj: Any = None) -> bool:
        return True

    def history_form_view(self, request: HttpRequest, object_id: str,
                          version_id: str,
                          extra_context: dict[str, Any] | None = None
                          ) -> HttpResponse:
        """Show an earlier version of the record; refuse a POST, which
        would restore it."""
        if request.method == "POST":
            raise PermissionDenied
        return super().history_form_view(request, object_id, version_id,
                                         extra_context)

    def save_model(self, request: HttpRequest, obj: Any, form: ModelForm,
                   change: bool) -> None:
        """Save the fields of FORM of OBJ, by the signed-in user."""
        obj._history_user = request.user
        obj.save(update_fields=list(form.fields))


class OpeningOnlyAdmin(RecordAdmin):
    """The admin of a record that may be deleted only with its opening
    movement as its one movement."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest,
                              obj: Any = None) -> bool:
        """Refuse to delete OBJ once it has a booking beyond its
        opening."""
        if obj is not None and not deletable(obj):
            return False
        return super().has_delete_permission(request, obj)

    def get_deleted_objects(self, objs: Any, request: HttpRequest
                            ) -> tuple[Any, ...]:
        """Return what deleting OBJS deletes, as the admin does, with the
        opening movements deleted alongside, and every record of OBJS
        that has a booking beyond its opening named as protected."""
        deleted, counts, needed, protected = super().get_deleted_objects(
            objs, request)
        movement = self.model._meta.get_field("movements").related_model
        needed = {name for name in needed
                  if str(name) != str(movement._meta.verbose_name)}
        blocked = [str(record) for record in objs if not deletable(record)]
        return deleted, counts, needed, [*protected, *blocked]

    def delete_model(self, request: HttpRequest, obj: Any) -> None:
        """Delete OBJ; refuse when it has a booking beyond its opening.

        The record is locked and checked in the transaction that deletes
        it, so a booking made after the page was shown stops the
        deletion."""
        self.delete_queryset(request, self.model.objects.filter(pk=obj.pk))

    def delete_queryset(self, request: HttpRequest,
                        queryset: QuerySet) -> None:
        """Delete the records of QUERYSET; refuse, deleting none, when
        one has a booking beyond its opening."""
        with transaction.atomic():
            records = list(queryset.select_for_update().order_by("pk"))
            if not all(deletable(record) for record in records):
                raise PermissionDenied
            super().delete_queryset(
                request, self.model.objects.filter(
                    pk__in=[record.pk for record in records]))


@admin.register(Item)
class ItemAdmin(OpeningOnlyAdmin):
    """The items, whose article number is editable only while an item
    has none and is then given by ``bookings.assign_article_number``,
    never by the form's own save."""

    list_display = ("article_number", "name", "category", "size", "unit",
                    "quantity")
    list_filter = ("category",)
    search_fields = ("article_number", "name")
    readonly_fields = ("inventory", "size", "unit", "quantity")

    def get_form(self, request: HttpRequest, obj: Any = None,
                 change: bool = False, **kwargs: Any) -> type[ModelForm]:
        """Return the change form, which refuses an article number
        another item of the inventory has with the item's size and
        unit, as ``bookings.assign_article_number`` does."""
        base = super().get_form(request, obj, change, **kwargs)

        class ItemForm(base):  # type: ignore[valid-type, misc]
            def clean_article_number(self) -> str | None:
                number = (self.cleaned_data.get("article_number")
                          or "").strip() or None
                if number and bookings.number_taken(self.instance, number):
                    raise ValidationError(str(bookings.TAKEN))
                return number

        return ItemForm

    def get_readonly_fields(self, request: HttpRequest,
                            obj: Any = None) -> tuple[str, ...]:
        fixed = tuple(super().get_readonly_fields(request, obj))
        if obj is None or obj.article_number is not None:
            return ("inventory", "article_number", *fixed[1:])
        return fixed

    def save_model(self, request: HttpRequest, obj: Any, form: ModelForm,
                   change: bool) -> None:
        """Save the fields of FORM of OBJ but the article number, by the
        signed-in user, and give OBJ the article number entered through
        the booking, which refuses it once the item has one."""
        number = form.cleaned_data.get("article_number") \
            if "article_number" in form.fields else None
        with transaction.atomic():
            if number:
                try:
                    bookings.assign_article_number(request.user, obj,
                                                   number)
                except bookings.Refused as refused:
                    # Given by another user since the form was checked:
                    # nothing of this submission is saved.
                    self.message_user(request, " ".join(refused.messages),
                                      messages.ERROR)
                    return
            obj.article_number = Item.objects.filter(pk=obj.pk) \
                .values_list("article_number", flat=True).get()
            obj._history_user = request.user
            obj.save(update_fields=[name for name in form.fields
                                    if name != "article_number"])


@admin.register(Lot)
class LotAdmin(OpeningOnlyAdmin):
    list_display = ("article_number", "batch", "unit", "amount", "location",
                    "made_on")
    search_fields = ("article_number", "batch")
    readonly_fields = ("inventory", "article_number", "unit", "amount")


class DeliveryLineInline(admin.TabularInline):
    model = DeliveryLine
    fields = ("item", "count")
    readonly_fields = ("item", "count")
    extra = 0
    can_delete = False

    def has_add_permission(self, request: HttpRequest,
                           obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest,
                              obj: Any = None) -> bool:
        return False


@admin.register(DeliveryNote)
class DeliveryNoteAdmin(RecordAdmin):
    list_display = ("__str__", "date", "recipient", "historical",
                    "reversed", "created_by")
    list_filter = ("historical", "reversed")
    search_fields = ("number", "recipient", "lines__item__article_number",
                     "lines__item__name")
    readonly_fields = ("date", "historical", "reversed", "reversal_note",
                       "created_by", "created_at")
    inlines = [DeliveryLineInline]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest,
                              obj: Any = None) -> bool:
        return False


class ReadOnlyAdmin(admin.ModelAdmin):
    """The admin of records that are shown and never changed."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest,
                              obj: Model | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest,
                              obj: Model | None = None) -> bool:
        return False


@admin.register(Movement)
class MovementAdmin(ReadOnlyAdmin):
    list_display = ("item", "kind", "count", "quantity_after", "date",
                    "booked_at", "user", "delivery_note")
    list_filter = ("kind",)
    list_select_related = ("item", "user", "delivery_note")
    search_fields = ("item__article_number", "item__name")


@admin.register(LotMovement)
class LotMovementAdmin(ReadOnlyAdmin):
    list_display = ("lot", "kind", "amount", "amount_after", "date",
                    "booked_at", "user")
    list_filter = ("kind",)
    list_select_related = ("lot", "user")
    search_fields = ("lot__article_number", "lot__batch")
