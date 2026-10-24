"""Static checks of the theme sources (site-theme, print-layout,
site-search). They need no build and never skip.
"""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import pipeline_support as ps
from pipeline_support import DEMO, REPO, Declaration

CSS_DIR = REPO / "site" / "assets" / "css"
SOURCES = ("tokens.css", "base.css", "screen.css", "print.css")
PRINT_SOURCES = ("tokens.css", "base.css", "print.css")
SVG_DIR = DEMO / "static" / "structures"
SVG_NS = "{http://www.w3.org/2000/svg}"
DARK = "@media(prefers-color-scheme:dark)"

TOKENS = ["--bg", "--fg", "--muted", "--border", "--surface", "--link",
          "--focus", "--banner-bg", "--banner-fg", "--draft-bg",
          "--draft-fg", "--checked-bg", "--checked-fg", "--retired-bg",
          "--retired-fg"]
TEXT_PAIRS = [("--fg", "--bg"), ("--muted", "--bg"), ("--link", "--bg"),
              ("--fg", "--surface"), ("--muted", "--surface"),
              ("--link", "--surface"), ("--banner-fg", "--banner-bg"),
              ("--draft-fg", "--draft-bg"),
              ("--checked-fg", "--checked-bg"),
              ("--retired-fg", "--retired-bg")]
PAGEFIND_VARIABLES = ["--pagefind-ui-primary", "--pagefind-ui-text",
                      "--pagefind-ui-background", "--pagefind-ui-border",
                      "--pagefind-ui-tag", "--pagefind-ui-font"]


def css(name: str) -> list[Declaration]:
    return ps.read_css(CSS_DIR / name)


def css_text(name: str) -> str:
    path = CSS_DIR / name
    assert path.is_file(), f"site/assets/css/{name} does not exist"
    return path.read_text(encoding="utf-8")


def custom_properties(declarations: list[Declaration],
                      context: tuple[str, ...]) -> dict[str, str]:
    """The ``:root`` custom properties declared in one at-rule context."""
    found = {}
    for decl in declarations:
        if decl.selector == ":root" and decl.prop.startswith("--") and (
                tuple(c.replace(" ", "") for c in decl.context) == context):
            found[decl.prop] = ps.plain_value(decl.value)
    return found


class DarkModeOnScreenTests(unittest.TestCase):
    def test_dark_scheme_and_forbidden_properties(self) -> None:
        """Scenario: Dark mode only on screen."""
        texts = {name: css_text(name) for name in SOURCES}
        dark = re.compile(r"prefers-color-scheme\s*:\s*dark")
        self.assertRegex(texts["screen.css"], dark)
        for name in ("tokens.css", "base.css", "print.css"):
            with self.subTest(file=name):
                self.assertNotIn("prefers-color-scheme", texts[name])
        for name in SOURCES:
            for decl in css(name):
                with self.subTest(file=name, selector=decl.selector):
                    self.assertNotIn(decl.prop, ("color-scheme",
                                                 "clip-path"))


class ContrastTests(unittest.TestCase):
    def sets(self) -> dict[str, dict[str, str]]:
        return {"light": custom_properties(css("tokens.css"), ()),
                "dark": custom_properties(css("screen.css"), (DARK,))}

    def test_every_pair_meets_its_threshold_in_both_schemes(self) -> None:
        """Scenario: Contrast in both schemes."""
        for scheme, tokens in self.sets().items():
            missing = [name for name in TOKENS if name not in tokens]
            self.assertEqual(missing, [], f"{scheme} set lacks tokens")
            for name in TOKENS:
                with self.subTest(scheme=scheme, token=name):
                    self.assertRegex(tokens[name], r"^#[0-9a-f]{6}$")
            for fg, bg in TEXT_PAIRS:
                with self.subTest(scheme=scheme, pair=f"{fg}/{bg}"):
                    ratio = ps.contrast_ratio(tokens[fg], tokens[bg])
                    self.assertGreaterEqual(ratio, 4.5, f"{ratio:.2f}")
            with self.subTest(scheme=scheme, pair="--focus/--bg"):
                ratio = ps.contrast_ratio(tokens["--focus"], tokens["--bg"])
                self.assertGreaterEqual(ratio, 3.0, f"{ratio:.2f}")

    def test_screen_stylesheet_sets_the_pagefind_variables(self) -> None:
        """Scenario: Contrast in both schemes (Pagefind variables)."""
        declared = {d.prop for d in css("screen.css")}
        for name in PAGEFIND_VARIABLES:
            with self.subTest(variable=name):
                self.assertIn(name, declared)


