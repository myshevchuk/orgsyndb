"""Tests of the level colours in lab.css (end-product-inventory: Stock
levels)."""

import colorsys
import re
from pathlib import Path

from django.test import SimpleTestCase

from . import REPO

CSS = REPO / "webapp" / "orgsyndb_web" / "static" / "lab.css"
LEVELS = ("out", "critical", "low", "watch")
MINIMUM = 4.5
# Hue ranges in degrees of the colours the spec names.
HUES = {"out": (-15, 15), "critical": (15, 45), "low": (45, 70),
        "watch": (70, 170)}


def luminance(colour: str) -> float:
    """The relative luminance of ``#rrggbb`` as WCAG 2 defines it."""
    channels = []
    for start in (1, 3, 5):
        value = int(colour[start:start + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.03928
                        else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)),
                             reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def hue(colour: str) -> float:
    red, green, blue = (int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    degrees = colorsys.rgb_to_hsv(red, green, blue)[0] * 360
    return degrees - 360 if degrees > 345 else degrees


def balanced(text: str, start: int) -> tuple[str, int]:
    """The text inside the braces that open at or after ``start``, and
    the index after the closing brace."""
    opening = text.index("{", start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index], index + 1
    raise AssertionError("unbalanced braces in lab.css")


def split_schemes(text: str) -> tuple[str, str]:
    """The stylesheet without its dark-scheme blocks, and those blocks'
    contents."""
    light, dark, position = [], [], 0
    for found in re.finditer(
            r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)", text):
        if found.start() < position:
            continue
        light.append(text[position:found.start()])
        body, position = balanced(text, found.end())
        dark.append(body)
    light.append(text[position:])
    return "".join(light), "\n".join(dark)


def root_tokens(text: str) -> dict[str, str]:
    """The level tokens that ``:root`` blocks in ``text`` declare."""
    tokens: dict[str, str] = {}
    for found in re.finditer(r":root\s*\{", text):
        body, _ = balanced(text, found.start())
        for name, value in re.findall(
                r"(--level-(?:out|critical|low|watch)-(?:bg|fg))\s*:\s*"
                r"(#[0-9a-fA-F]{6})\s*;", body):
            tokens[name] = value
    return tokens


class LevelColourTests(SimpleTestCase):

    def pair(self, tokens: dict[str, str], level: str) -> tuple[str, str]:
        """The background and the text colour of ``level``."""
        names = (f"--level-{level}-bg", f"--level-{level}-fg")
        for name in names:
            self.assertIn(name, tokens, f"{name} is not defined")
        return tokens[names[0]], tokens[names[1]]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        text = Path(CSS).read_text(encoding="utf-8")
        cls.text = text
        light, dark = split_schemes(text)
        cls.light = root_tokens(light)
        cls.dark = root_tokens(dark)

    def test_all_eight_tokens_are_defined_in_both_schemes(self) -> None:
        names = {f"--level-{level}-{part}" for level in LEVELS
                 for part in ("bg", "fg")}
        self.assertEqual(set(self.light), names)
        self.assertEqual(set(self.dark), names)

    def test_contrast_in_the_light_scheme(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level):
                ratio = contrast(*self.pair(self.light, level))
                self.assertGreaterEqual(ratio, MINIMUM)

    def test_contrast_in_the_dark_scheme(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level):
                ratio = contrast(*self.pair(self.dark, level))
                self.assertGreaterEqual(ratio, MINIMUM)

    def test_the_four_backgrounds_differ_in_each_scheme(self) -> None:
        for name, tokens in (("light", self.light), ("dark", self.dark)):
            with self.subTest(scheme=name):
                backgrounds = {self.pair(tokens, level)[0].lower()
                               for level in LEVELS}
                self.assertEqual(len(backgrounds), 4)

    def test_the_backgrounds_are_red_orange_yellow_and_pale_green(
            self) -> None:
        for name, tokens in (("light", self.light), ("dark", self.dark)):
            for level, (low, high) in HUES.items():
                with self.subTest(scheme=name, level=level):
                    shown = hue(self.pair(tokens, level)[0])
                    self.assertGreaterEqual(shown, low)
                    self.assertLessEqual(shown, high)

    def test_the_level_classes_use_the_tokens(self) -> None:
        for level in LEVELS:
            with self.subTest(level=level):
                rules = []
                for found in re.finditer(
                        rf"\.level-{level}\b[^{{}}]*\{{", self.text):
                    rules.append(balanced(self.text, found.start())[0])
                body = "\n".join(rules)
                self.assertIn(f"var(--level-{level}-bg)", body)
                self.assertIn(f"var(--level-{level}-fg)", body)

    def test_the_luminance_function_is_the_wcag_one(self) -> None:
        self.assertAlmostEqual(contrast("#000000", "#ffffff"), 21.0)
        self.assertAlmostEqual(contrast("#777777", "#ffffff"), 4.478, 3)
        self.assertAlmostEqual(contrast("#ffffff", "#ffffff"), 1.0)
