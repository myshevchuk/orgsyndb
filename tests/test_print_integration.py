"""PDF build tests (print-layout): WeasyPrint's PDFs of a theme build,
read with poppler. They skip, naming the missing tool, unless WeasyPrint,
pdfinfo and pdftotext exist besides the builder.
"""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import pipeline_support as ps
from pipeline_support import Content, norm_text

A4 = "595.276 x 841.89 pts (A4)"
QUOTED_TITLE = 'Bob\'s "best" </style> ester \\ x'
# The printed texts of each language: the sample banner, the chrome that
# must not print, the two navigation words that share a line only in the
# site header, the page footer, and the headings of the steps and table.
TEXTS = {
    "en": {"banner": "Sample data — quantities not experimentally verified.",
           "chrome": ["Skip to content", "Print / Save as PDF",
                      "No structure image", "OrgSynDB · internal procedures"],
           "navigation": ("Reaction types", "Authors"),
           "page": "Page {} of {}", "procedure": "Procedure",
           "reagents": "Reagents"},
    "de": {"banner": "Beispieldaten – Mengenangaben nicht experimentell "
                     "überprüft.",
           "chrome": ["Zum Inhalt springen", "Drucken / Als PDF speichern",
                      "Keine Strukturformel",
                      "OrgSynDB · interne Vorschriften"],
           "navigation": ("Reaktionstypen", "Autoren"),
           "page": "Seite {} von {}", "procedure": "Durchführung",
           "reagents": "Reagenzien"},
}
FOOTER_LINE = re.compile(r"(Page \d+ of \d+|Seite \d+ von \d+)")
NEGATIVE_CONTROL = ps.THEME_FIXTURES / "clip-negative-control.html"


class PdfCase(ps.ThemeBuildCase):
    COMMAND = "pdf"

    @classmethod
    def require_tools(cls) -> None:
        ps.require_pdf_tools()

    def pdfs(self) -> list[tuple[Path, Content]]:
        """Each PDF of pdf/ with the content file it was made from."""
        by_stem = {item.path.stem: item for item in self.content()}
        directory = self.sandbox.root / "pdf"
        found = sorted(directory.glob("*.pdf"))
        self.assertTrue(found, "pdf/ holds no PDF")
        self.assertEqual(sorted(p.stem for p in found), sorted(by_stem))
        return [(path, by_stem[path.stem]) for path in found]

    def html_of(self, item: Content) -> ps.Page:
        return ps.load_page(self.public, item.page_file(self.public))

    def pdf_of(self, stem: str) -> Path:
        path = self.sandbox.root / "pdf" / f"{stem}.pdf"
        self.assertTrue(path.is_file(), f"pdf/{stem}.pdf does not exist")
        return path


