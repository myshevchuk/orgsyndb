Starts after `collection-index` is merged; rebase this branch onto
`main` first.

## 1. The Org front end moves

- [ ] 1.1 Move `tools/osdb-org.el` to `emacs/osdb-org.el`; load it from
  there in `tools/export.el`, `tests/el/osdb-org-tests.el` and
  `tests/test_export_integration.py`; update the comments of
  `tests/test_elisp.py` and `.github/workflows/emacs-29.yml`. The
  existing suites stay green
- [ ] 1.2 ERT, red first: org-export "Front matter of an Org source"
- [ ] 1.3 `osdb-org-front-matter`

## 2. Tests, red first

- [ ] 2.1 `tests/el/orgsyndb-tests.el` with its fixture helpers: copies
  of the test collection and the demo, a fixed current time, a stub
  program that records its arguments, a `browse-url` recorder
- [ ] 2.2 Package files, program, turning the mode on, collection data
- [ ] 2.3 Completion in Markdown procedures, Org procedures, sequences
  and compound files; inserting a compound
- [ ] 2.4 Definitions and references; documentation at point
- [ ] 2.5 Language variants
- [ ] 2.6 Problem locations; diagnostics while typing; validation on
  save; validation buffer; diagnostics front end
- [ ] 2.7 Timestamps on save
- [ ] 2.8 New procedure and new compound
- [ ] 2.9 Preview, PDF, structure window, command menu
- [ ] 2.10 `tests/test_elisp.py`: the package suite and the byte
  compilation of every `emacs/*.el`

## 3. Implementation

- [ ] 3.1 `emacs/orgsyndb.el`: package headers, options, the program,
  collection roots and file kinds, `orgsyndb-mode` and
  `global-orgsyndb-mode`, the index and the Org records
- [ ] 3.2 Completion at point and `orgsyndb-insert-compound`
- [ ] 3.3 The `xref` backend and the `eldoc` function
- [ ] 3.4 Variants: visit and create a translation
- [ ] 3.5 Problem locations, the Flymake backend, validation on save,
  `orgsyndb-validate`
- [ ] 3.6 `emacs/orgsyndb-flycheck.el`
- [ ] 3.7 Timestamps through `time-stamp`
- [ ] 3.8 New procedure, new compound
- [ ] 3.9 Serve, preview, preview on save, PDF
- [ ] 3.10 The structure window
- [ ] 3.11 `orgsyndb-dispatch` and the key binding

## 4. Documents

- [ ] 4.1 README: installing the package from the checkout (load path,
  a local recipe, `package-vc-install` with `:lisp-dir`) and what the
  mode does; pointers from the Org and Markdown authoring guides, in
  both languages (doc writer)

## 5. Verification

- [ ] 5.1 Full suite green, the ERT suites included
- [ ] 5.2 By hand in the owner's Emacs: completion through Corfu,
  Flymake diagnostics, `M-.`, the structure window and a preview in
  the browser, on a copy of the demo
- [ ] 5.3 `openspec validate emacs-mode --strict`
