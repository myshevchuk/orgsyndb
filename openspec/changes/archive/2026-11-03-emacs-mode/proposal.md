## Why

Writing a procedure means remembering front-matter keys, the exact
vocabulary slugs, the compound keys of the registry and the procedure
IDs, then running `orgsyndb validate` and reading `path:field` lines to
find mistakes, and restarting `serve` to see the result. The owner
writes in Emacs. An Emacs mode that knows the collection can complete
those keys and values, jump to compounds and procedures, show problems
where they are, keep the modification time current and build a preview
of the page being edited.

## What Changes

- A new Emacs package, `orgsyndb`, ships in the application repository
  under `emacs/`. It needs Emacs 29.1, like the export, and no
  third-party package. It is loaded from the same checkout as the
  program it calls, and finds `tools/orgsyndb` beside itself.
- `tools/osdb-org.el`, the Org front end of the export, moves to
  `emacs/osdb-org.el`, so that the package and the export share it and
  the package directory is complete on its own. `tools/export.el` loads
  it from there. The front end gains a reader of an Org source's front
  matter.
- `global-orgsyndb-mode` turns on `orgsyndb-mode` in every buffer
  visiting a file of a collection: Org and Markdown procedures,
  sequences, compound files, vocabularies and `orgsyndb.toml`.
- The mode reads the collection through `orgsyndb index` (the
  `collection-index` change), refreshed when a collection file is
  saved, and reads Org sources itself through the front end.
- Completion at point: front-matter keys and values in Markdown and Org
  procedures (statuses, languages, reaction types, declared fields and
  their vocabularies, compound keys, structure images, tags and authors
  in use), Org scope-table cells, sequence steps and targets, and
  compound-file keys and values. A command inserts a compound chosen by
  name.
- Navigation: `xref` definitions and references for compound keys and
  procedure and sequence IDs, wherever they appear in a collection
  file; `eldoc` shows a compound's name, formula and MW, or a
  procedure's title and status.
- Language variants: a command visits another variant of the procedure,
  and one creates a translation with the shared front matter and the
  other language's section headings.
- Diagnostics through Flymake: the Org front end's checks run on the
  buffer as it is typed; `orgsyndb validate` runs on save, and its
  problems appear on the line of the field they name. A thin Flycheck
  adapter offers the same diagnostics to Flycheck users.
  `orgsyndb-validate` lists every problem in a compilation buffer.
- Timestamps: saving updates `#+LAST_MODIFIED` or `lastmod` through
  `time-stamp`, in Europe/Berlin with an English weekday and the right
  offset, set buffer-locally so that the user's own `time-stamp`
  settings are untouched elsewhere.
- Commands for a new procedure (through `orgsyndb new`) and a new
  compound file, prompted from the schema and the declared fields.
- Preview: one `orgsyndb serve` process per collection; `orgsyndb-preview`
  rebuilds and opens the page of the file being edited; an optional mode
  rebuilds on save; `orgsyndb-pdf` builds the PDFs and opens the
  procedure's.
- A structure window shows the structure image of the compound at
  point.
- A transient menu on `C-c C-;` gathers the commands.

## Capabilities

### New Capabilities

- `emacs-mode`: the package, its activation, completion, navigation,
  diagnostics, timestamps, commands, preview and tests.

### Modified Capabilities

- `org-export`: the Org front end lives in `emacs/osdb-org.el`, the
  export loads it from there, and it reads an Org source's front matter
  for the editor.

## Impact

- Code: new `emacs/orgsyndb.el` and further `emacs/orgsyndb-*.el`
  files, `emacs/orgsyndb-flycheck.el`; `tools/osdb-org.el` moved to
  `emacs/osdb-org.el` and extended; `tools/export.el` loads it from its
  new place.
- Tests: a new ERT suite `tests/el/orgsyndb-tests.el` run by
  `tests/test_elisp.py`, which gains a test for it; `tests/el/osdb-org-tests.el`,
  `tests/test_export_integration.py` and the Emacs 29 workflow's
  comment follow the move.
- Docs: a README section on installing and using the mode, and the Org
  and Markdown authoring guides' pointers to it (doc writer).
- Depends on `collection-index`, which must be merged first.
- Deferred, recorded in `openspec/STATE.md`: cross-references in
  procedure bodies and their completion, the reagents-table helper, and
  a preview in the other language.
