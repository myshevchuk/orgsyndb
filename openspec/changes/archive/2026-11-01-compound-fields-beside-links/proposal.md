## Why

A procedure names its compounds by name only: the metadata panel and
the scope table link each product and starting material to its compound
page. A group that keeps an inventory looks a compound up by its item
number, and a short name such as `Ac2O` is how a bench chemist writes
it. Those values are already declared compound fields, but the site
shows them only on the compound's own page and in the compound
directory, so finding the bottle for a procedure's starting material
takes a trip to each compound page.

## What Changes

- A compound field declaration of type `text` or `number` takes
  `beside`, an optional boolean, default `false`. Every other type, and
  every procedure field, refuses it as a configuration error.
- Wherever the site links a compound (`a.compound`), it writes the
  values of the compound's `beside` fields after the link, as
  `(<value>, <value>)` in declared order, each written as the compound
  page writes it, in a `span.compound-beside`. A compound that sets none
  of them gets no note. That covers the metadata panel's products and
  starting materials, the scope table of a general procedure, the
  sequence scheme and the sequence directory.
- The field data staged for the site carries `beside` for `text` and
  `number` compound fields.
- The demo collection declares `beside = true` on `item_number` and
  `short_name`, so every compound link of the demo reads like
  `Acetic anhydride (CH-0007, Ac2O)`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `compound-fields`: the `beside` option, its configuration error, its
  field data, and a new requirement for the note after a compound link.
- `procedure-fields`: a procedure field takes no `beside`.
- `site-theme`: the metadata panel's compound links carry their notes.
- `general-procedures`: the scope table's compound links carry their
  notes.
- `sample-procedures`: the demo declares `beside` on `item_number` and
  `short_name`.

## Impact

- Code: `tools/validate.py` (the option and its refusal),
  `tools/pipeline.py` (`fields_data`),
  `site/layouts/_partials/compound-link.html`, `site/assets/css/base.css`.
- Files: `examples/demo/orgsyndb.toml` and its byte-identical copy
  `tests/fixtures/collection/orgsyndb.toml`.
- Docs: `docs/SCHEMA.md` and `docs/SCHEMA.de.md`, which list the
  declaration options, and any other document that lists them.
- The metadata panel lies inside the search index's body, so a
  procedure's search text gains the `beside` values of the compounds it
  links.
