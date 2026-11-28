## Why

After the split layouts the owner asked on 2026-11-28 for four
refinements: pages outside the main lists still stop at the shell's
96rem cap; the view switch needs aiming at the other button and the
larger-area toggle is wordy; the substance pane buries the compound;
and a record page's back link drops the list's filters and selection,
unlike the browser's back button.

## What Changes

- The page shell no longer caps its width, on the lab and the static
  site; running prose and forms keep their measures.
- One layout picker of three icon buttons (table only, split with the
  table larger, split with the details larger) replaces the
  `Tabelle`/`Details` buttons and the larger-area toggle; the view and
  split cookies stay.
- The substance list's details put the compound widget on the left and
  the containers, batches and tasks on the right.
- Back links open the list with the record selected, and go back in
  history when the page was opened from that list.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: "Back links" names the record in `selected` and returns
  through history when the page came from its list.

## Impact

- `site/assets/css/screen.css`, `lab.css`, `lab.js`,
  `inventory/templates/inventory/view_switch.html` and the list
  toolbars that include it, `registry/templates/registry/list.html`,
  the seven record page templates and `orgsyndb_web/back.html`,
  German catalogues, tests, `README.md`.
