## MODIFIED Requirements

### Requirement: New procedure and new compound
`orgsyndb-new-procedure` SHALL read a title and, with a prefix argument, a format, `org` or `md`, and a language, `none`, `de` or `en`; without one it uses `org` and `none`. It runs `orgsyndb -C <collection> new`, adding `--md` for Markdown and `--lang <code>` for a language, then the title's words, and visits the file whose collection-relative path the program prints. When the run fails, it signals an error holding the program's error output.

`orgsyndb-new-compound` SHALL read a key, which must be a lowercase hyphenated slug that no compound file uses, and then, in the order of the application's compound template, `name`, the optional `name_de`, `formula`, `mw` as a number, `smiles`, and the optional `cas` and `structure_image`, empty input leaving an optional value out and the image being completed from `static/structures/`; then each declared compound field with `required = true`, in declared order: a choice with completion over its vocabulary's values, several for a `multiple` field; a boolean as yes or no; a number as a number; a text as text. It writes `compounds/<key>.toml` holding one `<key> = <value>` line per value read, in that order, with TOML strings, numbers, booleans and arrays of strings, and visits it.

#### Scenario: New Markdown procedure in German
- **WHEN** an ERT test sets `orgsyndb-program` to a stub that records its arguments, creates `md/procedures/OSDB-0010-ethylacetat.de.md` and prints that path, and calls `orgsyndb-new-procedure` with a prefix argument and the answers `md`, `de` and `Ethylacetat herstellen`
- **THEN** the stub received `-C <collection> new --md --lang de Ethylacetat herstellen` as separate arguments, and the current buffer visits `md/procedures/OSDB-0010-ethylacetat.de.md`

#### Scenario: New compound with declared fields
- **WHEN** an ERT test calls `orgsyndb-new-compound` in a copy of the demo collection with the answers `ethanol`, `Ethanol`, `Ethanol`, `C2H6O`, `46.07`, `CCO`, `64-17-5`, an empty structure image, `alcohols` and `reagents`
- **THEN** `compounds/ethanol.toml` holds exactly the lines `name = "Ethanol"`, `name_de = "Ethanol"`, `formula = "C2H6O"`, `mw = 46.07`, `smiles = "CCO"`, `cas = "64-17-5"`, `chemical_class = ["alcohols"]` and `group = "reagents"`, in that order, and `orgsyndb index` of the copy lists `ethanol` without an `error`
