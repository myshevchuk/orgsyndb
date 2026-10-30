# Procedure schema reference

This reference defines valid OrgSynDB procedures and compound records.
Use it to look up the exact spelling, type, and rule for a field, or to
interpret a message from
`tools/validate.py` or `orgsyndb export`.

A German version of this reference is [SCHEMA.de.md](SCHEMA.de.md).

A Markdown procedure starts with TOML front matter. TOML is the metadata
block between the opening and closing `+++` lines. The opening `+++` must be
the first line of the file. Text after the closing `+++` is the procedure
body.

In the tables below, a **string** is text in double quotes, an **array of
strings** is a comma-separated list in square brackets, and a **table** is a
group of named values, written inline in braces or under a table heading.
An **offset datetime** is an unquoted date and time with its UTC offset,
such as
`2026-10-19T17:42:05+02:00`.

## Identifiers, file names, and URLs

The procedure identifier has the exact form `OSDB-NNNN`, where `NNNN` is
four digits from `0001` through `9999`. For example, `OSDB-0001` is valid.
`OSDB-0000` is reserved for templates and is not a valid procedure
identifier. An identifier must be unique across all content roots passed
to the validator, except that the variants of one procedure in different
languages share it; see [Languages and variants](#languages-and-variants).

The source file name has this form:

```text
OSDB-NNNN-short-slug.md
OSDB-NNNN-short-slug.org
OSDB-NNNN-short-slug.de.md     (German variant)
OSDB-NNNN-short-slug.en.org    (English variant)
```

The `OSDB-NNNN` prefix must equal the procedure's `id`. The short slug after
the prefix contains lowercase letters or digits. It may contain single
hyphens between groups, as in `OSDB-0001-ethyl-acetate.md`. A language
code, `.de` or `.en`, may stand before the suffix; any other code is an
error.

The front-matter `slug` is not the short slug from the file name. It is
always the lowercase identifier: `OSDB-0001` becomes `osdb-0001`. This gives
the page the URL `/procedures/osdb-0001/`. Do not add a `url` field; the URL
is derived from `slug`.

The validator examines procedure files only at the top level of each root.
A subdirectory is an error. It silently skips dotfiles and `_index.md`. Any
other file with the wrong extension produces a warning and is ignored.

## Front-matter fields

Every required field must be present. A required string must contain
non-whitespace text. A required array described as non-empty must contain at
least one entry. Each entry in an array of strings must contain
non-whitespace text.

A procedure with `scope` is a **general procedure**: one method applied to
several substrates. A procedure without `scope` is a **specific procedure**.
The site derives the kind from `scope`; do not add a `kind` field.

### Required top-level fields

| Field | Meaning | TOML type | Required | Value rule | Example |
|---|---|---|---|---|---|
| `id` | The procedure identifier. | String | Yes | Must be `OSDB-0001` through `OSDB-9999` and unique across the validated content roots, except among the variants of one procedure. | `id = "OSDB-0001"` |
| `slug` | The value used in the procedure URL. | String | Yes | Must equal the lowercase `id` exactly. | `slug = "osdb-0001"` |
| `title` | The procedure heading, usually naming what it makes. | Non-empty string | Yes | Must not be empty. | `title = "Product Name"` |
| `date` | When the procedure was created. | Offset datetime | Yes | Must be unquoted. Its offset should be the Europe/Berlin offset in force at that instant. | `date = 2026-10-19T17:42:05+02:00` |
| `lastmod` | When the procedure was last changed. | Offset datetime | Yes | Must be unquoted, must not be earlier than `date`, and should use the Europe/Berlin offset in force at that instant. | `lastmod = 2026-10-19T17:42:05+02:00` |
| `authors` | Everyone who wrote the procedure. | Non-empty array of non-empty strings | Yes | Must contain at least one name. | `authors = ["A. Example"]` |
| `status` | The procedure's workflow state. | String | Yes | Must be exactly `draft`, `checked`, or `retired`. | `status = "draft"` |
| `reaction_types` | The controlled reaction category. | Array of strings | Yes | Must contain exactly one slug from the reaction-type vocabulary. | `reaction_types = ["esterification"]` |
| `tags` | Search terms for the procedure. | Non-empty array of strings | Yes | Every tag must contain lowercase letters or digits, with single hyphens between groups. | `tags = ["acid-catalysed"]` |
| `products` | The compounds made and their yields. | Non-empty array of tables | Only without `scope` | Every entry must contain `compound` and `yield_percent`, as described below. | `products = [{ compound = "ethyl-acetate", yield_percent = 85 }]` |
| `scale` | The amount of product the procedure makes; the typical scale for a general procedure. | String | Yes | Must contain a number, whitespace, and a unit token. The number may have a decimal point or a decimal comma. The unit vocabulary is not restricted. | `scale = "25 mmol"` |
| `hazards` | The main hazards. | Non-empty array of non-empty strings | Yes | Must contain at least one short description. | `hazards = ["Flammable liquid"]` |

A date with a non-Berlin offset is still an exact instant, so it produces a
warning rather than an error. A quoted datetime, a datetime without an
offset, or a bare date is an error. The validator compares `date` and
`lastmod` as instants, including their offsets.

### Products and starting materials

For a specific procedure, top-level `products` contains one table per product.
Each compound key must occur only once in the array. A procedure may have
several products, each with its own yield.

| Field | Meaning | TOML type | Required | Value rule | Example |
|---|---|---|---|---|---|
| `products[n].compound` | The product's key in the compound registry. | String | Yes | Must name an existing registry entry. | `compound = "ethyl-acetate"` |
| `products[n].yield_percent` | Isolated yield of this product in percent. | Integer or float | Yes | Must be finite and from 0 through 100, inclusive. Do not quote it or add `%`. A boolean is not a number. | `yield_percent = 85` |

Write the entries as inline tables, as in the procedure template:

```toml
products = [{ compound = "ethyl-acetate", yield_percent = 85 }]
```

You may also use TOML's `[[products]]` table headings, as the Org export
does. Keep those tables after all top-level fields: keys after a table
heading belong to that table.

For a specific procedure, the optional `substrates` array names the starting
materials by compound key. It may be empty. Every key must exist in the
registry, must occur only once, and must not also occur among the procedure's
products.

The site derives **Precursors** from other published procedures that make one
of these starting materials. It derives **Used in** from procedures that use
one of this procedure's products as a starting material. Both lists are ordered
by procedure ID and work across procedure languages. You do not write procedure
IDs for these links. For a general procedure, the site uses the products and
starting materials of every scope entry, each compound once in order of first
appearance. This also applies to the metadata panel, compound directory,
catalogue details and search, including SMILES matches.

### General procedures and scope entries

Use `scope` to record the substrates, products and yields of each application
of a shared method. It must be a non-empty array of tables, numbered from 1 in
their order. Omit top-level `products` and `substrates` entirely, even empty
arrays. Top-level `scale` remains required and gives the typical scale.

| Field | Meaning | TOML type | Required in each entry | Value rule | Example |
|---|---|---|---|---|---|
| `scope[n].substrates` | Starting materials for this entry. | Non-empty array of strings | Yes | Registry keys; none repeated or among this entry's products. | `substrates = ["acetophenone"]` |
| `scope[n].products` | Products and their isolated yields. | Non-empty array of tables | Yes | The same rules as top-level `products`, including `compound` and `yield_percent` in each product. | `products = [{ compound = "1-phenylethanol", yield_percent = 85 }]` |
| `scope[n].scale` | This entry's scale. | String | No | The same number-and-unit rule as top-level `scale`. | `scale = "5 mmol"` |
| `scope[n].time` | This entry's reaction time. | String | No | A number, whitespace and exactly `min`, `h` or `d`; a decimal point or comma is allowed. | `time = "30 min"` |
| `scope[n].temperature` | This entry's temperature in °C. | Integer or float | No | Must be finite, unquoted and not a boolean. Do not add a unit. | `temperature = 80` |
| `scope[n].note` | A comment on this entry. | Non-empty string | No | Must not be empty when present; may be translated. | `note = "Reflux"` |

Each entry is checked on its own. A compound may be a substrate of one entry
and a product of another. In Markdown, write `scope` as an array of inline
tables; the demo's
[OSDB-0009](../examples/demo/md/procedures/OSDB-0009-benzylic-alcohols.md)
shows three entries. For Org, use the [named scope table](#org-scope-table).

On the procedure page, **Scope** precedes **Summary**. Its columns are
**Entry**, **Starting materials**, **Products** and **Yield**. **Scale**,
**Time**, **Temperature** and **Note** appear only when some entry sets that
field. Compound names link to compound pages, and products with structure
images show small images. The key facts show the typical scale and the yield
range over all products of all entries, `<min>–<max> %`, or one percentage when
all yields are equal. A compound page's **Made by** list names each entry that
makes it: `<ID> <title> · entry <n> · <yield> % · <status>`. **Used in** and
directory counts include each procedure only once.

### Optional top-level fields

Omit an optional field when it does not apply.

| Field | Meaning | TOML type | Required | Value rule | Example |
|---|---|---|---|---|---|
| `substrates` | The starting materials of a specific procedure; forbidden at top level with `scope`. | Array of strings | No | Registry keys, with no duplicates and none among the products. | `substrates = ["ethanol"]` |
| `scope` | The entries of a general procedure. | Non-empty array of tables | No | Entry rules above; forbids top-level `products` and `substrates`. | See OSDB-0009. |
| `scheme_image` | A reaction-scheme image in the title block, replacing product structures. | String | No | Relative path under `structures/`, no `..` component, `.svg` or `.png`, existing under the static directory. A general procedure without it shows the placeholder. | `scheme_image = "structures/aryl-ketone-reduction.svg"` |
| `checked_by` | People who checked the procedure. | Array of non-empty strings | No | The array may be empty, but an entry may not be an empty string. | `checked_by = ["B. Example"]` |
| `references` | Literature references stored as metadata. | Array of non-empty strings | No | The array may be empty, but an entry may not be an empty string. | `references = ["Example, A. J. Fictitious Chem. 2020, 1, 1."]` |
| `ai_model` | The model that assisted with the procedure. | Non-empty string | No | Omit the field when no AI assisted. The value `"none"` is an error. | `ai_model = "example-model-1"` |
| `language` | The language the procedure is written in. | String | No | Must be `de` or `en`, and match the language code of the file name when it has one. | `language = "de"` |

## Compound registry

Store each compound once so several procedures and their translations can
refer to the same data. The collection's `compounds/` directory holds one
UTF-8 TOML file per compound, named `<key>.toml`. The key is the compound's
identity: two procedures name the same compound exactly when they use the
same key. Structures are not compared to establish identity.

A key matches `[a-z0-9]+(-[a-z0-9]+)*`: lowercase letters and digits, with
single hyphens between groups, for example `ethyl-acetate`. Use the key
without `.toml` in `products` and `substrates`. A compound that no procedure
names is valid. Copy [templates/compound.toml](../templates/compound.toml)
when adding a compound. This is a standalone TOML file, with no `+++` lines
or `[product]` heading.

| Field | Meaning | TOML type | Required | Value rule | Example |
|---|---|---|---|---|---|
| `name` | The compound name on an English site. | Non-empty string | Yes | Must not be empty. | `name = "Ethyl acetate"` |
| `name_de` | The compound name on a German site. | Non-empty string | No | Must not be empty when present. A German site uses `name` when absent. | `name_de = "Ethylacetat"` |
| `formula` | The molecular formula. | Non-empty string | Yes | Must not be empty. | `formula = "C4H8O2"` |
| `mw` | Molecular weight in g/mol. | Integer or float | Yes | Must be finite and greater than zero. Do not quote it. A boolean is not a number. | `mw = 88.11` |
| `smiles` | The structure in SMILES, a text notation for molecular structures. | Non-empty string | Yes | Must not be empty. | `smiles = "CCOC(C)=O"` |
| `cas` | The CAS Registry Number, a chemical registry identifier. | String | No | Must have 2–7 digits, a hyphen, 2 digits, a hyphen, and the check digit. The check digit must verify. | `cas = "141-78-6"` |
| `structure_image` | The structure image under the static directory. | String | No | Must be a relative path under `structures/`, contain no `..` component, end in `.svg` or `.png`, and name an existing file. | `structure_image = "structures/ethyl-acetate.svg"` |

For example, `compounds/ethyl-acetate.toml` can contain:

```toml
name = "Ethyl acetate"
name_de = "Ethylacetat"
formula = "C4H8O2"
mw = 88.11
smiles = "CCOC(C)=O"
cas = "141-78-6"
```

The validator checks that `formula` and `smiles` are non-empty strings. It
does not check chemical formula syntax, SMILES validity, or whether the
molecular weight agrees with the formula.

The `--static-dir` argument controls where the validator resolves a compound's
`structure_image` or a procedure's `scheme_image`. Without it, the validator
uses `static` in the current directory. `orgsyndb validate` passes the
collection's `static/`. A path with the wrong prefix or suffix is not checked
for existence.

The registry has no subdirectories. A subdirectory is a `file_name` error
containing `subdirectories are not supported`. Dotfiles are skipped
silently. Any other file not named `<key>.toml` is a `file_name` error
containing `must be named <key>.toml`, and defines no compound. A file that
cannot be read as UTF-8 TOML gets a `toml` error and defines no compound;
a parse error contains `invalid TOML`. A missing required field produces
`required field missing`; unknown fields produce `unknown field` warnings.

## Tolerated, rejected, and unknown keys

The following Hugo or export metadata is outside the procedure schema but
is accepted silently when it has the stated type.

| Key | Meaning | TOML type | Required | Value rule | Example |
|---|---|---|---|---|---|
| `draft` | Hugo publication metadata that an exporter may emit. | Boolean | No | Only `false` is accepted. | `draft = false` |
| `description` | Tolerated Hugo page metadata. | String | No | Any string is accepted. | `description = ""` |
| `aliases` | Tolerated Hugo page metadata. | Array of strings | No | Every entry must be a string. | `aliases = []` |
| `weight` | Tolerated Hugo page metadata. | Integer | No | Must be an integer, not a boolean. | `weight = 1` |

The following keys are rejected:

| Key or value | Why it is rejected | Use instead |
|---|---|---|
| `draft = true` | Workflow state belongs in the schema, and a true Hugo draft is not published. | `status = "draft"` and omit `draft`, or keep `draft = false` when an exporter emits it. |
| `author = ["A. Example"]` | The schema uses the plural field. | `authors = ["A. Example"]` |
| `url = "/procedures/osdb-0001/"` | The URL is derived from `slug`. | `slug = "osdb-0001"` |

Any other top-level key produces an `unknown field` warning. This includes
misspellings such as `checkedby` and the fields `product`, top-level
`yield_percent`, `precursors` and `structure_image`. An unknown key in a
`products` entry produces a warning such as `products[1].colour`. Unknown
fields in a compound record produce warnings on its file under the field
name.

## Org file-level keywords

`orgsyndb export` checks that an Org procedure contains `#+CREATED` and
`#+LAST_MODIFIED` exactly once. It may contain `#+AI_MODEL` at most once.
Keyword names are case-insensitive.

| Org keyword | Required value | Exported front matter |
|---|---|---|
| `#+CREATED` | An inactive timestamp in the exact form `[YYYY-MM-DD Day hh:mm:ss]`. | `date`, with the same local date and time and the Europe/Berlin offset in force at that instant. |
| `#+LAST_MODIFIED` | An inactive timestamp in the exact form `[YYYY-MM-DD Day hh:mm:ss]`. | `lastmod`, with the same local date and time and the Europe/Berlin offset in force at that instant. |
| `#+AI_MODEL` (optional) | When present, `none` or one model identifier matching `[A-Za-z0-9][A-Za-z0-9._:/@+-]*`. | No `ai_model` field when the keyword is absent or its value is `none`; otherwise an `ai_model` string equal to the keyword value. |

For example:

```org
#+CREATED: [2026-10-19 Mon 17:42:05]
#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]
```

`Day` must be the correct English three-letter weekday, from `Mon` through
`Sun`. The timestamp is Europe/Berlin local wall-clock time and carries no
offset. The date and time must be real, including across clock changes. A
time skipped by the spring clock change is invalid.

`#+LAST_MODIFIED` must not be earlier than `#+CREATED`. During the repeated
hour of the autumn clock change, a local time can name two instants. The Org
check accepts the timestamps when some choice of the two Berlin offsets
puts them in order. The exported front-matter check is authoritative
because `date` and `lastmod` contain explicit offsets.

The Org template also maps `#+TITLE` to `title`, `#+HUGO_SLUG` to `slug`,
and `#+HUGO_TAGS` to `tags`. Repeated
`#+HUGO_CUSTOM_FRONT_MATTER` lines supply the other schema fields. The
export must not contain an `author` key.

For a specific procedure, set `products` alone on the last custom-front-matter
line. Put `substrates` and every other custom field before it:

```org
#+HUGO_CUSTOM_FRONT_MATTER: :substrates '("ethanol")
#+HUGO_CUSTOM_FRONT_MATTER: :products '(((compound . "ethyl-acetate") (yield_percent . 85)))
```

Each product is one `((compound . "key") (yield_percent . N))` entry in the
quoted list. Keep decimal points in numeric values in every language. The
export also keeps table-valued metadata last so later fields do not become
members of the last `[[products]]` table.

An Org source must not set `date`, `lastmod`, `ai_model`, or the export file
name through another ox-hugo input. `orgsyndb export` rejects the keywords
`#+DATE`, `#+HUGO_LASTMOD`, `#+HUGO_AUTO_SET_LASTMOD`,
`#+HUGO_FRONT_MATTER_KEY_REPLACE`, `#+EXPORT_FILE_NAME`,
`#+HUGO_BASE_DIR`, `#+HUGO_BASE_CONTENT_FOLDER`, `#+HUGO_SECTION`,
`#+HUGO_BUNDLE`, `#+SETUPFILE`, and `#+INCLUDE`; custom front-matter keys
`:date`, `:lastmod`, and `:ai_model`; `#+PROPERTY` or drawer properties
named `EXPORT_*` or `LOG_INTO_DRAWER`; a `:LOGBOOK:` drawer; and the
source-block header argument `:front_matter_extra`. Lines
inside `#+begin_` ... `#+end_` blocks are ignored. The general error is
`must not be used; the export sets date, lastmod, ai_model and the export
file name itself`. A `#+PROPERTY` error is `must not set <NAME>; the export
sets date, lastmod, ai_model and the export file name itself`. The custom
front-matter errors are `must not set :date; the export writes it from
#+CREATED`, `must not set :lastmod; the export writes it from
#+LAST_MODIFIED`, and `must not set :ai_model; the export writes it from
#+AI_MODEL`.

### Org scope table

For a general procedure, remove the top-level `:products` and `:substrates`
custom-front-matter lines. Write one Org table directly after `#+NAME: scope`,
anywhere outside a block. The table name is case-insensitive. The first row
names the columns, followed by a separator line and one row per entry.
`substrates`, `products` and `yield_percent` are required columns; `scale`,
`time`, `temperature` and `note` are optional. Column names stay English.

In `substrates` and `products`, separate compound keys with spaces. Give one
number per product in `yield_percent`, separated by spaces in product order.
`temperature` holds one number. Numbers may use a decimal comma, such as
`45,5`. The text in `scale`, `time` and `note` is trimmed. An empty cell leaves
its key unset; required entry fields are still checked by validation.

The [Org fixture](../tests/fixtures/export/OSDB-0909-scope-table.org) shows
three entries, including one with two products. Export writes `scope` into the
front matter and removes the table and its `#+NAME` line from the body. It puts
each entry's `products` after its other keys so later fields do not become
members of the last product table. Set a scheme image with:

```org
#+HUGO_CUSTOM_FRONT_MATTER: :scheme_image "structures/aryl-ketone-reduction.svg"
```

Malformed scope tables stop export, with field `scope`. Rows count from 1 after
the separator:

| Message | What to correct |
|---|---|
| `appears more than once` | Keep only one table named `scope`. |
| `"<name>" is not a scope column` | Use one of the seven column names above. |
| `column "<name>" missing` | Add the named required column. |
| `column "<name>" appears more than once` | Keep the named column once. |
| `row <n>: <p> products but <y> yields` | Supply one yield for each product, in order. |
| `row <n>: "<cell>" is not a number` | Use a numeric yield or temperature, without units. |

## Reaction-type vocabulary

`reaction_types` contains exactly one slug from this table. The slug is the
value written in front matter, in every language. The label is the name
an English site shows, and the German label the name a German site
shows.

| Slug | Label | German label |
|---|---|---|
| `acylation` | Acylation | Acylierung |
| `aldol-condensation` | Aldol condensation | Aldolkondensation |
| `alkylation` | Alkylation | Alkylierung |
| `amide-coupling` | Amide coupling | Amidkupplung |
| `cross-coupling` | Cross-coupling | Kreuzkupplung |
| `cycloaddition` | Cycloaddition | Cycloaddition |
| `deprotection` | Deprotection | Entschützung |
| `esterification` | Esterification | Veresterung |
| `hydrolysis` | Hydrolysis | Hydrolyse |
| `nucleophilic-substitution` | Nucleophilic substitution | Nucleophile Substitution |
| `olefination` | Olefination | Olefinierung |
| `oxidation` | Oxidation | Oxidation |
| `protection` | Protection | Schützung |
| `reduction` | Reduction | Reduktion |
| `reductive-amination` | Reductive amination | Reduktive Aminierung |

The vocabulary is stored in `site/data/reaction_types.toml`. Each entry is
a lowercase, hyphenated slug whose table contains a non-empty `label` and
a non-empty `label_de`. The site shows `label` where `label_de` is
missing, and the validator refuses an empty `label_de`.

## Procedure body sections

Every procedure body, including a general procedure, has these eight sections
in this order. The site adds the scope table before them:

1. Summary
2. Reagents
3. Procedure
4. Workup and Purification
5. Characterization
6. Notes
7. Hazards and Waste Disposal
8. References

A procedure in German uses these names instead, in the same order:

1. Zusammenfassung
2. Reagenzien
3. Durchführung
4. Aufarbeitung und Reinigung
5. Charakterisierung
6. Anmerkungen
7. Gefahren und Entsorgung
8. Literatur

Which set applies depends on the language: the code in the file name, else
the `language` field. A file with neither is checked against the set that
fits its headings better, so it may use either.

In Markdown, write them as level-2 headings such as `## Summary`. In Org,
write them as top-level headings such as `* Summary`. A missing Markdown
section or sections in the wrong order produces a warning, not an error.
`orgsyndb validate` applies this body check to the Markdown exported from an
Org procedure. `tools/validate.py` does not read Org sources directly.

Markdown matching is case-insensitive and ignores surrounding or repeated
whitespace. It also accepts an exported trailing attribute such as
`## Summary {#summary}` and a closing `#` sequence. A heading inside a
fenced code block does not count. Other level-2 headings and headings at
other levels are allowed.

## Languages and variants

A procedure file's name may carry a language code, `.de` or `.en`, before
its suffix. Any other code is an error. A file without a code may be in
either language. Files with the same identifier are *variants* of one
procedure, for example `OSDB-0001-salicylic-acid.org` and its German
translation `OSDB-0001-salicylic-acid.de.org`. Org and Markdown may be
mixed. Within one identifier, each code, and the absence of a code, may
occur once.

The site has one language, set by `locale` in the application's
`site/hugo.toml` (`"de"` by default). Every procedure is published once,
in the variant that suits that language: the file tagged with it, else
the file without a code, else a file tagged with the other language. A
derived precursor may be any procedure, whatever the language of its
variants.

The variants of a procedure:

- have the same base name, the file name without code and suffix;
- have the same `id` and `slug`;
- have the same value, or the same absence, of `status`, `reaction_types`,
  `tags`, `products`, `substrates`, `scope` and `scheme_image`;
- may translate each scope entry's `note`; all other scope values and the entry
  order must agree;
- may differ in every other field and in the body: `title`, `scale`,
  `hazards`, `references`, `authors`, `checked_by`, `ai_model`, `language`,
  `date` and `lastmod`.

The validator compares each variant with a reference variant: the file without
a code, else the `.de` file. Each difference is an error on the other variant
that names the reference. A changed product key or yield is reported under
`products`; a changed starting-material list is reported under `substrates`. A
scope difference is reported under `scope`, ignoring entry notes; a scheme-path
difference is reported under `scheme_image`. Numbers compare by value, so `85`
and `85.0` agree; other values compare by both value and type.

Compound names come from the registry, independently of the procedure's
language. A German site uses `name_de` when present, otherwise `name`;
an English site uses `name`. This applies to compound pages and their
ordering in the directory, product and starting-material links, yields,
structure image descriptions, catalogue details and indexed terms.

The optional front-matter field `language` states a procedure's language,
`"de"` or `"en"`. When the file name has a code, the field must name the
same language; the build adds it to a tagged file that lacks it. It also
picks the section names that a file without a code is checked against.
When the published variant's language differs from the site's, its page
marks the procedure with a `lang` attribute.

A German Reagents table has the columns **Reagenz**, **CAS**, **M (g/mol)**,
**Menge**, **mmol** and **Äquiv.**, and German text uses decimal commas.
Product yields in `products` or `scope`, scope temperatures and `mw` in
compound files stay TOML numbers with a decimal point in every language; a
German site shows them with a comma.

## Reading validator output

Run the validator with at least one Markdown content root:

```text
tools/validate.py [--vocabulary FILE] [--static-dir DIR] [--compounds DIR] CONTENT_ROOT...
```

Each positional `CONTENT_ROOT` is a directory of Markdown procedures.
If omitted, `--vocabulary` defaults to the application's
`site/data/reaction_types.toml`, resolved from the script's location rather
than from the current directory, and `--static-dir` defaults to `static` in
the current directory. `--compounds` defaults to `compounds` in the current
directory. The validator checks every compound file there and resolves
procedure keys against that registry. A missing registry directory is empty,
so every key a procedure names is unknown. An existing path that is not a
directory is a configuration error. `orgsyndb validate` passes
`--static-dir static --compounds compounds` from the collection root, after
exporting Org sources.

Each problem is one line on standard output:

```text
<path>:<field>: <severity>: <message>
```

The field is normally a front-matter key. Product fields use dotted names,
such as `products[1].yield_percent`, counting products from 1. A non-table
entry is reported under `products[n]`. Compound problems use the compound
file's path and field name, for example `compounds/ethyl-acetate.toml:mw`.
Other possible fields are `file_name`, `front_matter`, `toml` and `body`.

Scope fields use `scope[n].<key>`, and a product within an entry uses
`scope[n].products[m].<key>`. Both indices start at 1. A non-table scope entry
is reported under `scope[n]`. An unknown key in an entry produces an
`unknown field` warning at its full field name.

| Field | Message | Meaning |
|---|---|---|
| `products` or `substrates` | `a general procedure lists them in scope; move <key> into its entries` | Remove the top-level field and put its data in the relevant entries. |
| `scope` | `must not be empty` | Supply at least one entry. |
| `scope` or `scope[n]` | `must be an array of tables` or `must be a table` | Correct the TOML shape. The message also gives an example. |
| `scope[n].time` | `"<value>" must be a number followed by min, h or d, e.g. "2 h"` | Supply a number and one of the three units. |
| `scope[n].temperature` | `must be a number in °C, unquoted, e.g. 80` | Remove quotes and units; use a finite number. |

Missing required scope fields, duplicate keys, unknown compounds and invalid
yields use the product and substrate messages below, under the scope field.

For `products`, `must not be empty` means you need at least one entry;
`must be an array of tables` or `must be a table` identifies the wrong TOML
shape. `required field missing` names an omitted key. An unknown compound
is reported as `unknown compound "<key>"; the compound registry has no
<key>.toml`. Check the spelling and the registry directory. `lists <key>
twice` means a duplicate product or substrate; `<key> is also a product`
means a starting material repeats a product.

`orgsyndb export` prints Org-source problems on standard output in the same
line format. Its fields can also be Org keywords such as `#+CREATED`,
properties such as `#+PROPERTY` or `:EXPORT_DATE:`, and drawers such as
`:LOGBOOK:`.

An `error` means a procedure or compound record is invalid. A `warning`
identifies a problem that does not make validation fail, such as a missing
body section or an
unknown field. After the problem lines, the validator writes a summary to
standard error. The file count includes compound files as well as
procedures. For the demo collection, including existing Org exports:

```text
validated 38 files: 0 errors, 0 warnings
```

The first three lines below are real validator output. The last is the same
line form produced by `orgsyndb export` for an Org source:

```text
tests/fixtures/invalid/yield-out-of-range/OSDB-0110-yield-out-of-range.md:products[1].yield_percent: error: 104.5 must be between 0 and 100
tests/fixtures/invalid/unknown-compound/OSDB-0123-unknown-compound.md:products[1].compound: error: unknown compound "no-such-compound"; the compound registry has no no-such-compound.toml
tests/fixtures/warn/missing-section/OSDB-0151-missing-section.md:body: warning: missing section "Notes"
tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org:#+CREATED: error: weekday "Tue" does not match 2026-10-19 (Mon)
```

The exit status tells a calling command whether validation succeeded:

| Exit status | Meaning |
|---|---|
| `0` | No errors were found. Warnings may still have been printed. |
| `1` | At least one procedure or compound error was found. |
| `2` | The invocation or validator configuration is invalid, such as no root, a root that is not a directory, or a missing or malformed vocabulary file. |

Usage and configuration failures are written to standard error and include
`validate.py: error:`. The validator suppresses checks that depend on a
missing or malformed value, so one mistake does not usually produce a chain
of secondary messages.
