## MODIFIED Requirements

### Requirement: Procedure variants
A procedure file's name MAY carry a language code, `de` or `en`, before its suffix: `OSDB-0001-x.de.md`, `OSDB-0001-x.en.org`. Files with the same `id` are variants of one procedure; an ID may occur once per code and once without one. Every variant SHALL have the same base name (the name without code and suffix) and the same value, or absence, of `status`, `reaction_types`, `tags`, `products`, `substrates`, `scope`, `scheme_image` and every procedure field the collection declares (procedure-fields "Procedure field declarations") as the reference variant, where `scope` is compared without each entry's `note`, which a translation translates: the untagged file, else the `.de` file. Numbers compare by value, so `85` and `85.0` agree; other values compare by value and type. A mismatch is an error on the other variant, under the field's name (`file_name` for the base name), naming the reference's path. Any other field, and the body, may differ.

#### Scenario: A translation shares its ID and facts
- **WHEN** a run examines the baseline as `OSDB-0100-baseline.md` and, as `OSDB-0100-baseline.de.md`, the baseline with German headings and a different title, hazards, authors and `scale = "25,0 mmol"`
- **THEN** it exits 0 and prints nothing
- **AND** when the German file instead changes a product's `yield_percent`, `status` or `tags`, or adds `substrates`, it reports an error under `products`, `status`, `tags` or `substrates` on the German file, naming `OSDB-0100-baseline.md`

#### Scenario: A translation shares its ID and facts (integer and float)
- **WHEN** a run examines an untagged file whose product has `yield_percent = 85`, and its `.de` variant with `85.0`
- **THEN** it exits 0 and prints nothing, while `yield_percent = true` in the variant is still an error

#### Scenario: A translation shares its ID and facts (no untagged file)
- **WHEN** a run examines `OSDB-0100-baseline.de.md` and an `OSDB-0100-baseline.en.md` whose product has a different `yield_percent`
- **THEN** it reports exactly one error, field `products`, on the `.en` file, naming `OSDB-0100-baseline.de.md`

#### Scenario: Variants share a base name
- **WHEN** a run examines `OSDB-0100-baseline.md` and `OSDB-0100-other.de.md` with the same ID
- **THEN** it reports exactly one error, field `file_name`, on the German file, containing `OSDB-0100-baseline.de.md`

#### Scenario: A translation shares its declared fields
- **WHEN** a procedure-field run (procedure-fields "Procedure field fixture") sets `funding = "first-year-practical"` in `OSDB-0100-baseline.md` and adds `OSDB-0100-baseline.de.md`, a copy of it whose eight section headings are the German ones and whose `funding` is `"research"`; and a second such run gives the German copy no `funding` key
- **THEN** each reports exactly one error, on the German file, field `funding`, containing `OSDB-0100-baseline.md`
