## Why

The group works in Germany, and several co-workers read and write German
more easily than English. Today every interface string of the site is
English, the procedure schema accepts only English section headings, and
the demo collection, the templates and the authoring guides exist in
English only. A co-worker can neither use the site in German nor write a
procedure in German that the validator accepts without warnings.

## What Changes

- **One site language, German by default.** `locale` in `site/hugo.toml`
  (`"de"` or `"en"`, default `"de"`) sets the site's language. Every
  interface string comes from `site/i18n/de.toml` or `site/i18n/en.toml`;
  reaction-type labels gain a German `label_de`; site page titles come
  from the strings. There is no language switch and no second site.
- **Procedure variants.** A procedure file's name may carry a language
  code, `.de` or `.en`, before its suffix. Files with one ID are variants
  of one procedure. Every procedure is published once, in the variant
  that suits the site: the one tagged with the site's language, else the
  untagged one, else one tagged with the other language. The build stages
  the chosen files in `build/content/procedures/` for Hugo.
- **Variant checks.** Variants share their ID, base name and
  language-neutral facts (status, reaction type, tags, yield, precursors,
  structure image, product formula, molecular weight, SMILES and CAS
  number); the validator compares each with the untagged file, else the
  `.de` file. An ID may occur once per code and once without one.
- **Language field.** An optional front-matter field `language` (`"de"`
  or `"en"`) states a procedure's language. It must match the file name's
  code; the build adds it to tagged files; it picks the section names of
  an untagged file; a page whose procedure is in another language than
  the site marks it with `lang`.
- **German sections.** German procedures use German section headings and
  Reagents columns; an untagged file may use either set. `scale` accepts
  a decimal comma.
- **Search and print.** Pagefind indexes the site in its language. PDFs
  are named after the published file (`pdf/<stem>.de.pdf`) and a German
  site prints `Seite N von M`.
- **Stubs.** `orgsyndb new --lang de|en` writes a stub from that
  language's template (`templates/procedure.de.org`, `.de.md`), named
  with the code.
- **Demo collection.** Each of the eight samples gets a German variant.
- **Docs.** German versions of the two authoring guides and of the schema
  reference. The README stays English.

## Capabilities

### New Capabilities

- `localization`: the site language, interface strings, variants and
  their choice and checks, the language field, German stubs and PDFs.

### Modified Capabilities

- `procedure-schema`: file names with a language code, IDs unique per
  code, German body sections, decimal comma in `scale`, the `language`
  field, German labels in the vocabulary.
- `site-build`: the locale, the staged content mount, `lang` per page.
- `site-theme`: the page shell in the site's language.
- `print-layout`: the page footer in the site's language.
- `sample-procedures`: German variants of the samples, and the rules that
  read them.

## Impact

- Code: `tools/validate.py`, `tools/pipeline.py`, `tools/orgsyndb`,
  `tools/export.el` (export file name keeps the language code).
- Site: `site/hugo.toml`, `site/i18n/`, `site/content/` page titles,
  every layout with a visible string, `site/assets/js/site.js`,
  `site/data/reaction_types.toml`.
- Data: eight German variants in `examples/demo/`, two German templates.
- Tests: the harness builds in a chosen locale and reads the published
  variants; new `tests/test_localization.py` and
  `tests/test_localization_integration.py`.
- Docs: README, schema, both guides, their German versions, the decision
  record.
- Behaviour: the shipped site is German. An owner who wants English sets
  `locale = "en"` in `site/hugo.toml`.
- Dependencies: none.
