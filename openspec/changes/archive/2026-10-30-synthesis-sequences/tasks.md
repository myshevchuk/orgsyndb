## 1. Tests and fixtures, red first

- [x] 1.1 Fixtures: `tests/fixtures/sequences/`,
  `tests/fixtures/sequences-procedures/`,
  `tests/fixtures/sequences-invalid/file-name/`; the sequence fixture
  and variant runs
- [x] 1.2 Validator: sequence files and names, fields, steps and
  entries, continuity, variants, `--sequences` and its default, report
  format and summary
- [x] 1.3 Test collection: the two demo sequences and their German
  variants, as the demo will hold them
- [x] 1.4 Pipeline: the overlay's seventh mount, staging the chosen
  sequence variants, `init` creating `md/sequences/`, `validate`'s
  arguments
- [x] 1.5 Samples: the demo sequences
- [x] 1.6 Site: navigation, sequence pages and directory, key facts and
  overall yield, scheme, steps, the panel's `Sequences`, the compound
  page's sequences, the home page's browse list, German strings
- [x] 1.7 Template: `templates/sequence.md`

## 2. Implementation

- [x] 2.1 `tools/validate.py`: sequences
- [x] 2.2 `tools/pipeline.py` and `tools/orgsyndb`: staging, overlay,
  `init`, `validate`
- [x] 2.3 Site: content page and layouts for `/sequences/`, the panel,
  the compound page, the header, the home page, i18n, styles
- [x] 2.4 Demo collection and `templates/sequence.md`

## 3. Verification

- [x] 3.1 Full suite: 665 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: both demo sequences and the directory, at 1280 and
  500 CSS pixels, light and dark; a sequence page printed. Checked in
  headless Firefox on the German demo build: SEQ-0002 shows Stufen 2,
  Gesamtausbeute 77 %, the scheme with a plus between its starting
  materials and Eintrag 1 in its steps; SEQ-0001 at 500 in the dark
  scheme runs down the page with downward arrows; WeasyPrint prints
  SEQ-0001 on one page with its scheme, steps and notes

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA*.md`,
  `docs/AUTHORING*.md`, `docs/AUTHORING-ORG*.org`
- [x] 4.2 Codex reviewer: two findings, taxonomy keys and double rounding;
  both fixed
- [x] 4.3 Archive
