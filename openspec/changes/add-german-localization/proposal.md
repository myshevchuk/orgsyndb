## Why

The group works in Germany, and several co-workers read and write German
more easily than English. Today every interface string of the site is
English, the procedure schema accepts only English section headings, and
the demo collection, the templates and the authoring guides exist in
English only. A co-worker can neither browse the site in German nor write
a procedure in German that the validator accepts without warnings.

## What Changes

- **Bilingual site.** The site is built in English, at the root as
  before, and in German, under `/de/`. Every interface string comes from
  `site/i18n/en.toml` or `site/i18n/de.toml`; reaction-type labels gain a
  German `label_de` in the vocabulary. A page that has a translation links
  to it from a language switch in the site header.
- **Translated procedures.** A procedure's language is a code in its file
  name: `OSDB-0001-salicylic-acid.org` is English, and
  `OSDB-0001-salicylic-acid.de.org` (or `.de.md`) its German translation.
  A translation shares the original's ID, base name and language-neutral
  facts (status, reaction type, tags, yield, precursors, structure image,
  product formula, molecular weight, SMILES and CAS number); the validator
  checks that. An ID may be used once per language. A German-only
  procedure, without an English file, is allowed.
- **German sections.** German procedures use German section headings
  (`Zusammenfassung` … `Literatur`) and German Reagents columns
  (`Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv.`). `scale` accepts a
  decimal comma.
- **Search and print.** Pagefind indexes each language separately, so a
  German search finds German pages. A translation prints to
  `pdf/<stem>.de.pdf` with a German page footer (`Seite N von M`).
- **German stubs.** `orgsyndb new --lang de` writes a German stub from
  `templates/procedure.de.org` or `templates/procedure.de.md`, named
  `OSDB-NNNN-<slug>.de.<ext>`, with umlauts written out in the slug.
- **Demo collection.** Each of the eight samples gets a German translation.
- **Docs.** German versions of the two authoring guides and of the schema
  reference: `docs/AUTHORING.de.md`, `docs/AUTHORING-ORG.de.org` and
  `docs/SCHEMA.de.md`. The README stays English and describes the feature.

Nothing changes for an English-only collection except that its site also
has an (empty) German section and a language switch on pages that exist
in both languages.

## Capabilities

### New Capabilities

- `localization`: site languages, interface strings, translations and
  their checks, German stubs, the language switch and cross-language links.

### Modified Capabilities

- `procedure-schema`: file names with a language code, IDs unique per
  language, German body sections, decimal comma in `scale`, German labels
  in the vocabulary.
- `site-build`: German pages under `/de/`, `lang` per page, one search
  index per language.
- `site-theme`: the page shell in the page's language.
- `print-layout`: the page footer in the page's language.
- `sample-procedures`: German translations of the samples, and the rules
  that read them.

## Impact

- Code: `tools/validate.py`, `tools/pipeline.py`, `tools/orgsyndb`,
  `tools/export.el` (export file name keeps the language code).
- Site: `site/hugo.toml`, `site/i18n/`, `site/content/*.de.md`, every
  layout with a visible string, `site/assets/js/site.js`,
  `site/data/reaction_types.toml`.
- Data: eight translations in `examples/demo/`, two German templates.
- Tests: the harness reads content and pages per language; new
  `tests/test_localization.py` and `tests/test_localization_integration.py`.
- Docs: README, schema, both guides, their German versions, the decision
  record.
- Dependencies: none.
