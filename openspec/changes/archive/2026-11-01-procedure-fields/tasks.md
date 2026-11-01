## 1. Tests and fixtures, red first

- [x] 1.1 Validator fixture `tests/fixtures/procedure-fields/` and the
  procedure-field run; declarations accepted, facets, a key shared with
  a compound field; the configuration errors (options a procedure field
  does not take, reserved keys, a key declared twice, a single table, a
  missing vocabulary, `fields.reagent`)
- [x] 1.2 Validator values: declared values pass, pattern, quoted number,
  unknown choice value, required on a specific and a general procedure,
  uniqueness across procedures and not across variants, a declared key
  that is no unknown field, variants sharing declared values
- [x] 1.3 Field data: `procedure` in both languages; `procedure` empty
  for the compound fixture and for a missing settings file
- [x] 1.4 Test collection: `orgsyndb.toml` with the procedure
  declarations, `vocabularies/projects.toml`, and every procedure's
  values, as the demo will hold them; the demo's declarations,
  vocabulary and values
- [x] 1.5 Site: the declared fields in the metadata panel (OSDB-0002,
  the canonical order on every page, German); the declared facets in
  the procedure catalogues' controls and rows
- [x] 1.6 Org export: the demo's Org samples export their declared
  values with their types; a quoted integer is no text

## 2. Implementation

- [x] 2.1 `tools/validate.py`: `fields.procedure` declarations, reserved
  keys, procedure value checks, uniqueness per procedure, variants
  sharing declared values, declared keys exempt from `unknown field`
- [x] 2.2 `tools/pipeline.py`: `procedure` in the field data
- [x] 2.3 Site: the metadata panel, the catalogue facets and the rows'
  `data-<key>` attributes
- [x] 2.4 Demo collection: `orgsyndb.toml`, `vocabularies/projects.toml`
  and every sample procedure, Org and Markdown, in both languages, as
  the test collection's

## 3. Verification

- [x] 3.1 Full suite: 990 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: site-catalogue "Filtering procedures by a declared
  field" on the German demo build, light and dark, at 1280 and 500 CSS
  pixels; the German panel of a procedure with declared fields. Driven
  through Marionette in headless Firefox: Forschung narrowed nine
  procedures to four, Ja under Schutzgas to OSDB-0004 and OSDB-0007,
  with counts and chips following; the reload kept
  `/procedures/?project=research&inert_atmosphere=true` and Back
  restored both earlier addresses. Projekt indents its second level;
  at 500 pixels the facets open from the toggle. The panel of
  OSDB-0002 reads Laborjournal AE-1/2, Projekt Lehre › Grundpraktikum,
  Arbeitszeit 2,5 h and Schutzgas Nein between Autoren and Erstellt

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`,
  the two Markdown and the two Org authoring guides
- [x] 4.2 Codex reviewer: one test passed on a reserved-key error
  instead of its vocabulary errors; corrected
- [x] 4.3 Archive
