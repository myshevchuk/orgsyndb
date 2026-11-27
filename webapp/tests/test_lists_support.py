"""Tests for shared list helpers and django-cotton component integration."""

from pathlib import Path
from tempfile import TemporaryDirectory

from django.template import engines
from django.template.loader import get_template
from django.test import SimpleTestCase

from orgsyndb_web.lists import clean_choice, sort_rows

from . import parse


def _reset_loaders(engine) -> None:
    """Reset every loader cache, including django-cotton's cached dirs."""
    for loader in engine.template_loaders:
        loader.reset()
        for inner in getattr(loader, "loaders", ()):
            inner.reset()
            get_dirs = getattr(inner, "get_dirs", None)
            if hasattr(get_dirs, "cache_clear"):
                get_dirs.cache_clear()


class ListHelpersTests(SimpleTestCase):

    def test_clean_choice_accepts_allowed_and_falls_back(self) -> None:
        allowed = {"active", "ended", "all"}
        self.assertEqual(clean_choice("ended", allowed, "active"), "ended")
        self.assertEqual(clean_choice("unknown", allowed, "active"), "active")
        self.assertEqual(clean_choice("", allowed), "")

    def test_sort_rows_places_missing_values_last_and_is_stable(self) -> None:
        rows = [("a", 2), ("b", None), ("c", 1), ("d", 2), ("e", None)]
        self.assertEqual(
            sort_rows(rows, lambda r: r[1]),
            [("c", 1), ("a", 2), ("d", 2), ("b", None), ("e", None)],
        )
        self.assertEqual(
            sort_rows(rows, lambda r: r[1], descending=True),
            [("a", 2), ("d", 2), ("c", 1), ("b", None), ("e", None)],
        )


class CottonPartialCompatibilityTests(SimpleTestCase):
    """Verify django-cotton components work alongside Django 6.0 template
    partials through the configured template backend."""

    def test_partialdef_inside_split_layout_slot_resolves_by_name(
            self) -> None:
        engine = engines["django"].engine
        with TemporaryDirectory() as tmpdir:
            tpl_path = Path(tmpdir) / "probe_list.html"
            tpl_path.write_text(
                '<c-split-layout view="details" cookie="probe-cookie" '
                'split scroll_id="category-table-scroll">'
                '<table class="item-table"><tbody></tbody></table>'
                '<c-slot name="detail">'
                '{% partialdef detail inline %}'
                '<aside id="item-detail" data-item="{{ key }}">'
                '{{ label }}</aside>'
                '{% endpartialdef %}'
                '</c-slot>'
                '</c-split-layout>',
                encoding="utf-8",
            )
            orig_dirs = list(engine.dirs)
            engine.dirs = [tmpdir, *orig_dirs]
            _reset_loaders(engine)
            try:
                full_tpl = get_template("probe_list.html")
                full_root = parse(
                    full_tpl.render({"key": "k-1", "label": "Demo"}))
                layout = full_root.find("div", cls="item-layout")
                self.assertIsNotNone(layout)
                self.assertIn("item-layout--split", layout.classes)
                self.assertEqual(layout.get("data-view"), "details")
                self.assertEqual(layout.get("data-cookie"), "probe-cookie")
                scroll = full_root.find("div", id="category-table-scroll")
                self.assertIsNotNone(scroll)
                self.assertIn("table-scroll", scroll.classes)
                self.assertIn("table-sticky", scroll.classes)
                self.assertIsNotNone(full_root.find("aside", id="item-detail"))

                part_tpl = get_template("probe_list.html#detail")
                part_root = parse(
                    part_tpl.render({"key": "k-2", "label": "Only detail"}))
                self.assertIsNone(part_root.find("div", cls="item-layout"))
                aside = part_root.find("aside", id="item-detail")
                self.assertIsNotNone(aside)
                self.assertEqual(aside.get("data-item"), "k-2")
                self.assertEqual(aside.text(), "Only detail")
            finally:
                engine.dirs = orig_dirs
                _reset_loaders(engine)

    def test_migrated_list_partials_resolve_through_backend(self) -> None:
        for name in ("inventory/category_list.html#detail",
                     "inventory/bulk_list.html#detail",
                     "inventory/note_list.html#detail",
                     "inventory/item_list.html#detail"):
            with self.subTest(partial=name):
                rendered = get_template(name).render({})
                root = parse(rendered)
                self.assertIsNone(root.find("div", cls="item-layout"))
                self.assertIsNotNone(root.find("aside", id="item-detail"))
