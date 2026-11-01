## MODIFIED Requirements

### Requirement: Vocabularies
A vocabulary SHALL be the file `vocabularies/<name>.toml` in the directory of the collection's `orgsyndb.toml`, where `<name>` matches `^[a-z0-9]+(-[a-z0-9]+)*$`. Each top-level key of the file is a value of the vocabulary and matches the same pattern. Its table holds:
- `label`: required non-empty string, the value's name on an English site;
- `label_de`: optional non-empty string, its name on a German site, which shows `label` when it is absent;
- `parent`: optional, another value of the same vocabulary, under which this value is filed.

Following `parent` from any value ends at a value without one, a top-level value; the values passed on the way are the value's ancestors, and no value is its own ancestor. An entry holds no other key, and a vocabulary has at least one value. A vocabulary that no declaration names is not read, apart from `reaction-types`, the collection's reaction types, which the validator always reads (reaction-types "Reaction-type vocabulary").

#### Scenario: Values at every level
- **WHEN** a field-declaration run sets `chemical_class = ["carbonyl-compounds", "ketones"]` and `storage = "fridge"` in `ethyl-acetate.toml`
- **THEN** it exits 0 and prints nothing to stdout
