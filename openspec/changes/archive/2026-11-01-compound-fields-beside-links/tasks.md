## 1. Tests and fixtures, red first

- [x] 1.1 Validator: `beside` accepted on a `text` and a `number`
  compound field; refused on a `boolean` and a `choice` compound field
  and on a procedure field
- [x] 1.2 Pipeline: `fields_data` gives `beside` for `text` and `number`
  compound fields only, with its default
- [x] 1.3 Site: the note after every `a.compound` of a theme build; none
  for a compound that sets no `beside` field; a number with its unit and
  decimal comma on a German build; markup in a value is text; the
  stylesheet rule
- [x] 1.4 Demo: the declarations of `item_number` and `short_name` carry
  `beside`
- [x] 1.5 Existing tests that compare the whole text of a container of
  `a.compound` links move to the new contract, keeping their checks of
  each link's text: the English panel's `Product` and `Starting
  materials` (`tests/test_theme_integration.py`), the German starting
  materials (`tests/test_localization_integration.py`), the scope
  table's substrate and product cells (`tests/general_support.py`), the
  sequence scheme's compound items (`tests/test_sequence_pages.py`,
  `tests/sequence_support.py`), and any other the suite turns up

## 2. Implementation

- [x] 2.1 `tools/validate.py`: `beside` for `text` and `number`; withheld
  from procedure fields
- [x] 2.2 `tools/pipeline.py`: `beside` in the compound field data
- [x] 2.3 Site: `compound-link.html` writes the note; `base.css` styles it
- [x] 2.4 Demo: `examples/demo/orgsyndb.toml` and
  `tests/fixtures/collection/orgsyndb.toml`

## 3. Documents

- [x] 3.1 `docs/SCHEMA.md` and `docs/SCHEMA.de.md`: `beside` among the
  compound declaration options and among the options a procedure field
  withholds; any other document that lists them (doc writer)

## 4. Verification

- [x] 4.1 Full suite: 1049 passed and 1 skipped (`caddy`)
- [x] 4.2 Browser: a demo build shows the notes in a metadata panel, a
  scope table and a sequence page, in both colour schemes. Driven through
  Marionette in headless Firefox on a build of the demo, which builds
  in German: the panel of OSDB-0002 read Acetylsalicylsäure (CH-0010,
  ASA), Salicylsäure (CH-0020) and Essigsäureanhydrid (CH-0007, Ac2O);
  the scope table of OSDB-0009, the scheme of SEQ-0001 and the targets
  of `/sequences/` carried a note after every compound link; every note
  had the computed colour of `--muted`, `#555555` light and `#a8a8a3`
  dark
