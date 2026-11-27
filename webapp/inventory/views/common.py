"""Shared paths, navigation, master-detail, dialog, and URL helpers for
inventory views."""

from collections.abc import Callable, Sequence
from datetime import date
from functools import wraps
from typing import Any, TypeVar
from urllib.parse import urlencode, urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.forms import BaseForm
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import pgettext_lazy
from django.views.decorators.vary import vary_on_headers
from django_htmx.http import HttpResponseClientRedirect, trigger_client_event

from inventory.bookings import Refused
from inventory.forms import show_refusal
from inventory.models import Article, Batch, DeliveryNote, Item, Vessel
from inventory.summaries import natural

T = TypeVar("T")

LIST = "/lab/inventory/end-products/"
INTERMEDIATES = "/lab/inventory/intermediates/"
CHEMICALS = "/lab/inventory/chemicals/"
BATCHES = "/lab/inventory/batches/"
VESSELS = "/lab/inventory/vessels/"
DELIVERIES = "/lab/inventory/deliveries/"
BULK = "/lab/inventory/end-products/bulk/"

VIEW_COOKIE = "item-list-view"
BULK_COOKIE = "bulk-list-view"
NOTE_COOKIE = "delivery-list-view"
INTERMEDIATE_COOKIE = "intermediate-list-view"
CHEMICAL_COOKIE = "chemical-list-view"


def tabs(current: str) -> list[dict[str, Any]]:
    """Return the section tabs of the inventory, marking CURRENT, the
    path of the tab's list; the end products' layers are under
    ``LIST``."""
    return [{"url": url, "label": label, "current": url == current}
            for url, label in ((LIST, _("End products")),
                               (INTERMEDIATES, _("Intermediates")),
                               (CHEMICALS, _("Commercial chemicals")),
                               (BATCHES, _("Batches")),
                               (VESSELS, _("All vessels")))]


def bulk_vessels() -> Any:
    """Return the open vessels of the substances that have an article,
    with their batch, its step's task, the substance and its article
    read."""
    return Vessel.objects.open().filter(
        batch__substance__article__isnull=False
    ).with_substance().select_related("batch__task_step__task")


def layers(current: str) -> list[dict[str, Any]]:
    """Return the layers of the end products, the item list, the bulk
    list and the delivery list, each with its count, marking CURRENT,
    the path of the layer shown."""
    return [{"url": url, "label": label, "count": count,
             "current": url == current}
            for url, label, count in (
                (LIST, pgettext_lazy("layer", "Containers"),
                 Item.objects.count()),
                (BULK, pgettext_lazy("layer", "Bulk"),
                 bulk_vessels().count()),
                (DELIVERIES, pgettext_lazy("layer", "Deliveries"),
                 DeliveryNote.objects.count()))]


def oldest_vessel_order(vessel: Vessel) -> tuple[Any, ...]:
    """Order vessels by their batch's date, oldest first and undated
    vessels last, then by ID."""
    return (vessel.batch.date is None, vessel.batch.date or date.min,
            vessel.pk)


def open_vessels(item: Item | None = None) -> list[Vessel]:
    """Return the open vessels, those holding an amount above zero, of
    ITEM's substance, or of every substance when ITEM is None, by their
    batch's date, oldest first and undated ones last, then by ID, each
    with its batch, substance and the substance's article read."""
    vessels = Vessel.objects.open().with_substance()
    if item is not None:
        vessels = vessels.filter(batch__substance_id=item.article_id)
    return sorted(vessels, key=oldest_vessel_order)


def list_view(request: HttpRequest, cookie: str) -> str:
    """Return the view of a list with two views that the cookie COOKIE
    remembers, ``details`` or else ``table``."""
    return "details" if request.COOKIES.get(cookie) == "details" \
        else "table"


def pick_selected(rows: Sequence[T], wanted: str,
                  key: Callable[[T], Any]) -> tuple[T | None, str]:
    """Select the row in ROWS whose stringified KEY equals WANTED, else
    the first row, else None; return the chosen row and its string key
    (empty when ROWS is empty)."""
    for row in rows:
        row_key = str(key(row))
        if row_key == wanted:
            return row, row_key
    if not rows:
        return None, ""
    return rows[0], str(key(rows[0]))


def htmx_detail_or_redirect(request: HttpRequest, base_url: str,
                            selected: Any, template: str,
                            context_fn: Callable[[], dict[str, Any]],
                            keep_query: bool = False) -> HttpResponse:
    """Render TEMPLATE with CONTEXT_FN() and ``HX-Replace-Url`` for an
    htmx request, or redirect non-htmx requests to BASE_URL with
    ``selected`` set to SELECTED."""
    if not request.htmx:
        if keep_query:
            params = request.GET.copy()
            params["selected"] = str(selected)
            return redirect(f"{base_url}?{params.urlencode()}")
        return redirect(f"{base_url}?{urlencode({'selected': selected})}")
    response = render(request, template, context_fn())
    current = request.htmx.current_url or ""
    if current and url_has_allowed_host_and_scheme(
            current, {request.get_host()}, request.is_secure()):
        params = QueryDict(urlsplit(current).query, mutable=True)
    elif keep_query:
        params = request.GET.copy()
    else:
        params = QueryDict(mutable=True)
    params["selected"] = str(selected)
    response["HX-Replace-Url"] = f"{base_url}?{params.urlencode()}"
    return response


def for_dialog(request: HttpRequest) -> bool:
    """Tell whether REQUEST asks for a form to show in the lab's dialog.

    That is an htmx request that is not htmx's reload of a page from its
    history, which needs the complete page.
    """
    return bool(request.htmx and not request.htmx.history_restore_request)


