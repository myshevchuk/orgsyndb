## Why

A review of the site's layout found six places where a page repeats
itself, hides what it is doing, or withholds something a chemist needs:

- On a term page the header search is silently scoped, and its only hint,
  the placeholder `Vorschriften des Reaktionstyps Hydrolyse durchsuchen`,
  is cut off at `…durchsu`.
- The home page's `h1` repeats `OrgSynDB` directly under the identical
  site title, and the drafts that await a check appear only as a count,
  `Entwürfe (8)`, though checking them is the group's standing work.
- The metadata panel repeats the ID that the header line above it shows,
  and the product name when it is the title.
- The footer tells the reader nothing the header does not; nothing says
  how current the site is.
- Stacked in the status facet, the German labels `Entwurf`, `geprüft` and
  `zurückgezogen` read as inconsistent.
- A step's `(Note 1)` is plain text, so a reader at the bench scrolls to
  the notes and counts.

## What Changes

- **Term-page search.** The header field's placeholder on a term page
  becomes `Search these procedures` (`Diese Vorschriften durchsuchen`),
  short enough to show whole. Its accessible name still names the scope.
- **Home page.** The `h1` becomes `Synthetic procedures`
  (`Synthesevorschriften`), and the lede neither repeats it nor says
  `checked` of the schema, a word the page now keeps for a colleague's
  check. A new section, `Not yet checked` (`Noch nicht geprüft`), lists
  the first five drafts by ID with their creation dates and links all of
  them with their count; it is absent when there is no draft. The browse
  list drops its `Draft procedures` entry, which that section replaces.
- **Metadata panel.** The `ID` pair goes, and `Product` appears only when
  it differs from the title, as in the catalogue's Details view. A hidden
  `span.index-terms` keeps the ID and the product name in the indexed
  text, so search finds them as before.
- **Footer.** It adds the time the site was built: `built 2026-10-28
  20:08` (`Stand 2026-10-28 20:08`), the same on every page of a build.
- **German status labels.** `Geprüft` and `Zurückgezogen`, capitalised
  like `Entwurf`.
- **Note references.** Staging links each `(Note n)` or `(Anmerkung n)`
  to its note, which gets the anchor `note-n`; a targeted note is
  highlighted on screen. References to notes that do not exist stay
  plain.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-theme`: the page shell's footer, the procedure page's
  index-terms element, the metadata panel, the home page, and the new
  note references.
- `site-catalogue`: the term page's search placeholder.
- `site-search`: the index-terms element in the indexed content.
- `localization`: the German strings, and staging links notes.

## Impact

- Layouts: `home.html`, `site-footer.html`, `site-header.html`,
  `procedure-meta.html`, `procedures/page.html`, a new
  `index-terms.html` partial; both i18n files; `screen.css`.
- `tools/pipeline.py`: `link_notes`, applied by `stage_content`.
- Tests: page shell, home page, metadata panel and indexed content,
  catalogue controls, German strings, staging, and `link_notes`.
- Docs: `README.md` where it describes the home page, the term-page
  search, the details panel and the footer; the four authoring guides,
  `docs/AUTHORING.md`, `AUTHORING.de.md`, `AUTHORING-ORG.org` and
  `AUTHORING-ORG.de.org`, on how to refer to a note.
