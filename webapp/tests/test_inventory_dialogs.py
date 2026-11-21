"""Tests of the item forms as dialogs: the form alone for a request that
htmx makes, the answer to a save, the sign-in redirect, the links that
open a dialog and the parts of the pages that a save refreshes
(web-app: Form dialogs, Permissions; end-product-inventory: Inventory
forms).

The script that opens the dialog and refreshes the page runs in a
browser; these tests cover what the server answers and what the pages
mark for it.
"""

import json
from typing import Any
from urllib.parse import parse_qs, urlsplit

from . import PASSWORD, Element, field_value, page
from .inventory_support import (
    LIST,
    NEW_ITEM,
    NEW_NOTE,
    TODAY,
    FormCase,
    InventoryCase,
    fill_data,
    fresh,
    has_number,
    item_data,
    item_url,
    movement_url,
    note_data,
    num,
    snapshot,
)
from .test_inventory_detail import pane_of

HTMX = {"HTTP_HX_REQUEST": "true"}
RESTORE = {**HTMX, "HTTP_HX_HISTORY_RESTORE_REQUEST": "true"}
LOGIN = "/lab/accounts/login/"
CONTROLS = ("input", "select", "textarea")
FORM_NAMES = ("edit", "fill", "correct", "consumption", "reverse")
DIALOG_LINKS = ("Abfüllen", "Bestand korrigieren", "Verbrauch nachtragen",
                "Bearbeiten")
# Controls that a refresh of the list must not replace: the search the
# user typed in and the view controls.
KEPT = ({"name": "q"}, {"id": "detail-switch"}, {"id": "row-height"},
        {"id": "heat-switch"})


def correction(**over: str) -> dict[str, str]:
    data = {"count": "4", "date": TODAY.isoformat(), "note": "gezählt"}
    data.update(over)
    return data


def current(path: str, host: str = "testserver") -> dict[str, str]:
    """The header with which a page at ``path`` asks for a form."""
    return {**HTMX, "HTTP_HX_CURRENT_URL": f"http://{host}{path}"}


def vary_of(response: Any) -> set[str]:
    return {name.strip().lower()
            for name in response.get("Vary", "").split(",")}


def heading_of(root: Element) -> str | None:
    found = root.find_all(("h1", "h2", "h3"))
    return found[0].text() if found else None


def controls_of(root: Element) -> set[str]:
    return {c.get("name") for c in root.find_all(CONTROLS)
            if c.get("name") and c.get("type") != "hidden"}


def errors_at(root: Element, name: str) -> list[str]:
    """The texts of the error list beside the control ``name``: the one
    in the largest element around it that holds no other control."""
    control = root.find(CONTROLS, name=name)
    assert control is not None, f"the form has no control {name}"

    def alone(node: Element) -> bool:
        return [c for c in node.find_all(CONTROLS)
                if c.get("type") != "hidden"] == [control]

    box = control
    while box.parent is not None and box.parent.tag not in (
            "form", "#root") and alone(box.parent):
        box = box.parent
    return [e.text() for e in box.find_all("ul", cls="errorlist")]


def region(node: Element) -> Element | None:
    """The element that is ``node`` or holds it and is marked
    ``data-refresh``."""
    while node is not None and node.tag != "#root":
        if "data-refresh" in node.attrs:
            return node
        node = node.parent
    return None


def deepest(root: Element, text: str) -> Element:
    """The innermost element whose whole text is ``text``."""
    found = [e for e in root.walk() if e.text() == text]
    assert found, f"no element shows {text!r}"
    return [e for e in found if not any(
        d is not e and d.text() == text for d in e.walk())][0]


def has_ancestor(node: Element, other: Element) -> bool:
    while node is not None:
        if node is other:
            return True
        node = node.parent
    return False


def assert_scripts(case: Any, root: Element) -> None:
    """The page rule of web-app "Scripts": no script text, no attribute
    ``on…``, ``hx-on…`` or ``data-hx-on…``."""
    for script in root.find_all("script"):
        case.assertTrue(script.get("src", "").startswith("/lab/static/"),
                        script.get("src"))
        case.assertEqual(script.text(), "")
    for element in root.walk():
        for name in element.attrs:
            case.assertFalse(
                name.startswith(("on", "hx-on", "data-hx-on")),
                f"<{element.tag}> carries {name}")


