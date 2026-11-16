"""The drawing of a substance's structure from its molfile, with RDKit.

A molfile is read as drawn: without strict valence checks, so that an
unusual valence still draws, and with the file's atom coordinates and
wedges. RDKit is imported on the first reading, not with this module.
"""

from typing import Any

from django.utils.translation import gettext as _

# The colour of the drawing's background, white, as RDKit takes it.
WHITE = (1.0, 1.0, 1.0, 1.0)


def lf(text: str) -> str:
    """Return TEXT with its CR LF and lone CR line endings made LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _read(molfile: str) -> Any:
    """Return the molecule RDKit reads from MOLFILE, its valences
    computed without strict checks and sanitized as far as RDKit can, or
    None when RDKit reads no molecule from it."""
    from rdkit import Chem
    try:
        molecule = Chem.MolFromMolBlock(molfile, sanitize=False,
                                        removeHs=False)
    except RuntimeError:
        return None
    if molecule is None:
        return None
    molecule.UpdatePropertyCache(strict=False)
    Chem.SanitizeMol(molecule, Chem.SanitizeFlags.SANITIZE_ALL
                     ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES,
                     catchErrors=True)
    return molecule


def refusal(molfile: str) -> str | None:
    """Return why MOLFILE cannot be drawn or kept, in the active
    language: it holds no text, it holds a NUL character, which a
    PostgreSQL text column cannot hold, RDKit reads no molecule from it,
    or the molecule has no atom; None when it can be drawn."""
    if not molfile.strip():
        return _("The molfile is empty.")
    if "\x00" in molfile:
        return _("The molfile holds a NUL character.")
    molecule = _read(molfile)
    if molecule is None:
        return _("RDKit reads no molecule from this molfile.")
    if molecule.GetNumAtoms() == 0:
        return _("The molecule of this molfile has no atom.")
    return None


def draw(molfile: str) -> str:
    """Return the SVG document of the structure MOLFILE describes.

    The drawing is black on a white background, its size follows the
    molecule's, and its root ``svg`` element has a ``viewBox``. It keeps
    the file's atom coordinates and wedges; when every atom lies at the
    origin, RDKit computes the coordinates. An atom's alias is drawn as
    its label, as outlines rather than text, and atom map numbers are
    not drawn. Raise ValueError when ``refusal`` refuses MOLFILE.
    """
    from rdkit import Chem
    from rdkit.Chem import rdDepictor
    from rdkit.Chem.Draw import rdMolDraw2D
    molecule = _read(lf(molfile))
    if molecule is None or molecule.GetNumAtoms() == 0:
        raise ValueError(refusal(molfile))
    for atom in molecule.GetAtoms():
        atom.ClearProp("molAtomMapNumber")
        if atom.HasProp("molFileAlias"):
            atom.SetProp("atomLabel", atom.GetProp("molFileAlias"))
    conformer = molecule.GetConformer() \
        if molecule.GetNumConformers() else None
    if conformer is None or not conformer.GetPositions().any():
        rdDepictor.Compute2DCoords(molecule)
    else:
        Chem.ReapplyMolBlockWedging(molecule)
    drawer = rdMolDraw2D.MolDraw2DSVG(-1, -1)
    options = drawer.drawOptions()
    options.useBWAtomPalette()
    options.setBackgroundColour(WHITE)
    drawer.DrawMolecule(rdMolDraw2D.PrepareMolForDrawing(
        molecule, kekulize=False, addChiralHs=False, wedgeBonds=False))
    drawer.FinishDrawing()
    return drawer.GetDrawingText()