def narrow_value(declarations: list[Declaration], selector: str,
                 prop: str, width_rem: float) -> str | None:
    """The value a window ``width_rem`` wide gets from unconditional and
    ``max-width`` rules, the last matching declaration winning."""
    max_width = re.compile(r"@media\s*\(\s*max-width\s*:\s*([\d.]+)rem\s*\)")
    found = None
    for decl in declarations:
        if decl.prop != prop or selector not in ps.selectors_of(decl):
            continue
        limits = [max_width.fullmatch(c.strip()) for c in decl.context]
        if all(m and float(m.group(1)) >= width_rem for m in limits):
            found = ps.plain_value(decl.value)
    return found


class NarrowWindowTests(unittest.TestCase):
    def test_columns_stack_at_500_pixels(self) -> None:
        """Scenario: Narrow windows stack the columns."""
        declarations = css("screen.css")
        width = 500 / 16
        for selector in (".home-layout", ".home-browse"):
            with self.subTest(selector=selector):
                self.assertEqual(
                    narrow_value(declarations, selector,
                                 "grid-template-columns", width),
                    "minmax(0, 1fr)")
        self.assertEqual(
            narrow_value(declarations, ".procedure", "display", width),
            "block")


class ContrastFunctionTests(unittest.TestCase):
    """The helpers must reproduce known WCAG values, or the test above
    would hold nothing."""

    def test_known_ratios(self) -> None:
        """Scenario: Contrast in both schemes (checker)."""
        self.assertAlmostEqual(
            ps.contrast_ratio("#000000", "#ffffff"), 21.0, places=2)
        self.assertAlmostEqual(
            ps.contrast_ratio("#1a1a1a", "#ffffff"), 17.40, places=2)
        self.assertAlmostEqual(
            ps.contrast_ratio("#777777", "#ffffff"), 4.48, places=2)


class StructureImageTests(unittest.TestCase):
    def check(self, path: Path) -> list[str]:
        """Return the safe-SVG rules ``path`` breaks."""
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            return [f"does not parse as XML: {exc}"]
        problems = []
        if root.tag != f"{SVG_NS}svg":
            return [f"root element is {root.tag}"]
        if "viewBox" not in root.attrib:
            problems.append("no viewBox")
        if root.get("role") != "img":
            problems.append("root lacks role=img")
        title = root.find(f"{SVG_NS}title")
        if title is None or not (title.text or "").strip():
            problems.append("no child title with text")
        skip = {f"{SVG_NS}{n}" for n in ("title", "desc", "metadata",
                                          "defs")}
        drawn = [c for c in root if c.tag not in skip]
        background = drawn[0] if drawn else None
        if background is None or background.tag != f"{SVG_NS}rect":
            problems.append("first drawing element is not a rect")
            background = None
        else:
            if (background.get("fill") or "").lower() != "#fff":
                problems.append("background rect is not fill=#fff")
            try:
                _x, _y, width, height = (
                    float(v) for v in root.get("viewBox", "").split())
                for name, want in (("width", width), ("height", height)):
                    value = background.get(name, "")
                    if value != "100%" and float(value) != want:
                        problems.append(f"rect {name} is not the view box")
            except ValueError:
                problems.append("rect or viewBox is not numeric")
        for element in root.iter():
            local = element.tag.rsplit("}", 1)[-1]
            if local in ("script", "foreignObject", "image", "use"):
                problems.append(f"element {local}")
            if local == "style" and "url(" in (element.text or ""):
                problems.append("style element with url(")
            for name, value in element.attrib.items():
                attribute = name.rsplit("}", 1)[-1]
                if attribute == "href":
                    problems.append(f"attribute {name}")
                if attribute == "style" and "url(" in value:
                    problems.append("style attribute with url(")
                if re.match(r"\s*(https?:|//)", value):
                    problems.append(f"attribute {name}={value!r}")
                if attribute in ("stroke", "fill") and not (
                        element is background and attribute == "fill"):
                    if value.lower() not in ("#000", "none"):
                        problems.append(f"{attribute}={value!r}")
        return problems

    def test_every_shipped_image_is_safe_svg(self) -> None:
        """Scenario: Shipped structure images."""
        files = sorted(SVG_DIR.glob("*.svg"))
        self.assertTrue(files, "site/static/structures has no .svg file")
        self.assertIn("osdb-0003.svg", [f.name for f in files])
        for path in files:
            with self.subTest(file=path.name):
                self.assertEqual(self.check(path), [])