def sign_in_next(request: HttpRequest) -> str:
    """Return the address to which signing in leads back after REQUEST.

    That is the path and query of the page that made the htmx request
    REQUEST, named by its ``HX-Current-URL`` header, when the page is on
    the host of REQUEST; otherwise the path of REQUEST.
    """
    current = request.htmx.current_url or ""
    if current and url_has_allowed_host_and_scheme(
            current, {request.get_host()}, request.is_secure()):
        parts = urlsplit(current)
        return (parts.path or "/") + (f"?{parts.query}" if parts.query
                                      else "")
    return request.path


def item_form(view: Callable[..., HttpResponse]
              ) -> Callable[..., HttpResponse]:
    """Decorate the item form VIEW to need a signed-in user and to answer
    a request for a dialog (see ``for_dialog``).

    A request without a signed-in user is redirected to the sign-in page
    with ``next`` the path of the request. Where the request is for a
    dialog, the answer is instead ``204 No Content`` with ``HX-Redirect``
    to the sign-in page, whose ``next`` is the address of the page that
    made the request (see ``sign_in_next``), which htmx makes the page
    follow. Every answer varies with the headers ``HX-Request`` and
    ``HX-History-Restore-Request``.
    """
    signed_in = login_required(view)

    @wraps(view)
    @vary_on_headers("HX-Request", "HX-History-Restore-Request")
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any
                ) -> HttpResponse:
        if for_dialog(request) and not request.user.is_authenticated:
            return HttpResponseClientRedirect(
                redirect_to_login(sign_in_next(request)).url, status=204)
        return signed_in(request, *args, **kwargs)

    return wrapper


def render_form(request: HttpRequest, form: BaseForm,
                context: dict[str, Any], dialog: bool = False,
                template: str = "inventory/form.html") -> HttpResponse:
    """Render TEMPLATE with FORM and CONTEXT.

    When DIALOG is true and REQUEST is for a dialog (see ``for_dialog``),
    only the form's partial is rendered, to post from the dialog;
    otherwise the complete page is.
    """
    if dialog and for_dialog(request):
        return render(request, f"{template}#form",
                      {"form": form, "dialog": True, **context})
    return render(request, template, {"form": form, **context})


def form_page(request: HttpRequest, form: BaseForm,
              book: Callable[[dict[str, Any]], HttpResponse],
              context: dict[str, Any],
              template: str = "inventory/form.html",
              dialog: bool = False) -> HttpResponse:
    """Show FORM, or pass the cleaned data of the posted FORM to BOOK and
    return its response.

    A form with errors, and one whose booking is refused, shows again
    with the errors at their fields. CONTEXT goes to TEMPLATE beside the
    form. A true DIALOG lets a request for a dialog show the form alone
    (see ``render_form``).
    """
    if request.method == "POST" and form.is_valid():
        try:
            return book(form.cleaned_data)
        except Refused as refused:
            show_refusal(form, refused, form.cleaned_data.get("rows"))
    return render_form(request, form, context, dialog, template)


def saved(request: HttpRequest, text: str, target: str,
          record: Any = None) -> HttpResponse:
    """Leave the message TEXT and redirect to TARGET.

    When RECORD is given and REQUEST is for a dialog (see ``for_dialog``),
    the answer is instead ``204 No Content`` with an ``HX-Trigger``
    header that fires the event ``lab-saved`` naming RECORD's ID.
    """
    messages.success(request, text)
    if record is not None and for_dialog(request):
        key = "vessel" if isinstance(record, Vessel) else "item"
        return trigger_client_event(
            HttpResponse(status=204), "lab-saved", {key: record.pk})
    return redirect(target)


def item_url(item: Item, action: str = "") -> str:
    """Return the path of ITEM's page, or of its form ACTION."""
    return f"/lab/inventory/items/{item.pk}/" + (f"{action}/" if action
                                                 else "")


def consumption_url(item: Item, year: int, quarter: int) -> str:
    """Return the path of ITEM's consumption form for the QUARTER of
    YEAR."""
    query = urlencode({"year": year, "quarter": quarter})
    return f"{item_url(item, 'consumption')}?{query}"


def batch_url(batch: Batch, action: str = "") -> str:
    """Return the path of BATCH's page, or of its form ACTION."""
    return f"/lab/inventory/batches/{batch.pk}/" + (
        f"{action}/" if action else "")


def vessel_url(vessel: Vessel, action: str = "") -> str:
    """Return the path of VESSEL's page, or of its form ACTION."""
    return f"/lab/inventory/vessels/{vessel.pk}/" + (
        f"{action}/" if action else "")


def note_url(note: DeliveryNote, action: str = "") -> str:
    """Return the path of NOTE's page, or of its form ACTION."""
    return f"/lab/inventory/deliveries/{note.pk}/" + (
        f"{action}/" if action else "")


def categories() -> Any:
    """The categories of the articles, for the category's
    ``datalist``."""
    return Article.objects.exclude(category="").order_by("category") \
        .values_list("category", flat=True).distinct()


def in_use(field: str) -> list[str]:
    """The values of the items' FIELD, ``compartment`` or ``box``, each
    once, in natural order."""
    return sorted(set(Item.objects.exclude(**{field: ""}).values_list(
        field, flat=True)), key=natural)


def locations() -> Any:
    """The locations of the vessels, for the location's ``datalist``."""
    return Vessel.objects.exclude(location="").order_by("location") \
        .values_list("location", flat=True).distinct()