class DialogCase(FormCase):
    """A signed-in user, an item of the article ``CH-0012`` with a
    delivery that can be reversed, and its five forms."""

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item("CH-0012", size="10", unit="umol",
                                quantity=5)
        self.delivery = self.deliver_movement(self.target, 2)

    def urls(self) -> dict[str, str]:
        return {"edit": item_url(self.target, "edit"),
                "fill": item_url(self.target, "fill"),
                "correct": item_url(self.target, "correct"),
                "consumption": item_url(self.target, "consumption"),
                "reverse": movement_url(self.delivery)}

    def valid_posts(self) -> dict[str, dict[str, str]]:
        return {"edit": {"category": "", "status": "active",
                         "note": "Neu"},
                "fill": fill_data(count="1"),
                "correct": correction(),
                "consumption": {"year": "2026", "quarter": "1",
                                "count": "3"},
                "reverse": {"note": "falsch gebucht"}}


class TheFormAloneTests(DialogCase):

    def assert_complete_page(self, response: Any, url: str,
                             title: str) -> None:
        self.assertEqual(response.status_code, 200)
        root = page(response)
        self.assertIsNotNone(root.find("html"))
        self.assertIsNotNone(root.find("header", cls="site-header"))
        self.assertEqual(root.find("main").find("h1").text(), title)
        form = root.find("main").find("form")
        self.assertEqual(form.get("method"), "post")
        self.assertEqual([n for n in form.attrs if n.startswith("hx-")],
                         [])

    def test_a_dialog_request_answers_the_form_alone(self) -> None:
        """Scenario: The form alone for a dialog."""
        for name, url in self.urls().items():
            with self.subTest(form=name):
                whole = page(self.client.get(url))
                title = whole.find("main").find("h1").text()
                self.assertTrue(title)
                response = self.client.get(url, **HTMX)
                self.assertEqual(response.status_code, 200)
                root = page(response)
                for tag in ("html", "head", "body", "nav", "main",
                            "script", "dialog"):
                    self.assertIsNone(root.find(tag), tag)
                self.assertIsNone(root.find("header", cls="site-header"))
                self.assertEqual(heading_of(root), title)
                forms = root.find_all("form")
                self.assertEqual(len(forms), 1)
                form = forms[0]
                self.assertEqual(form.get("hx-post"), url)
                self.assertEqual(form.get("action"), url)
                self.assertEqual(form.get("method"), "post")
                self.assertIn("hx-target", form.attrs)
                self.assertIn("hx-disabled-elt", form.attrs)
                self.assertIsNotNone(root.find(
                    "input", name="csrfmiddlewaretoken"))
                self.assertEqual(controls_of(form),
                                 controls_of(whole.find("main")))
                cancel = [a for a in form.find_all("a")
                          if a.text() == "Abbrechen"]
                self.assertEqual([a.get("href") for a in cancel],
                                 [item_url(self.target)])

    def test_a_page_request_answers_the_complete_page(self) -> None:
        """Scenario: The form page posts as a page."""
        for name, url in self.urls().items():
            with self.subTest(form=name):
                response = self.client.get(url)
                title = page(response).find("main").find("h1").text()
                self.assert_complete_page(response, url, title)

    def test_a_history_restore_answers_the_complete_page(self) -> None:
        for name, url in self.urls().items():
            with self.subTest(form=name):
                title = page(self.client.get(url)).find("main").find(
                    "h1").text()
                self.assert_complete_page(
                    self.client.get(url, **RESTORE), url, title)

    def test_the_answers_vary_on_both_headers(self) -> None:
        want = {"hx-request", "hx-history-restore-request"}
        for name, url in self.urls().items():
            answers = {
                "page": self.client.get(url),
                "dialog": self.client.get(url, **HTMX),
                "restore": self.client.get(url, **RESTORE),
                "refused": self.client.post(url, {}, **HTMX)}
            for kind, response in answers.items():
                with self.subTest(form=name, answer=kind):
                    self.assertLessEqual(want, vary_of(response))

    def test_the_form_page_posts_as_a_page(self) -> None:
        """Scenario: The form page posts as a page (the redirect)."""
        done = self.client.post(self.urls()["correct"], correction())
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)

    def test_other_forms_are_unchanged(self) -> None:
        for path in (NEW_ITEM, NEW_NOTE):
            with self.subTest(path=path, method="GET"):
                response = self.client.get(path, **HTMX)
                root = page(response)
                self.assertIsNotNone(root.find("html"))
                form = root.find("main").find("form")
                self.assertNotIn("hx-post", form.attrs)
        for path, data in ((NEW_ITEM, item_data(size="50")),
                           (NEW_NOTE, note_data((self.target, 1)))):
            with self.subTest(path=path, method="POST"):
                done = self.client.post(path, data, **HTMX)
                self.assertEqual(done.status_code, 302)
                self.assertNotIn("HX-Trigger", done)