class PrintStylesheetTests(unittest.TestCase):
    def test_print_colours_are_black_on_white(self) -> None:
        """Scenario: Print colours."""
        declarations = css("print.css")
        for decl in declarations:
            value = ps.plain_value(decl.value)
            if decl.prop == "color":
                with self.subTest(selector=decl.selector, prop="color"):
                    self.assertEqual(value, "#000")
            elif decl.prop in ("background", "background-color"):
                with self.subTest(selector=decl.selector, prop=decl.prop):
                    self.assertIn(value, ("#fff", "none", "transparent"))
        html = {d.prop: ps.plain_value(d.value) for d in declarations
                if "html" in ps.selectors_of(d)}
        self.assertEqual(html.get("color"), "#000")
        self.assertIn(html.get("background", html.get("background-color")),
                      ("#fff",))

    def test_page_break_declarations_are_present(self) -> None:
        """Scenario: Declarations present."""
        declarations = css("print.css")

        def has(selector: str, prop: str, value: str) -> bool:
            return any(selector in ps.selectors_of(d) and d.prop == prop
                       and ps.plain_value(d.value) == value
                       for d in declarations)

        for tag in ("h1", "h2", "h3", "h4"):
            with self.subTest(selector=tag):
                self.assertTrue(has(tag, "break-after", "avoid"))
        for tag in ("tr", "li", "figure"):
            with self.subTest(selector=tag):
                self.assertTrue(has(tag, "break-inside", "avoid"))
        with self.subTest(selector="thead"):
            self.assertTrue(has("thead", "display", "table-header-group"))
        with self.subTest(selector="the metadata panel's rows"):
            self.assertTrue(any(
                "metadata" in d.selector and d.prop == "break-inside"
                and ps.plain_value(d.value) == "avoid"
                for d in declarations))

    def test_no_print_stylesheet_clips_content(self) -> None:
        """Scenario: No clipping CSS in print."""
        for name in PRINT_SOURCES:
            with self.subTest(file=name):
                self.assertEqual(ps.clipping_violations(css(name)), [])


class ClippingCheckTests(unittest.TestCase):
    """The check must reject what the spec forbids, or the test above
    would hold nothing."""

    def violations(self, source: str) -> list[str]:
        return ps.clipping_violations(ps.parse_css(source))

    def test_each_forbidden_declaration_is_rejected(self) -> None:
        """Scenario: No clipping CSS in print (checker, rejected)."""
        for source in ("p { overflow: hidden }", "p { overflow-x: clip }",
                       "p { overflow-y: hidden }",
                       "@media print { p { height: 10px } }",
                       "p { max-height: 5em }", "figure { max-height: 5em }",
                       "p { overflow: hidden auto }"):
            with self.subTest(source=source):
                self.assertNotEqual(self.violations(source), [])
        self.assertNotEqual(ps.clipping_violations(
            ps.inline_declarations("height:1px; overflow:hidden")), [])

    def test_allowed_declarations_are_accepted(self) -> None:
        """Scenario: No clipping CSS in print (checker, accepted)."""
        for source in ("p { overflow: visible }", "p { height: auto }",
                       "p { max-height: none }", "img { max-height: 90% }",
                       ".structure img { max-height: 60mm }",
                       "td, th { overflow-wrap: anywhere }"):
            with self.subTest(source=source):
                self.assertEqual(self.violations(source), [])


class NoNodeInToolsTests(unittest.TestCase):
    def test_tools_never_mention_node_or_npm(self) -> None:
        """Scenario: No Node in the tools (file search)."""
        tools = REPO / "tools"
        self.assertTrue(tools.is_dir())
        found = []
        for path in sorted(tools.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                if re.search(r"\b(node|npm)\b", line, re.I):
                    found.append(f"{path.relative_to(REPO)}:{number}")
        self.assertEqual(found, [])

    def test_check_deps_neither_reports_nor_requires_node(self) -> None:
        """Scenario: No Node in the tools (check-deps)."""
        sandbox = ps.make_sandbox(self)
        path = ps.make_path(self, ("python3", "emacs", "git",
                                   "hugo", "weasyprint"))
        result = sandbox.program("check-deps",
                                 env=sandbox.env(PATH=str(path.directory)))
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        for line in (result.stdout + result.stderr).splitlines():
            self.assertNotRegex(line, r"(?i)\bnode\b")
