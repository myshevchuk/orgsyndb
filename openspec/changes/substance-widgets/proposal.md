## Why

The substance page stacks a long definition list beside an isolated
structure drawing, then up to seven headed sections of bullet lists
whose items glue ID, entry, yield and status together with middots.
The owner chose mockup A of the UI survey (2026-11-22) for it, the
second of the pages to move onto the widgets that `lab-widgets`
introduced (web-app "Widgets").

## What Changes

- The substance's data moves into a compound widget at the top right:
  the structure drawing, then a key–value table of article number,
  formula, molar mass, CAS number, SMILES with its copy button,
  inventory group, chemical classes, key, name, German name, short
  name and note. The heading line keeps the name and adds the key,
  the inventory group and the chemical classes as short marks.
- Containers, batches and tasks become three table widgets side by
  side: article and size with the count; batch with its amount in
  open vessels; task with its state. Each still reads `Keine` when
  empty.
- `Hergestellt nach`, `Verwendet in` and `Synthesewege` become table
  widgets with a column per value (procedure, entry, yield, status;
  procedure, status; sequence, title) instead of middot-joined lines.
- `Herstellungswege` keeps its tree, in a collapsible widget, open
  when the page loads.
- **BREAKING** (spec text only) The Registry pages requirement stops
  prescribing the middot-joined line format for the substance page's
  procedure lists; it names their values instead. The route tree's
  steps keep the line format.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lab-registry`: Registry pages — the substance page shows its data
  in widgets (web-app "Widgets"); its procedure, sequence, container,
  batch and task lists are tables of the same values; its scenarios
  follow.

## Impact

- Templates: `registry/substance.html`; `registry/procedure_item.html`
  stays for the route tree. `lab.css` for the page's grid if the
  shared widget classes do not suffice.
- German catalogue of `registry` for new column labels.
- Tests: `test_registry_pages.py` and `test_registry_collection.py`
  read the old lists and definition list.
