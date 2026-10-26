## MODIFIED Requirements

### Requirement: Stubs in a language
`tools/orgsyndb new` SHALL accept `--lang LANG`, where `LANG` is `de` or `en`; any other value is a usage error (exit 2) naming `--lang`. With `--lang`, it fills `templates/procedure.<LANG>.org` (or `.md` with `--md`), the English template for `en`, exactly as it fills the English template, and names the file `OSDB-NNNN-<slug>.<LANG>.org` or `.md`. Without `--lang` it behaves as before. The slug of a German title has `ä`, `ö`, `ü`, `ß` (and capitals) written out as `ae`, `oe`, `ue`, `ss` before the ASCII folding. The German templates carry the same keyword or anchor lines as the English ones, German comments and the German section headings. Once their placeholders are filled, the German Markdown template validates cleanly, and the German Org template passes the export's Org checks (org-export "Org sources and their problems").

#### Scenario: German stub
- **WHEN** a test calls `new_procedure` with `language` `de` at `2026-10-19T17:42:05+02:00` for the Org title `Größe Säure`, and then for the Markdown title `Ölsäure`, in an empty collection
- **THEN** it creates `org/procedures/OSDB-0001-groesse-saeure.de.org` and `md/procedures/OSDB-0002-oelsaeure.de.md`
- **AND** the Org stub has `#+TITLE: Größe Säure`, `#+CREATED: [2026-10-19 Mon 17:42:05]` and `* Zusammenfassung`, and the Markdown stub validates without any problem line

#### Scenario: German templates
- **WHEN** a test fills `templates/procedure.de.md` with `OSDB-0001` and validates it as `OSDB-0001-vorlage.de.md`, and compares the keyword lines of the two Org templates
- **THEN** the run is clean, the Markdown headings are the eight German sections in order, and both Org templates have the same keyword lines in the same order

#### Scenario: German Org template passes the Org checks
- **WHEN** an ERT test copies `templates/procedure.de.org` to a temporary directory as `OSDB-0001-vorlage.de.org`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, and calls `osdb-org-examine` on that directory
- **THEN** it returns no problem and one source, whose stem is `OSDB-0001-vorlage.de`, so that its export is named `OSDB-0001-vorlage.de.md`
