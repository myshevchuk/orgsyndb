Starts after `collection-index` is merged; rebase this branch onto
`main` first.

## 1. The Org front end moves

- [x] 1.1 Move `tools/osdb-org.el` to `emacs/osdb-org.el`; load it from
  there in `tools/export.el`, `tests/el/osdb-org-tests.el` and
  `tests/test_export_integration.py`; add `emacs` to the directories
  `tests/pipeline_support.py` copies into an application copy; update
  the comments of `tests/test_elisp.py` and
  `.github/workflows/emacs-29.yml`, and the living specs and README
  lines that name the old path. The existing suites stay green
- [x] 1.2 ERT, red first: org-export "Front matter of an Org source"
- [x] 1.3 `osdb-org-front-matter`

## 2. Tests, red first

- [x] 2.1 `tests/el/orgsyndb-tests.el` with its fixture helpers: copies
  of the test collection and the demo, a fixed current time, a stub
  program that records its arguments, a `browse-url` recorder
- [x] 2.2 Package files, program, turning the mode on, collection data
- [x] 2.3 Completion in Markdown procedures, Org procedures, sequences
  and compound files; inserting a compound
- [x] 2.4 Definitions and references; documentation at point
- [x] 2.5 Language variants
- [x] 2.6 Problem locations; diagnostics while typing; validation on
  save; one command at a time; validation buffer; diagnostics front end
- [x] 2.7 Timestamps on save
- [x] 2.8 New procedure and new compound
- [x] 2.9 Preview, PDF, structure window, command menu
- [x] 2.10 `tests/test_elisp.py`: the package suite and the byte
  compilation of every `emacs/*.el`

## 3. Implementation

- [x] 3.1 `emacs/orgsyndb.el`: package headers, options, the program,
  collection roots and file kinds, `orgsyndb-mode` and
  `global-orgsyndb-mode`, the index and the Org records
- [x] 3.2 Completion at point and `orgsyndb-insert-compound`
- [x] 3.3 The `xref` backend and the `eldoc` function
- [x] 3.4 Variants: visit and create a translation
- [x] 3.5 Problem locations, the per-collection command queue, the
  Flymake backend, validation on save, `orgsyndb-validate`
- [x] 3.6 `emacs/orgsyndb-flycheck.el`
- [x] 3.7 Timestamps through `time-stamp`
- [x] 3.8 New procedure, new compound
- [x] 3.9 Serve, preview, preview on save, PDF
- [x] 3.10 The structure window
- [x] 3.11 `orgsyndb-dispatch` and the key binding

## 4. Documents

- [x] 4.1 README: installing the package from the checkout (load path,
  a local recipe, `package-vc-install` with `:lisp-dir`) and what the
  mode does; pointers from the Org and Markdown authoring guides, in
  both languages (doc writer)

## 5. Verification

- [ ] 5.1 Full suite green, the ERT suites included, and the Emacs 29
  workflow green
- [ ] 5.2 By hand in the owner's Emacs: completion through Corfu,
  Flymake diagnostics, `M-.`, the structure window and a preview in
  the browser, on a copy of the demo
- [x] 5.3 `openspec validate emacs-mode --strict`
