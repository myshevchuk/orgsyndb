## Context

The procedure page is built by Hugo from `site/layouts/procedures/page.html`:
the header partial (ID line, `h1`, key facts, print facts, actions,
structure figures), then `article.procedure` with
`div.procedure-details` (one `dl.metadata`), the scope of a general
procedure, `div.procedure-content` (`.Content`) and the hidden index
elements. The lab pages already have the widget classes in the site's
`screen.css` (lab-widgets): `section.widget`, `.widget__head` with an
`h2`, `.widget__body`, `.widget .structure`. The chosen mockup is
`procedure-A` of the survey in
`~/local/workspace/orgsyndb/ui-widgets-survey/mockups/`, with the notes
beside the steps taken from `procedure-B`.

Body sections are fixed by validation: eight `h2` sections in a fixed
order, named in English or German (`tools/validate.py`
`SECTIONS_BY_LANGUAGE`); a general procedure adds its scope above them.
Goldmark renders `<h2 id="...">` in `.Content`; the note anchors and
links come from `pipeline.link_notes`.

## Goals / Non-Goals

**Goals:** the same compound widget as the substance page; the
metadata split into three small widgets; every body section in a
widget; notes beside the steps on wide screens; print and search
unchanged in substance.

**Non-Goals:** new data (no reagent counts, no step counts, no lab
links — the links change comes later), sortable reagent tables (would
need script logic on the site), collapsible sections, any change to
the PDF pipeline or `print.css` beyond what the new markup needs.

## Decisions

1. **Split `.Content` in the template.** A new partial
   `procedure-sections.html` splits the rendered body on `<h2` and
   wraps each part: `section.widget.procedure-section`, the `h2` in
   `div.widget__head`, the rest in `div.widget__body`. Escaped markup
   in code blocks is `&lt;h2`, so it never matches. Alternative
   rejected: wrapping in `pipeline.stage_content` — it would put layout
   markup into the Markdown staging and the Org/Markdown twin test.
   Alternative rejected: a script that wraps on load — print and
   no-script readers would lose it.

2. **Roles from a table, checked against validation.** The partial
   holds a dict from the sixteen section names to the eight roles and
   writes `data-section`. A test compares it with
   `SECTIONS_BY_LANGUAGE`, so a renamed section fails a test instead of
   losing its place. Alternative rejected: roles by position — an
   unknown extra `h2` would shift every role. Alternative rejected:
   heading ids — they are slugs of the language's text, so the same
   list in another form.

3. **A band of details above a full-width body; notes beside the
   steps by dense packing, screen only.** At 1440 px `main` is about
   1048 px wide; a rail beside the body as in mockup A would leave
   about 700 px for Procedure and Notes together. So the three details
   widgets form a band of columns above the body (as mockup B's top
   band), and the body widgets use the full width.
   `div.procedure-content` becomes a two-column grid with
   `grid-auto-flow: dense`: every child spans both columns, except
   `procedure` and `workup`, which take the first, and `notes`, which
   takes the second and spans two rows. Dense packing places the notes
   in the first free second-column slot, the procedure's row, without
   naming rows, so preamble content and sections without a role keep
   their authored places. Workup sits beside the notes too because it
   refers to them (OSDB-0003's Note 2). The column rules apply only
   when the content `:has` both a `procedure` and a `notes` section;
   otherwise everything spans. The notes align to the top. Below the
   breakpoint the grid is off and the authored order holds. The DOM is
   not reordered, so print and the search index keep the authored
   order. Alternative rejected: `grid-template-areas` — it moves
   preamble and unknown sections to the end and leaves holes when a
   role is missing.

4. **Three widgets, one panel.** The details wrapper holds the
   compound widget, `Details` and `Synthesis context`, each with its
   own `dl.metadata`. Other specs that name "the metadata panel"
   (compound-fields, procedure-fields, synthesis-sequences,
   procedure-authors, site-search) stay true, because the panel is
   defined as the pairs of the three lists in order. `Starting
   materials` moves to the context widget beside `Precursors`, which
   changes the canonical label order. Alternative rejected: `table.kv-table`
   as in the lab — every panel test and Pagefind's word separation rely
   on `dt`/`dd`; the site styles `.widget dl.metadata` to look like the
   lab's key–value table instead.

5. **Structure figures move into the compound widget.** They leave the
   header, which becomes a compact title block. Inside
   `article.procedure` they would add `alt` text to the search index,
   so every figure carries `data-pagefind-ignore` (the placeholder
   already does), and so do the three widget title bars. Print order becomes header, compound widget with the
   structure, details, context, scope, body — the structure still
   prints on the first page.

6. **Compound widget rows follow the lab.** The substance page's
   compound widget, fixed by substance-widgets, orders formula, molar
   mass, CAS number, SMILES; the site's facts already follow that
   order, and a test compares the two templates so they cannot drift.
   The site keeps its own labels (`CAS`, `MW`) and the rows the site
   data has; the lab's registry-only rows (group, classes, key, names,
   note) are not added — that would be new data on the site.

7. **All sections stay open.** The mockup folded secondary sections;
   hazards must never be hidden and print needs everything, so every
   section is a plain `section.widget`. Folding can come later with a
   remembered state if the owner asks.

9. **Widget styles adapted to prose.** The lab's `.widget` sets a small
   font, `overflow: hidden` and flush `h3` bars for tables. Body
   sections keep the body font size and the reading measure, do not
   clip the `:target` highlight of a note, and leave `h3` in prose as
   headings. The section title bar itself looks like the lab's.

8. **Specs give up the layout.** site-theme "Measure and tables" no
   longer fixes `.procedure`/`.procedure-header` columns or their
   narrow-window declarations; the requirement keeps the table markup,
   the measure and "wide tables scroll locally". Positions are checked
   in the browser (tasks section 4), not in the specs.

## Risks / Trade-offs

- [Splitting HTML with string functions] → the input is Goldmark
  output of validated files; a test reads every procedure page and
  checks that each section holds exactly one `h2` and that no `h2`
  stands outside a section. A `##` heading nested in a block quote or
  list item would split its container across two widgets; no shipped
  or fixture procedure has one, and validation reads such a heading as
  a section anyway, so the split follows validation's view.
- [PDF page breaks change] → `break-after: avoid` still applies to the
  `h2`s; the print-layout PDF tests (page ends, steps on one page, no
  clipping, warning-free run) run in this change.
- [Three framed `dl.metadata` in print, each under its own `h2`] →
  accepted: they read as three short tables; the page images are
  inspected (task 4.3). `break-after: avoid` on `.widget__head` keeps
  each title with its list.
- [Long notes leave a gap under Workup] → accepted; the notes are the
  reason for the column, and the gap is blank space, not lost text.
- [Shared `print.css`] → lab pages load it too, so new print rules are
  scoped to the procedure page.
