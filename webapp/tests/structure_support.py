"""Molfiles, uploads and drawing checks shared by the tests of the
structure images (lab-registry "Structure images").

Nothing here imports Django, the lab's packages or RDKit at module
level, so a test that uses these helpers fails on its own assertions
while the packages are missing.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Iterator

SVG = "{http://www.w3.org/2000/svg}"
HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
}
# The colours the spec lets a drawing name: black and white, and none.
PLAIN = {"#000", "#000000", "#fff", "#ffffff", "none", "black", "white"}


def v2000(name: str, atoms: list[tuple[float, float, str]],
          bonds: list[tuple[int, int, int]], extra: str = "") -> str:
    """A V2000 molfile of ``name`` with LF line endings: ``atoms`` are
    the coordinates and element of each atom, ``bonds`` the numbers of
    two atoms (from 1) and the bond order; ``extra`` lines come before
    ``M  END``."""
    lines = [name, "     RDKit          2D", "",
             f"{len(atoms):3d}{len(bonds):3d}  0  0  0  0  0  0  0  0999 "
             "V2000"]
    lines += [f"{x:10.4f}{y:10.4f}{0:10.4f} {symbol:<3}0  0  0  0  0  0  0  "
              "0  0  0  0  0" for x, y, symbol in atoms]
    lines += [f"{a:3d}{b:3d}{order:3d}  0" for a, b, order in bonds]
    return "\n".join(lines) + "\n" + extra + "M  END\n"


ACETONE_ATOMS = [(-1.299, -0.75, "C"), (0.0, 0.0, "C"), (1.299, -0.75, "C"),
                 (0.0, 1.5, "O")]
ACETONE_BONDS = [(1, 2, 1), (2, 3, 1), (2, 4, 2)]
ETHANOL_BONDS = [(1, 2, 1), (2, 3, 1)]

ACETONE = v2000("acetone", ACETONE_ATOMS, ACETONE_BONDS)
ETHANOL = v2000("ethanol", [(-1.299, -0.25, "C"), (0.0, 0.5, "C"),
                            (1.299, -0.25, "O")], ETHANOL_BONDS)
# Every atom at the origin: the drawing has to compute coordinates.
ETHANOL_AT_THE_ORIGIN = v2000(
    "ethanol", [(0.0, 0.0, "C"), (0.0, 0.0, "C"), (0.0, 0.0, "O")],
    ETHANOL_BONDS)
# Atoms in a vertical line: a drawing that keeps the coordinates draws
# vertical bonds.
ETHANOL_IN_A_COLUMN = v2000(
    "ethanol", [(0.0, 0.0, "C"), (0.0, 1.5, "C"), (0.0, 3.0, "O")],
    ETHANOL_BONDS)
ALIAS = "<script>alert(1)</script>"
ACETONE_WITH_AN_ALIAS = v2000("acetone", ACETONE_ATOMS, ACETONE_BONDS,
                              f"A    1\n{ALIAS}\n")
# A molfile that holds no atom.
NO_ATOM = v2000("empty", [], [])
NOT_A_MOLFILE = "not a molfile"
# A molfile that RDKit reads, followed by lines it ignores, in all a
# little over 1.1 million bytes.
LARGE = ACETONE + ("x" * 99 + "\n") * 12000
# A molfile that RDKit reads, saved as Latin-1, which is not UTF-8.
LATIN_1 = v2000("Äthanol", [(-1.299, -0.25, "C"), (0.0, 0.5, "C"),
                            (1.299, -0.25, "O")],
                ETHANOL_BONDS).encode("latin-1")


def crlf(text: str) -> str:
    """``text`` with CR LF line endings."""
    return text.replace("\n", "\r\n")


def upload(content: str | bytes, name: str = "structure.mol") -> Any:
    """A file to post, holding ``content`` (text is encoded as UTF-8)."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(
        name, content if isinstance(content, bytes)
        else content.encode("utf-8"), content_type="chemical/x-mdl-molfile")


def tag(element: ET.Element) -> str:
    """The local name of an element's tag."""
    return element.tag.rsplit("}", 1)[-1]


def parsed(body: bytes | str) -> ET.Element:
    """The root of the XML document ``body``."""
    return ET.fromstring(body.encode("utf-8") if isinstance(body, str)
                         else body)


def named_colours(root: ET.Element) -> Iterator[str]:
    """Each colour the document names: the ``fill`` and ``stroke``
    attributes and the ``fill`` and ``stroke`` declarations of the
    ``style`` attributes, lower-cased."""
    for element in root.iter():
        for name in ("fill", "stroke"):
            if element.get(name) is not None:
                yield element.get(name).strip().lower()
        for declaration in element.get("style", "").split(";"):
            name, _, value = declaration.partition(":")
            if name.strip().lower() in ("fill", "stroke"):
                yield value.strip().lower()


def points(path: ET.Element) -> list[tuple[float, float]]:
    """The coordinate pairs of a path's ``d`` attribute."""
    numbers = [float(n) for n in re.findall(
        r"-?\d+(?:\.\d+)?", path.get("d", ""))]
    return list(zip(numbers[0::2], numbers[1::2]))


def bonds(root: ET.Element) -> list[list[tuple[float, float]]]:
    """The points of each bond path (a path whose class names a bond)
    of a drawing."""
    return [points(path) for path in root.iter(SVG + "path")
            if "bond-" in path.get("class", "")]
