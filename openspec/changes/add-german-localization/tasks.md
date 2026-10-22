## 1. Site

- [x] 1.1 `site/hugo.toml`: languages, default language at the root, no
      `/en/` redirect (D1).
- [x] 1.2 `site/i18n/en.toml` and `de.toml`; every layout string through
      `T`; status and decimal partials; `lang` on `<html>` (D5).
- [x] 1.3 German site pages `site/content/**/_index.de.md`, `search.de.md`,
      `procedures-by-date.de.md`, and German titles for tags and authors.
- [x] 1.4 Language switch in the header; cross-language precursor and
      used-in links (D6).
- [x] 1.5 `label_de` for every reaction type (D5).
- [x] 1.6 Copy-button messages from data attributes; footer text in the
      per-page `@page` rule (D5).

## 2. Tools

- [x] 2.1 `validate.py`: language from the file name, German sections,
      IDs unique per language, translation checks, decimal comma in
      `scale`, `label_<lang>` in the vocabulary (D2–D4).
- [x] 2.2 `export.el`: export file name with `.md`, keeping the language
      code (D2).
- [x] 2.3 `pipeline.py`: PDF jobs of translations, German slugs,
      `new --lang` (D8); `tools/orgsyndb new --lang`.

## 3. Content

- [x] 3.1 German translations of the eight samples.
- [x] 3.2 `templates/procedure.de.org` and `templates/procedure.de.md`.

## 4. Tests

- [x] 4.1 Harness: content, pages, PDFs and searches per language.
- [x] 4.2 `tests/test_localization.py`: validator, stubs, templates, PDF
      jobs, site configuration, strings and labels.
- [x] 4.3 `tests/test_localization_integration.py`: German shell, language
      switch, German panel, German lists and search, partial translation.
- [x] 4.4 Sample tests read German tables and summaries.

## 5. Docs

- [x] 5.1 README, `docs/SCHEMA.md`, both authoring guides: translations and
      `new --lang de`.
- [x] 5.2 `docs/AUTHORING.de.md`, `docs/AUTHORING-ORG.de.org`,
      `docs/SCHEMA.de.md`.
- [x] 5.3 `docs/DECISIONS.org`: the localization decisions.
- [ ] 5.4 Owner's review of the German texts and a build on Fedora 44.
