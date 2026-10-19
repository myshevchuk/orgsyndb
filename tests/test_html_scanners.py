"""The HTML scanners that the site-build integration tests rely on must
find what the spec forbids and accept what it allows."""

import unittest

from pipeline_support import css_remote_fetches, html_remote_fetches, scan_page

PAGE = """<html lang="en"><head><meta charset="utf-8"><title>T OSDB-2</title>
</head><body><h1>Aspirin</h1><main data-pagefind-body><h2>Summary</h2>
<p>text<ul><li>item</ul><a href="https://doi.example/x">cite</a></main>
</body></html>"""


class ScannerTests(unittest.TestCase):
    def test_indexed_body_headings_and_outside_text(self) -> None:
        """Scenario: One indexed body per procedure page (scanner)."""
        scan = scan_page(PAGE)
        self.assertEqual(len(scan.bodies), 1)
        self.assertEqual(scan.bodies[0].headings, ["Summary"])
        self.assertIn("OSDB-2", scan.outside_text)
        self.assertIn("Aspirin", scan.outside_text)
        self.assertNotIn("Summary", scan.outside_text)

    def test_page_without_the_attribute_has_no_body(self) -> None:
        """Scenario: One indexed body per procedure page (scanner)."""
        self.assertEqual(scan_page("<main><h1>x</h1></main>").bodies, [])

    def test_remote_fetches_are_found_and_links_are_not(self) -> None:
        """Scenario: Seed build fetches nothing remote (scanner)."""
        html = ('<link rel="stylesheet" href="https://cdn.example/x.css">'
                '<img src="//cdn.example/a.png">'
                '<div style="background:url(http://h/i.png)"></div>'
                '<style>@import "//h/s.css";</style>'
                '<a href="https://doi.example/x">cite</a>'
                '<link rel="stylesheet" href="/css/site.css">')
        self.assertEqual(len(html_remote_fetches(html)), 4)
        self.assertEqual(html_remote_fetches(PAGE), [])
        self.assertNotEqual(css_remote_fetches("a{b:url('https://h/x')}"), [])
        self.assertEqual(css_remote_fetches("a{b:url(/x.png)}"), [])
