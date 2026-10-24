## 1. Site

- [x] 1.1 `site/hugo.toml`: `locale = "de"`, no `languages` table (D1).
- [x] 1.2 `site/i18n/en.toml` and `de.toml`; every layout string through
      `T`; site page titles by `title_key`; status and decimal partials;
      `lang` on `<html>` and on a procedure in another language (D4, D6).
- [x] 1.3 `label_de` for every reaction type; lists sorted by label (D6).
- [x] 1.4 Copy-button messages from data attributes; footer text in the
      per-page `@page` rule (D6).

## 2. Tools

- [x] 2.1 `validate.py`: language codes in file names, German sections,
      IDs unique per code, variant checks, the `language` field, decimal
      comma in `scale`, `label_<lang>` in the vocabulary (D3–D5).
- [x] 2.2 `export.el`: export file name with `.md`, keeping the code (D2).
- [x] 2.3 `pipeline.py`: `site_language`, `choose_variants`,
      `stage_content`, the overlay's language and staged mount, PDF jobs of
      the chosen files, German slugs, `new --lang` (D1, D2, D7);
      `tools/orgsyndb` builds from the staged files.

## 3. Content

- [x] 3.1 German variants of the eight samples.
- [x] 3.2 `templates/procedure.de.org` and `templates/procedure.de.md`.

## 4. Tests

- [x] 4.1 Harness: builds in a chosen locale, published variants per ID.
- [x] 4.2 `tests/test_localization.py`: validator, variant choice and
      staging, stubs, templates, site locale, strings and labels.
- [x] 4.3 `tests/test_localization_integration.py`: German shell, titles,
      published variants, panel, labels, search, partial translation, the
      `lang` marking, German PDFs.
- [x] 4.4 Sample tests read German tables and summaries.

## 5. Docs

- [x] 5.1 README, `docs/SCHEMA.md`, both authoring guides.
- [x] 5.2 `docs/AUTHORING.de.md`, `docs/AUTHORING-ORG.de.org`,
      `docs/SCHEMA.de.md`.
- [ ] 5.3 Owner's review of the German texts and a build on Fedora 44.