class PdfBuildTests(PdfCase):
    """The shipped procedures and the quoted-title fixture, as PDFs."""

    FIXTURES = ("OSDB-0906-quoted-title.md",)

    def test_every_pdf_is_a4(self) -> None:
        """Scenario: A4 PDFs."""
        for path, _item in self.pdfs():
            with self.subTest(pdf=path.name):
                info = ps.pdf_info(path)
                self.assertEqual(info.page_size, A4)
                self.assertGreaterEqual(info.pages, 1)

    def test_header_and_footer_are_on_every_page(self) -> None:
        """Scenario: Header and footer on every page."""
        for path, item in self.pdfs():
            pages = ps.pdf_page_texts(path)
            self.assertEqual(len(pages), ps.pdf_info(path).pages)
            for number, text in enumerate(pages, 1):
                with self.subTest(pdf=path.name, page=number):
                    self.assertIn(item.id, text)
                    self.assertIn(norm_text(item.title), norm_text(text))
                    lines = [line.strip() for line in text.splitlines()]
                    footer = TEXTS[self.LOCALE]["page"]
                    self.assertIn(footer.format(number, len(pages)), lines)

    def test_title_with_quotes_and_markup_characters(self) -> None:
        """Scenario: Title with quotes and markup characters."""
        path = self.pdf_of("OSDB-0906-quoted-title")
        first = ps.pdf_page_texts(path)[0]
        line = next(ln for ln in first.splitlines() if ln.strip())
        self.assertTrue(line.rstrip().endswith(QUOTED_TITLE), repr(line))
        # The running header carries the ID on the same line, left of the
        # title; the page's own h1 would not.
        self.assertIn("OSDB-0906", line)

    def test_no_chrome_in_the_pdfs(self) -> None:
        """Scenario: No chrome in the PDFs."""
        for path, item in self.pdfs():
            texts = TEXTS[self.LOCALE]
            pages = ps.pdf_page_texts(path)
            for number, text in enumerate(pages, 1):
                with self.subTest(pdf=path.name, page=number):
                    for chrome in texts["chrome"]:
                        self.assertNotIn(chrome, text)
                    first, second = texts["navigation"]
                    for line in text.splitlines():
                        self.assertFalse(first in line and second in line)
            if "sample-data" in item.tags:
                with self.subTest(pdf=path.name, check="banner"):
                    self.assertIn(texts["banner"], norm_text(pages[0]))

    def test_full_url_is_on_the_first_page_by_default(self) -> None:
        """Scenario: Full URL on the first page by default."""
        first = ps.pdf_page_texts(self.pdf_of("OSDB-0002-aspirin"))[0]
        self.assertIn(
            "http://127.0.0.1:8000/procedures/osdb-0002/ · OSDB-0002 · "
            "status draft · last modified 2026-10-19 23:50",
            norm_text(first))

    def test_no_page_ends_on_a_heading(self) -> None:
        """Scenario: No page ends on a heading."""
        for path, item in self.pdfs():
            headings = {h.norm() for h in self.html_of(item).find_all("h2")}
            self.assertTrue(headings, "the page has no h2")
            pages = ps.pdf_page_texts(path)
            for number, text in enumerate(pages[:-1], 1):
                lines = [ln.strip() for ln in text.splitlines()
                         if ln.strip()
                         and not FOOTER_LINE.fullmatch(ln.strip())]
                with self.subTest(pdf=path.name, page=number):
                    self.assertTrue(lines)
                    self.assertNotIn(norm_text(lines[-1]), headings)

    def test_steps_and_rows_stay_on_one_page(self) -> None:
        """Scenario: Steps and rows stay on one page."""
        for path, item in self.pdfs():
            page = self.html_of(item)
            raw = ps.pdf_page_texts(path, "raw")
            texts = TEXTS[self.LOCALE]
            steps = page.following(page.heading(texts["procedure"]), "ol")
            table = page.following(page.heading(texts["reagents"]), "table")
            self.assertIsNotNone(steps, "no list under Procedure")
            self.assertIsNotNone(table, "no table under Reagents")
            texts = ([li.text() for li in steps.find_all("li")]
                     + [tr.text() for tr in table.find_all("tr")])
            with self.subTest(pdf=path.name):
                self.assertEqual(ps.texts_missing_from_pages(texts, raw), [])

    def test_every_word_is_within_the_margins(self) -> None:
        """Scenario: Every word within the margins."""
        for path, _item in self.pdfs():
            with self.subTest(pdf=path.name):
                self.assertEqual(
                    ps.words_outside_margins(ps.pdf_words(path)), [])

    def test_every_table_cell_is_printed(self) -> None:
        """Scenario: Every table cell is printed."""
        for path, item in self.pdfs():
            raw = ps.pdf_page_texts(path, "raw")
            cells = [cell.text for table in self.html_of(item).tables()
                     for row in table.rows for cell in row]
            with self.subTest(pdf=path.name):
                self.assertTrue(cells)
                self.assertEqual(ps.texts_missing_from_pages(cells, raw), [])

    def test_the_long_sample_spans_pages(self) -> None:
        """Scenario: The long sample spans pages."""
        for path, _item in self.pdfs():
            with self.subTest(pdf=path.name):
                pages = ps.pdf_info(path).pages
                self.assertTrue(1 <= pages <= 10, f"{pages} pages")
        self.assertGreaterEqual(
            ps.pdf_info(self.pdf_of("OSDB-0004-4-acetylbiphenyl")).pages, 3)

    def test_the_pdf_run_prints_no_warning(self) -> None:
        """Scenario: Clean pdf run."""
        self.assertEqual(self.result.returncode, 0)
        lines = (self.result.stdout + self.result.stderr).splitlines()
        self.assertEqual([ln for ln in lines if ln.startswith("WARNING:")],
                         [])


class PdfSiteUrlTests(PdfCase):
    ENV = {"HUGO_PARAMS_SITEURL": "https://orgsyndb.example.invalid/"}

    def test_site_url_comes_from_the_environment(self) -> None:
        """Scenario: Site URL from the environment."""
        first = norm_text(
            ps.pdf_page_texts(self.pdf_of("OSDB-0002-aspirin"))[0])
        self.assertIn(
            "https://orgsyndb.example.invalid/procedures/osdb-0002/", first)
        self.assertNotIn("127.0.0.1", first)


class HiddenOverflowTests(unittest.TestCase):
    """Needs WeasyPrint and poppler, but no build."""

    @classmethod
    def setUpClass(cls) -> None:
        ps.require_pdf_tools()

    def test_the_checks_do_not_see_hidden_overflow(self) -> None:
        """Scenario: The checks do not see hidden overflow.

        This records a limit of the margin and text checks: they pass on
        content that CSS clipped. Only the clipping-CSS check rejects the
        fixture. Do not "fix" this test into a failing one; the raster
        review of the page images is what covers clipping.
        """
        self.assertTrue(NEGATIVE_CONTROL.is_file(),
                        "tests/fixtures/theme/clip-negative-control.html")
        with tempfile.TemporaryDirectory(prefix="orgsyndb clip ") as tmp:
            pdf = Path(tmp) / "clip negative control.pdf"
            done = subprocess.run(
                ["weasyprint", "--allowed-protocols", "file",
                 str(NEGATIVE_CONTROL), str(pdf)],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(done.returncode, 0, done.stderr)
            words = ps.pdf_words(pdf)
            raw = ps.pdf_page_texts(pdf, "raw")
        source = NEGATIVE_CONTROL.read_text(encoding="utf-8")
        page = ps.parse_page(source)
        self.assertEqual(ps.words_outside_margins(words), [])
        self.assertEqual(ps.texts_missing_from_pages(
            [p.norm() for p in page.find_all("p")], raw), [])
        self.assertTrue(any("HiddenClippedSentinel" in text for text in raw))
        declarations = [d for style in page.find_all("style")
                        for d in ps.parse_css(style.text())]
        declarations += [d for node in page.nodes if "style" in node.attrs
                         for d in ps.inline_declarations(node.attrs["style"])]
        violations = ps.clipping_violations(declarations)
        self.assertTrue(any("overflow" in v for v in violations), violations)
        self.assertTrue(any("height" in v for v in violations), violations)


if __name__ == "__main__":
    unittest.main()
