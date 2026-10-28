## Why

A procedure page opens with an ID line, a title and a print button, and
leaves everything that identifies and qualifies the procedure to the
margin: the structure drawing sits below the header at the top of the
details column, the scale and yield halfway down it, and who checked the
procedure among fifteen other facts. A chemist opening a procedure wants
three answers first — what it makes, at what scale and yield, and whether
anyone has checked it — and has to read down the margin for each.

*Organic Syntheses*, which OrgSynDB is modelled on, answers them at the
head of every procedure: the structure beside the title, the checkers'
names under it.

## What Changes

- The procedure header becomes a title block. Beside the ID line, the
  `h1`, the key facts and the actions stands the structure figure, at the
  top of the margin column, so that the drawing and the title read
  together.
- The key facts, `Scale` and `Yield`, move from the metadata panel into
  a `dl.key-facts` under the `h1`.
- The ID line carries a sign-off after the status badge: for a checked
  procedure with `checked_by`, `by <names>` (`von <names>`), so that it
  reads `checked by A. Example` (`Geprüft von A. Example`). The panel
  keeps its `Checked by` pair only where the status is not `checked`, so
  that the names show once.
- The status badge is set in normal case instead of tracked capitals.
- A rule closes the title block, above the body and the margin.
- Below 55rem and on paper the block keeps its document order: ID line,
  title, key facts, print facts, structure, then the panel and the body.

## Capabilities

### Modified Capabilities

- `site-theme`: procedure page structure, metadata panel, structure
  image slot, and the header columns and the desktop, print and narrow
  scenarios of "Measure and tables".
- `localization`: the German sign-off, and the German panel scenario.

## Impact

- Layouts: `procedure-header.html`, `procedures/page.html`,
  `procedure-meta.html`, `structure.html`; both i18n files;
  `base.css`, `screen.css`, `print.css`.
- Tests: procedure page order, key facts and sign-off, the panel, the
  structure slot, the narrow-window declarations, the German panel.
- Docs: `README.md` where it describes a procedure page, and the four
  authoring guides where they describe the page's fields.
