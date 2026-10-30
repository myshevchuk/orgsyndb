## Why

A synthesis takes several procedures in a row: the product of one is
the starting material of the next. The site now knows which procedures
make and use each compound, but not which of the possible routes the
group runs, in which order, with which entry of a general procedure,
and what the whole route yields. That knowledge lives in people's heads
or in prose.

## What Changes

- A collection gains synthesis sequences: Markdown files
  `md/sequences/SEQ-NNNN-short-slug.md` whose front matter names an ID,
  title, dates, a target compound and at least two steps, each
  a procedure and, for a general procedure, one of its entries. The
  body holds notes. A sequence may have a German and an English
  variant, published like a procedure's.
- The validator reads them with a new `--sequences` option, checks
  their fields, that each step's procedure exists and its entry is
  valid, that each step starts from a product of the step before, and
  that the target is a product of the last step. `tools/orgsyndb
  validate` passes `md/sequences`.
- The site publishes every sequence at `/sequences/<slug>/`: its key
  facts (steps, overall yield), a scheme of compounds and steps with
  structures, the steps with their procedures, and the notes; and a
  directory at `/sequences/`. Sequences join the navigation:
  Procedures, Compounds, Sequences, Help.
- A procedure's panel links the sequences it is a step of, and a
  compound page the sequences that make it.
- The demo collection gains two sequences, one of them through an
  entry of the demo's general procedure; `templates/sequence.md` is
  new.

## Capabilities

### New Capabilities

- `synthesis-sequences`: sequence files, fields, continuity, pages,
  links from procedures and compounds, and the template.

### Modified Capabilities

- `procedure-validation`: the `--sequences` option and the report.
- `collection`: `md/sequences/` in the layout and in `init`.
- `build-script`: the validator arguments of `validate`.
- `site-build`: the sequences mount.
- `site-theme`: the navigation and the panel's `Sequences` pair.
- `localization`: the German strings.
- `sample-procedures`: the demo sequences.

## Impact

- `tools/validate.py`, `tools/orgsyndb`, `tools/pipeline.py`.
- Site: layouts for `/sequences/`, the panel, compound pages, the
  header; i18n; styles.
- Content: `examples/demo/md/sequences/` and the test collection's;
  `templates/sequence.md`.
- Tests: validator, pipeline, theme, localization, samples.
- Docs: `README.md`, `docs/SCHEMA*.md`, `docs/AUTHORING*.md`,
  `docs/AUTHORING-ORG*.org`.