class ErrorsInTheDialogTests(DialogCase):

    def assert_partial(self, response: Any, url: str) -> Element:
        self.assertEqual(response.status_code, 200)
        root = page(response)
        self.assertIsNone(root.find("html"))
        self.assertIsNone(root.find("header", cls="site-header"))
        self.assertEqual(root.find("form").get("hx-post"), url)
        return root

    def test_an_invalid_correction_shows_the_error_at_the_count(
            self) -> None:
        """Scenario: Errors stay in the dialog."""
        url = self.urls()["correct"]
        before = snapshot()
        count = fresh(self.target).quantity
        done = self.client.post(url, correction(count="x"), **HTMX)
        root = self.assert_partial(done, url)
        self.assertTrue(errors_at(root, "count"))
        self.assertEqual(errors_at(root, "note"), [])
        self.assertEqual(fresh(self.target).quantity, count)
        self.assertEqual(snapshot(), before)

    def test_an_invalid_form_of_each_kind_stays_in_the_dialog(self) -> None:
        bad = {"edit": ("status", {"category": "", "status": "nonsense",
                                   "note": ""}),
               "fill": ("count", fill_data(count="x")),
               "consumption": ("year", {"year": "x", "quarter": "1",
                                        "count": "3"}),
               "reverse": ("note", {"note": ""})}
        before = snapshot()
        for name, (field, data) in bad.items():
            url = self.urls()[name]
            with self.subTest(form=name):
                root = self.assert_partial(
                    self.client.post(url, data, **HTMX), url)
                self.assertTrue(errors_at(root, field))
        self.assertEqual(snapshot(), before)

    def test_a_refused_filling_shows_the_refusal(self) -> None:
        """A filling above the lot's amount is refused by the booking,
        not by the form."""
        lot = self.lot("CH-0012", "mg", "5")
        url = self.urls()["fill"]
        before = snapshot()
        done = self.client.post(url, fill_data(
            count="5", lot=str(lot.pk)), **HTMX)
        root = self.assert_partial(done, url)
        self.assertTrue(errors_at(root, "amount"))
        self.assertEqual(snapshot(), before)
        self.assertNotIn("HX-Trigger", done)

    def test_a_movement_reversed_twice_shows_a_form_error(self) -> None:
        url = self.urls()["reverse"]
        self.client.post(url, {"note": "x"})
        before = snapshot()
        done = self.client.post(url, {"note": "y"}, **HTMX)
        root = self.assert_partial(done, url)
        form_errors = root.find_all("ul", cls="nonfield")
        self.assertEqual(len(form_errors), 1)
        self.assertTrue(form_errors[0].text())
        self.assertEqual(errors_at(root, "note"), [])
        self.assertEqual(snapshot(), before)
        self.assertNotIn("HX-Trigger", done)

    def test_propose_amount_fills_in_the_amount(self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        url = self.urls()["fill"]
        before = snapshot()
        done = self.client.post(url, fill_data(
            count="5", lot=str(lot.pk), propose="1"), **HTMX)
        root = self.assert_partial(done, url)
        self.assertEqual(field_value(root, "amount"), "7,408")
        self.assertEqual(field_value(root, "count"), "5")
        self.assertEqual(field_value(root, "lot"), str(lot.pk))
        self.assertEqual(snapshot(), before)
        self.assertNotIn("HX-Trigger", done)

    def test_propose_amount_without_a_lot_shows_the_error(self) -> None:
        url = self.urls()["fill"]
        before = snapshot()
        done = self.client.post(url, fill_data(
            count="5", propose="1"), **HTMX)
        root = self.assert_partial(done, url)
        self.assertTrue(errors_at(root, "lot"))
        self.assertEqual(snapshot(), before)

    def test_propose_amount_without_a_molar_mass_shows_the_error(
            self) -> None:
        stock = self.item("X-1", size="10", unit="umol", quantity=0)
        lot = self.lot("X-1", "mg", "50")
        url = item_url(stock, "fill")
        before = snapshot()
        done = self.client.post(url, fill_data(
            count="5", lot=str(lot.pk), propose="1"), **HTMX)
        root = self.assert_partial(done, url)
        self.assertTrue(errors_at(root, "amount"))
        self.assertEqual(snapshot(), before)

    def test_propose_amount_on_a_page_answers_the_page(self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        done = self.client.post(self.urls()["fill"], fill_data(
            count="5", lot=str(lot.pk), propose="1"))
        root = page(done)
        self.assertIsNotNone(root.find("html"))
        self.assertNotIn("hx-post", root.find("main").find("form").attrs)
        self.assertEqual(field_value(root, "amount"), "7,408")

    def test_propose_amount_after_a_history_restore_answers_the_page(
            self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        done = self.client.post(self.urls()["fill"], fill_data(
            count="5", lot=str(lot.pk), propose="1"), **RESTORE)
        self.assertIsNotNone(page(done).find("html"))

    def test_the_propose_answer_varies_on_both_headers(self) -> None:
        lot = self.lot("CH-0012", "mg", "50")
        done = self.client.post(self.urls()["fill"], fill_data(
            count="5", lot=str(lot.pk), propose="1"), **HTMX)
        self.assertLessEqual(
            {"hx-request", "hx-history-restore-request"}, vary_of(done))


class SavedInTheDialogTests(DialogCase):

    def test_a_valid_correction_answers_204(self) -> None:
        """Scenario: Saved in a dialog."""
        done = self.client.post(self.urls()["correct"], correction(),
                                **HTMX)
        self.assertEqual(done.status_code, 204)
        self.assertEqual(done.content, b"")
        saved = json.loads(done["HX-Trigger"])
        self.assertIn("lab-saved", saved)
        self.assertEqual(str(saved["lab-saved"]["item"]),
                         str(self.target.pk))
        self.assertEqual(fresh(self.target).quantity, 4)
        self.assertLessEqual(
            {"hx-request", "hx-history-restore-request"}, vary_of(done))

    def test_the_message_shows_on_the_next_page_once(self) -> None:
        done = self.client.post(self.urls()["correct"], correction(),
                                **HTMX)
        self.assertEqual(done.status_code, 204)
        shown = page(self.client.get(LIST)).find("ul", cls="lab-messages")
        self.assertIsNotNone(shown)
        self.assertEqual(
            [li.text() for li in shown.find_all("li")],
            [f"Bestand von {fresh(self.target)} korrigiert."])
        self.assertIsNone(page(self.client.get(LIST)).find(
            "ul", cls="lab-messages"))

    def test_without_the_header_a_save_redirects(self) -> None:
        done = self.client.post(self.urls()["correct"], correction())
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.assertNotIn("HX-Trigger", done)
        self.assertEqual(fresh(self.target).quantity, 4)

    def test_a_history_restore_request_is_redirected(self) -> None:
        done = self.client.post(self.urls()["correct"], correction(),
                                **RESTORE)
        self.assertRedirects(done, item_url(self.target),
                             fetch_redirect_response=False)
        self.assertNotIn("HX-Trigger", done)

    def test_every_item_form_answers_a_save_with_204(self) -> None:
        posts = self.valid_posts()
        for name, url in self.urls().items():
            before = snapshot()
            with self.subTest(form=name):
                done = self.client.post(url, posts[name], **HTMX)
                self.assertEqual(done.status_code, 204)
                saved = json.loads(done["HX-Trigger"])["lab-saved"]
                self.assertEqual(str(saved["item"]), str(self.target.pk))
                self.assertNotEqual(snapshot(), before)

    def test_a_save_in_the_dialog_shows_in_the_list(self) -> None:
        """The list requested again shows the new count and the
        message."""
        other = self.item("CH-0013", size="10", unit="umol", quantity=9)
        done = self.client.post(self.urls()["correct"],
                                correction(count="3"), **HTMX)
        self.assertEqual(done.status_code, 204)
        root = page(self.client.get(f"{LIST}?detail={self.target.pk}"))
        counts = {}
        for row in root.find_all("tr"):
            if row.get("data-item"):
                counts[row.get("data-item")] = num(row.find(
                    cls="col-stock"))
        self.assertEqual(counts[str(self.target.pk)], 3)
        self.assertEqual(counts[str(other.pk)], 9)
        self.assertIsNotNone(root.find("ul", cls="lab-messages"))

    def test_a_save_in_the_dialog_reorders_the_list(self) -> None:
        """The list sorted by stock, requested again after a save that
        fills the item up, shows its row after the other's."""
        other = self.item("CH-0013", size="10", unit="umol", quantity=9)
        self.deliver_movement(other, 2)
        order = f"{LIST}?sort=stock"

        def rows() -> list[str]:
            return [row.get("data-item") for row in
                    page(self.client.get(order)).find_all("tr")
                    if row.get("data-item")]

        self.assertEqual(rows(), [str(self.target.pk), str(other.pk)])
        done = self.client.post(self.urls()["correct"],
                                correction(count="99"), **HTMX)
        self.assertEqual(done.status_code, 204)
        self.assertEqual(rows(), [str(other.pk), str(self.target.pk)])


class SignedOutTests(InventoryCase):

    def setUp(self) -> None:
        super().setUp()
        self.target = self.item("CH-0012", size="10", unit="umol",
                                quantity=5)
        self.delivery = self.deliver_movement(self.target, 2)
        self.forms = {
            item_url(self.target, "edit"): {
                "category": "", "status": "active", "note": "Neu"},
            item_url(self.target, "fill"): fill_data(count="1"),
            item_url(self.target, "correct"): correction(),
            item_url(self.target, "consumption"): {
                "year": "2026", "quarter": "1", "count": "3"},
            movement_url(self.delivery): {"note": "x"}}

    def led_to(self, response: Any) -> str:
        """The ``next`` of the sign-in page that the answer sends the
        page to."""
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        target = urlsplit(response["HX-Redirect"])
        self.assertEqual(target.path, LOGIN)
        query = parse_qs(target.query)
        self.assertEqual(list(query), ["next"])
        self.assertEqual(len(query["next"]), 1)
        return query["next"][0]

    def test_a_page_is_led_to_sign_in_and_back(self) -> None:
        """Scenario: Signed out meanwhile."""
        origin = "/lab/inventory/end-products/?q=CH&detail=3"
        before = snapshot()
        for path, data in self.forms.items():
            headers = current(origin)
            with self.subTest(path=path, method="GET"):
                self.assertEqual(
                    self.led_to(self.client.get(path, **headers)), origin)
            with self.subTest(path=path, method="POST"):
                self.assertEqual(
                    self.led_to(self.client.post(path, data, **headers)),
                    origin)
        self.assertEqual(snapshot(), before)

    def test_signing_in_leads_back_to_the_page(self) -> None:
        origin = "/lab/inventory/end-products/?q=CH&detail=3"
        path = item_url(self.target, "fill")
        led = self.led_to(self.client.get(path, **current(origin)))
        done = self.client.post(LOGIN, {"username": "kl",
                                        "password": PASSWORD,
                                        "next": led})
        self.assertEqual(done.status_code, 302)
        self.assertEqual(done["Location"], origin)

    def test_a_foreign_address_gives_the_forms_path(self) -> None:
        for path, data in self.forms.items():
            for foreign in ("/x", "/lab/inventory/end-products/?q=CH"):
                headers = current(foreign, "evil.example")
                with self.subTest(path=path, current=foreign):
                    self.assertEqual(
                        self.led_to(self.client.get(path, **headers)),
                        path)
                    self.assertEqual(
                        self.led_to(self.client.post(path, data,
                                                     **headers)), path)

    def test_without_an_address_the_next_is_the_forms_path(self) -> None:
        for path in self.forms:
            with self.subTest(path=path):
                self.assertEqual(
                    self.led_to(self.client.get(path, **HTMX)), path)

    def test_without_htmx_the_redirect_is_as_before(self) -> None:
        before = snapshot()
        for path, data in self.forms.items():
            for method, done in (
                    ("GET", self.client.get(path)),
                    ("POST", self.client.post(path, data))):
                with self.subTest(path=path, method=method):
                    self.assertEqual(done.status_code, 302)
                    self.assertEqual(done["Location"],
                                     f"{LOGIN}?next={path}")
        self.assertEqual(snapshot(), before)

    def test_a_history_restore_is_redirected_as_before(self) -> None:
        path = item_url(self.target, "fill")
        done = self.client.get(path, **{
            **RESTORE, "HTTP_HX_CURRENT_URL":
            "http://testserver/lab/inventory/end-products/"})
        self.assertEqual(done.status_code, 302)
        self.assertEqual(done["Location"], f"{LOGIN}?next={path}")

    def test_the_delivery_note_is_unchanged(self) -> None:
        before = snapshot()
        headers = current("/lab/inventory/end-products/?q=CH&detail=3")
        login = f"{LOGIN}?next={NEW_NOTE}"
        for method, done in (
                ("GET", self.client.get(NEW_NOTE, **headers)),
                ("POST", self.client.post(
                    NEW_NOTE, note_data((self.target, 1)), **headers))):
            with self.subTest(method=method):
                self.assertEqual(done.status_code, 302)
                self.assertEqual(done["Location"], login)
                self.assertNotIn("HX-Redirect", done)
        self.assertEqual(snapshot(), before)


class LinksTests(DialogCase):

    def links_in(self, root: Element) -> dict[str, list[Element]]:
        found: dict[str, list[Element]] = {}
        for link in root.find_all("a"):
            found.setdefault(link.text(), []).append(link)
        return found

    def assert_dialog_links(self, scope: Element, item: Any,
                            numbered: bool = True) -> None:
        by_text = self.links_in(scope)
        wanted = {"Abfüllen": item_url(item, "fill"),
                  "Bestand korrigieren": item_url(item, "correct"),
                  "Bearbeiten": item_url(item, "edit")}
        if numbered:
            wanted["Verbrauch nachtragen"] = item_url(item, "consumption")
            self.assertEqual(len(by_text["Abgabe buchen"]), 1)
            self.assertNotIn("data-dialog",
                             by_text["Abgabe buchen"][0].attrs)
        else:
            self.assertNotIn("Abgabe buchen", by_text)
            self.assertNotIn("Verbrauch nachtragen", by_text)
            wanted["Artikelnr. eintragen"] = item_url(item, "edit")
        for text, href in wanted.items():
            with self.subTest(link=text):
                self.assertEqual(len(by_text[text]), 1)
                link = by_text[text][0]
                self.assertIn("data-dialog", link.attrs)
                self.assertEqual(link.get("href"), href)

    def test_links_in_the_details(self) -> None:
        """Scenario: Item forms as dialogs (the list)."""
        root = page(self.client.get(f"{LIST}?detail={self.target.pk}"))
        pane = pane_of(root)
        self.assert_dialog_links(pane, self.target)
        self.assertEqual(
            {a.text() for a in pane.find_all("a")
             if "data-dialog" in a.attrs},
            {*DIALOG_LINKS})

    def test_links_in_the_details_of_an_item_without_a_number(self) -> None:
        bare = self.item(None, "Neuverbindung 9")
        root = page(self.client.get(f"{LIST}?detail={bare.pk}"))
        pane = pane_of(root)
        self.assertEqual(pane.get("data-item"), str(bare.pk))
        self.assert_dialog_links(pane, bare, numbered=False)

    def test_links_on_the_item_page(self) -> None:
        """Scenario: Item forms as dialogs (the page)."""
        from inventory.bookings import fill
        filling = fill(self.kl, self.target, count=1)
        root = page(self.client.get(item_url(self.target)))
        self.assert_dialog_links(root.find("main"), self.target)
        reversals = self.links_in(root)["Stornieren"]
        self.assertEqual(
            sorted(a.get("href") for a in reversals),
            sorted([movement_url(self.delivery), movement_url(filling)]))
        for link in reversals:
            self.assertIn("data-dialog", link.attrs)
        self.assertEqual(
            {a.text() for a in root.find("main").find_all("a")
             if "data-dialog" in a.attrs},
            {*DIALOG_LINKS, "Stornieren"})

    def test_links_on_the_page_of_an_item_without_a_number(self) -> None:
        bare = self.item(None, "Neuverbindung 9")
        root = page(self.client.get(item_url(bare)))
        self.assert_dialog_links(root.find("main"), bare, numbered=False)


class MarkupTests(DialogCase):

    def setUp(self) -> None:
        super().setUp()
        self.other = self.item("CH-0013", size="10", unit="umol",
                               quantity=9, compartment="2", box="7")

    def listing(self) -> Element:
        return page(self.client.get(f"{LIST}?detail={self.target.pk}"))

    def assert_marked(self, root: Element, node: Element) -> Element:
        """``node`` is, or lies in, an element with ``data-refresh`` and
        a unique ``id`` that leaves the search and the view controls
        out."""
        marked = region(node)
        self.assertIsNotNone(marked, f"<{node.tag}> is not refreshed")
        self.assertTrue(marked.get("id"))
        self.assertNotIn(marked.tag, ("main", "body", "html"))
        ids = [e.get("id") for e in root.walk() if e.get("id")]
        self.assertEqual(ids.count(marked.get("id")), 1)
        for kept in KEPT:
            self.assertIsNone(marked.find(attrs=kept), kept)
        return marked

    def test_every_page_has_the_dialog(self) -> None:
        """Scenario: Refreshed parts come from the page (the dialog)."""
        paths = [LIST, item_url(self.target), "/lab/tasks/",
                 self.urls()["fill"], LOGIN]
        for signed_in in (True, False):
            if not signed_in:
                self.client.logout()
            # A form page sends a visitor to sign in (Permissions).
            for path in paths if signed_in else [
                    p for p in paths if p != self.urls()["fill"]]:
                with self.subTest(path=path, signed_in=signed_in):
                    root = page(self.client.get(path))
                    dialogs = root.find_all("dialog")
                    self.assertEqual([d.get("id") for d in dialogs],
                                     ["lab-dialog"])
                    self.assert_empty_dialog(dialogs[0])

    def assert_empty_dialog(self, dialog: Element) -> None:
        self.assertTrue(dialog.find_all("button"), "no close button")
        self.assertEqual(
            dialog.text(skip=lambda node: node.tag == "button"), "")
        self.assertIsNone(dialog.find(("h1", "h2", "h3", "h4")))
        self.assertEqual(dialog.find_all(CONTROLS), [])
        empty = [e for e in dialog.walk()
                 if e.tag not in ("button", "br", "img", "input", "hr")
                 and e.closest("button") is None
                 and not any(isinstance(c, Element) or c.strip()
                             for c in e.children)]
        self.assertTrue(empty, "the dialog has no empty body element")

    def test_the_list_marks_what_a_save_changes(self) -> None:
        """Scenario: Refreshed parts come from the page (the list)."""
        root = self.listing()
        parts = {
            "count": deepest(root, "2 Artikel"),
            "summary": root.find("p", cls="list-summary"),
            "table body": root.find("tbody"),
            "details": pane_of(root)}
        for name in ("container", "compartment", "box"):
            parts[f"{name} choices"] = root.find("select", name=name)
        menu = [a for a in root.find_all("a")
                if a.find("span", cls="swatch")]
        self.assertTrue(menu, "the page has no stock menu")
        for index, entry in enumerate(menu):
            parts[f"stock menu {index}"] = entry
        for name, node in parts.items():
            with self.subTest(part=name):
                self.assertIsNotNone(node)
                self.assert_marked(root, node)

    def test_the_list_parts_are_marked_when_nothing_is_chosen(self) -> None:
        root = page(self.client.get(f"{LIST}?q=no-such-item"))
        for name, node in (("details", pane_of(root)),
                           ("table body", root.find("tbody")),
                           ("summary", root.find("p", cls="list-summary"))):
            with self.subTest(part=name):
                self.assert_marked(root, node)

    def test_the_item_page_marks_what_a_save_changes(self) -> None:
        root = page(self.client.get(item_url(self.target)))
        marked = root.find_all(attrs={"data-refresh": True})
        self.assertEqual(len(marked), 1)
        wrapper = marked[0]
        self.assertTrue(wrapper.get("id"))
        self.assertNotEqual(wrapper.tag, "main")
        ids = [e.get("id") for e in root.walk() if e.get("id")]
        self.assertEqual(ids.count(wrapper.get("id")), 1)
        self.assertTrue(has_ancestor(wrapper, root.find("main")))
        self.assertTrue(has_ancestor(root.find("h1"), wrapper))
        actions = [a for a in root.find("main").find_all("a")
                   if "data-dialog" in a.attrs]
        self.assertTrue(actions)
        for link in actions:
            self.assertTrue(has_ancestor(link, wrapper), link.text())
        for grid in root.find_all("table"):
            self.assertTrue(has_ancestor(grid, wrapper))

    def test_the_marked_parts_follow_a_save(self) -> None:
        """A page requested after a save in a dialog shows the new count
        in the marked table body and in the marked details."""
        done = self.client.post(self.urls()["correct"],
                                correction(count="3"), **HTMX)
        self.assertEqual(done.status_code, 204)
        root = self.listing()
        row = root.find("tr", attrs={"data-item": str(self.target.pk)})
        self.assertIsNotNone(row)
        self.assertEqual(region(row), region(root.find("tbody")))
        self.assertEqual(num(row.find(cls="col-stock")), 3)
        pane = pane_of(root)
        self.assertEqual(pane.get("data-item"), str(self.target.pk))
        self.assertIsNotNone(region(pane))
        self.assertTrue(has_number(pane.find("dl").text(), "3"))


class ScriptsTests(DialogCase):
    """The pages that carry the dialog still pass web-app "Scripts"."""

    def test_the_pages_carry_no_inline_script_or_handler(self) -> None:
        paths = [f"{LIST}?detail={self.target.pk}",
                 item_url(self.target), "/lab/tasks/", *self.urls().values()]
        for path in paths:
            with self.subTest(path=path):
                root = page(self.client.get(path))
                self.assertIsNotNone(root.find("dialog", id="lab-dialog"))
                assert_scripts(self, root)

    def test_the_form_alone_carries_no_script_or_handler(self) -> None:
        for name, url in self.urls().items():
            with self.subTest(form=name):
                root = page(self.client.get(url, **HTMX))
                self.assertEqual(root.find_all("form")[0].get("hx-post"),
                                 url)
                self.assertEqual(root.find_all("script"), [])
                assert_scripts(self, root)

    def test_the_marked_pages_carry_no_handler(self) -> None:
        root = page(self.client.get(item_url(self.target)))
        self.assertTrue(root.find_all(attrs={"data-refresh": True}))
        assert_scripts(self, root)
        root = page(self.client.get(f"{LIST}?detail={self.target.pk}"))
        self.assertTrue(root.find_all(attrs={"data-refresh": True}))
        assert_scripts(self, root)

