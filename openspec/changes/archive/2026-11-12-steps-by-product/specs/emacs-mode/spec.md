## MODIFIED Requirements

### Requirement: Completion in sequences
`orgsyndb-completion-at-point` SHALL offer, in a buffer of kind `sequence`, inside the front matter: at the start of a line, the sequence keys that the front matter does not set yet; inside the string of `target`, the compound keys; inside the string of `procedure` in a step, the procedure IDs, each annotated with its title; inside the string of `product` in a step, the product keys of the entries of the general procedure that the step's `procedure` names, each once, in file order, each annotated with the numbers of the entries it is a product of, and nothing when the step names a specific procedure; and inside a list of `substrates` or `products` in a step, the compound keys.

#### Scenario: Step procedure
- **WHEN** an ERT test, in a buffer visiting `md/sequences/SEQ-0001-aspirin-from-wintergreen.md` of a copy of the demo collection, calls `orgsyndb-completion-at-point` with point after `OSDB-000` inside `steps = [{ procedure = "OSDB-000" }]`
- **THEN** the completions are the nine IDs `OSDB-0001` to `OSDB-0009`, and `OSDB-0007` is annotated with text containing `Ethyl cinnamate`

#### Scenario: Step product
- **WHEN** the test does the same with point inside the quotes of `product = ""` in `{ procedure = "OSDB-0009", product = "" }`
- **THEN** the completions are `("1-biphenyl-4-yl-ethanol" "1-phenylethanol" "1-4-bromophenyl-ethanol")`, and the first is annotated with text containing `1`

#### Scenario: Step product of an Org general procedure
- **WHEN** an ERT test copies `tests/fixtures/export/OSDB-0909-scope-table.org` into `org/procedures/` of a copy of the demo collection and does the same in `{ procedure = "OSDB-0909", product = "" }`
- **THEN** the completions are `("ethyl-acetate" "propyl-acetate" "benzyl-acetate" "methyl-benzoate")`, and `propyl-acetate` is annotated with text containing `1`
