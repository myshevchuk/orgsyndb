## MODIFIED Requirements

### Requirement: Completion in Markdown procedures
The mode SHALL put `orgsyndb-completion-at-point` on the buffer's `completion-at-point-functions`. In a buffer of kind `md-procedure`, it offers completions only inside the `+++` front matter:
- At the start of a line, while point follows nothing but the letters, digits and underscores of a key: the schema's top-level procedure keys and the declared procedure field keys that the front matter does not set yet, each annotated `required` when the schema requires it, or with its label when it is a declared field.
- Inside a double-quoted string that is the value, or an entry of the array value, of a key, the values of that key. The key is the innermost one whose value encloses the string, so that `compound` inside a `products` table and `substrates` inside a `scope` entry count as themselves:
  - `status`: the statuses; `language`: the languages;
  - `reaction_types`: the collection's reaction types, annotated with their labels;
  - `tags`: the tags that the collection's procedures use; `authors`: the user names of the index's accounts, each annotated with its name; `checked_by`: the names that the procedures use under that key;
  - `substrates` and `compound`: the registry's compound keys, annotated with name and formula;
  - `scheme_image`: `structures/<name>` for each `.svg` or `.png` file directly in the collection's `static/structures/`;
  - a declared `choice` field: the values of its vocabulary, annotated with the labels of the value's ancestors and its own, outermost first, joined by ` › `.
- After `<key> = ` for a declared `boolean` field: `true` and `false`.

Elsewhere, and in the body, it returns nil, so that other completion functions run. Tags and names in use come from the index for Markdown procedures and from `orgsyndb-procedures` for Org sources.

#### Scenario: Status
- **WHEN** an ERT test, in a buffer visiting `md/procedures/OSDB-0002-aspirin.md` of a copy of the test collection, puts point after `d` in `status = "d"` and calls `orgsyndb-completion-at-point`
- **THEN** the completions of its table for the text before point are `("draft")`

#### Scenario: Reaction type
- **WHEN** the test does the same inside `reaction_types = ["est"]`
- **THEN** the completions are `("esterification")`, annotated with text containing `Esterification`

#### Scenario: Compound of a product
- **WHEN** the test does the same inside `products = [{ compound = "acetyls", yield_percent = 75 }]`
- **THEN** the completions are `("acetylsalicylic-acid")`, annotated with text containing `Acetylsalicylic acid`

#### Scenario: Declared choice
- **WHEN** the test does the same inside `project = "first"`
- **THEN** the completions are `("first-year-practical")`, annotated with text containing `Teaching › First-year practical`

#### Scenario: Keys not yet set
- **WHEN** the test inserts a new line `sc` before the closing `+++` and calls the function with point after `sc`
- **THEN** the completions are `scheme_image` and `scope`, and not `scale`, which the file sets

#### Scenario: Nothing in the body
- **WHEN** the test calls the function with point in the text of the Summary section
- **THEN** it returns nil
