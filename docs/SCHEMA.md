# Procedure schema reference

This reference defines valid OrgSynDB procedures and synthesis sequences,
and the registry data they use.
Use it to look up the exact spelling, type, and rule for a field, or to
interpret a message from
`tools/validate.py` or `orgsyndb export`.

A German version of this reference is [SCHEMA.de.md](SCHEMA.de.md).

A Markdown procedure starts with TOML front matter. TOML is the metadata
block between the opening and closing `+++` lines. The opening `+++` must be
the first line of the file. Text after the closing `+++` is the procedure
body. Sequences use the same front-matter delimiters; their body holds notes.

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
| `reaction_types` | The controlled reaction category. | Array of strings | Yes | Must contain exactly one slug from the registry's `reaction-types` vocabulary. | `reaction_types = ["esterification"]` |
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

The panel adds **Sequences** after **Used in** when this procedure is a step
of a sequence. It links those sequences by title, ordered by sequence ID.

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

Procedures and sequences share the substances of the lab application's
registry. Create and edit substances at `/lab/registry/` in that application.
A compound key is a substance's key: two procedures name the same compound
exactly when they use the same key. Structures are not compared to establish
identity. A key matches `[a-z0-9]+(-[a-z0-9]+)*`: lowercase letters and digits,
with single hyphens between groups, for example `ethyl-acetate`. A substance
that no procedure names is valid.

The collection names its registry in `orgsyndb.toml`:

```toml
format = 1
registry = "http://localhost:8000/lab/registry/snapshot.json"
```

`registry` is a non-empty string. It names an `http://` or `https://` address
of the lab application's snapshot, or a snapshot file's path, relative to
the collection unless absolute. A non-empty `ORGSYNDB_REGISTRY` environment
variable overrides it. The demo uses
`registry = "../../webapp/demo/registry.json"` and needs no running lab
application. Collection directories named `compounds/` or `vocabularies/`
are ignored.

`orgsyndb validate`, `build`, `serve`, `pdf` and `index` read this registry.
The first four keep the snapshot in `build/registry.json` and its source in
`build/registry.source`; `index` writes nothing. Requests to an address have
a 30-second timeout. If the address cannot be read or does not return a
snapshot, the tools use the kept copy only when `build/registry.source`
names the same address. They warn with:

```text
orgsyndb: warning: cannot read the registry: <address>: <reason>; using the copy in build/registry.json, digest <digest>
```

Without a matching copy, the command fails with an error naming the address.
A missing or unreadable snapshot file also fails; it has no fallback.

The snapshot, a saved copy of the lab registry, is UTF-8 JSON in format 1.
Its `digest` is a fingerprint of its contents. It supplies the vocabularies
`chemical-classes`, `inventory-groups`, `projects` and `reaction-types`, and
the substances. The site uses each substance's names, formula, molar mass
(`mw`, in g/mol), SMILES (a text notation for molecular structures), CAS
Registry Number (`cas`), article number, short name, chemical classes and
group. An English site uses `name`; a German site uses `name_de` when
supplied, otherwise `name`. Without formula, molar mass or SMILES, the
substance has an empty directory cell, no corresponding search text and no
such fact on its page. The lab application checks substance values; the
collection validator checks references to their keys.

To supply a structure image, put `static/structures/<key>.svg` or
`static/structures/<key>.png` in the collection. The build uses the SVG when
both exist. A substance without either has no image. There is no
`structure_image` field to set. The build writes one
`build/data/compounds/<key>.json` per substance and sets `structure_image`
in that generated data only when it finds an image. Hugo reads these files
as `data/compounds`.

For a procedure's `scheme_image`, `--static-dir` controls where the validator
resolves the path. It defaults to `static` in the current directory;
`orgsyndb validate` passes the collection's `static/`. A path with the wrong
prefix or suffix is not checked for existence.

A compound page adds **Sequences** after **Used in** when any sequence names
it as its target. The list links those sequences by title, ordered by ID.

**Routes** is the last section of the compound page, after **Sequences**
when that section is present. It shows ways to make the compound from the
collection's published procedures, including the procedures that make its
starting materials. It appears only when a route goes beyond one step.
When no procedure makes any of the starting materials, **Made by** already
covers the available steps and there is no **Routes** section.

Read the tree as nested lists. Under a compound, the steps are alternatives:
any one will do. Under a step, all listed starting materials are needed.
Each starting material links to its compound page and has its own steps
below it, down to compounds no procedure makes. Compound links carry the
substance’s article number and short name when supplied, as elsewhere on
the site.

Each step shows the procedure's ID and title, entry number for a general
procedure, yield and status, as in **Made by**. Steps are ordered by
procedure ID, with a general procedure's entries in entry order. Each entry
is a separate step and uses only that entry's starting materials. All
published procedures take part, whatever their status; the badge shows it.

The tree omits a step if any of its starting materials already appears
above it on the same branch. This avoids cycles such as protection followed
by removal of the protecting group. A compound whose only steps would loop
back appears without steps: you must obtain it another way.

The display uses a fixed depth limit of 6 steps and a fixed budget of 200
steps per tree. These are not collection settings. A larger tree is drawn to
the largest depth that fits. When more than 200 steps make the compound
directly, the tree shows only those. A compound cut off by a limit ends with
**more steps on its page**; follow its link to continue.

The build derives routes automatically. You add nothing to a procedure or
`orgsyndb.toml` for them. Compound pages remain outside
the search index, so routes do not change search.

## Collection field declarations

To record extra procedure data such as a lab-notebook reference or project,
declare fields in the collection's `orgsyndb.toml`. This UTF-8 TOML file must
contain `format = 1` as an integer. The other allowed top-level keys are
`registry` and `fields`. `registry` names the snapshot as described under
[Compound registry](#compound-registry). `fields` is an optional table whose
only allowed key is `procedure`, an array of field declarations. Without
`fields` or `fields.procedure`, the collection declares no extra procedure
fields.

Compounds have four built-in registry fields, in this order. Their
presentation is fixed for every collection:

| Key | Value from the substance | Type and vocabulary | Label (English / German) | Display |
|---|---|---|---|---|
| `article_number` | Article number | Text | Article no. / Artikelnr. | Directory column, search, beside links |
| `short_name` | Short name | Text | Short name / Kurzname | Search, beside links |
| `chemical_class` | `chemical_classes`, in their order | Multiple choice, `chemical-classes` | Chemical class / Stoffklasse | Directory column, filter |
| `group` | Group | Single choice, `inventory-groups` | Group / Gruppe | Filter, tabs |

Set these values in the lab application. The collection declares only
procedure fields; `fields.compound` is a configuration error.

### Declaration keys

The following tables describe procedure declarations. Write one
`[[fields.procedure]]` table per field; a single `[fields.procedure]`
table is invalid.

| Key | TOML type | Required or default | Rule |
|---|---|---|---|
| `key` | String | Required | Matches `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`: lowercase letters and digits, words joined by single underscores, starting with a letter. Must be declared once, must not end in `_de`, and must avoid the reserved procedure keys listed below. |
| `type` | String | Required | One of `text`, `number`, `boolean` or `choice`. |
| `label` | Non-empty string | Required | The field's name on an English site. |
| `label_de` | Non-empty string | Optional | The field's name on a German site; without it, the site uses `label`. |
| `required` | Boolean | `false` | When `true`, every procedure must set the field, including a general procedure. |

Only the following additional keys are allowed for each type. Using an
option on another type is a configuration error.

| Key | Field type | TOML type | Required or default | Rule |
|---|---|---|---|---|
| `pattern` | `text` | String | Optional | A valid Python regular expression that the whole value must match. |
| `unique` | `text`, `number` | Boolean | `false` | No two procedures may set the same valid value; language variants count as one. |
| `min` | `number` | Integer or float | Optional | Finite inclusive lower bound; must not exceed `max` when both are set. A boolean is not a number. |
| `max` | `number` | Integer or float | Optional | Finite inclusive upper bound. A boolean is not a number. |
| `unit` | `number` | Non-empty string | Optional | Written after the number, separated by a space. |
| `vocabulary` | `choice` | String | Required | Names one of the registry vocabularies: `chemical-classes`, `inventory-groups`, `projects` or `reaction-types`. |
| `multiple` | `choice` | Boolean | `false` | When `true`, the procedure supplies a non-empty list of distinct term keys instead of one string. |
| `facet` | `boolean`, `choice` | Boolean | `false` | When `true`, the procedure catalogues offer the field as a filter. |

### Procedure field declarations

To record a lab-notebook reference, project or other procedure data, write
one `[[fields.procedure]]` table per field in `orgsyndb.toml`, in display
order. Omitting `fields.procedure` declares no procedure fields. For example,
the demo declares:

```toml
[[fields.procedure]]
key = "notebook"
type = "text"
label = "Lab notebook"
label_de = "Laborjournal"
unique = true
pattern = '[A-Z]{2}-\d+/\d+'

[[fields.procedure]]
key = "project"
type = "choice"
label = "Project"
label_de = "Projekt"
vocabulary = "projects"
facet = true
```

Use the declaration keys, types and defaults above. These rules also apply:

- `column`, `search`, `tabs` and `beside` are never allowed, even with
  `false`.
- `required = true` requires the field on every procedure, including general
  procedures. The default is `false`.
- `unique = true`, available for `text` and `number`, forbids the same valid
  value on two procedures. Language variants of one procedure count as one.
  The default is `false`.
- `facet = true`, available for `boolean` and `choice`, makes the field a
  filter of the procedure catalogues. The default is `false`.
- `key` must match `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, must not end in `_de`,
  and must occur only once within `fields.procedure`. Procedure keys must
  avoid these groups:

  **Procedure schema:** `id`, `slug`, `title`, `date`, `lastmod`, `authors`,
  `status`, `reaction_types`, `tags`, `products`, `scale`, `hazards`, `substrates`,
  `scope`, `scheme_image`, `checked_by`, `references`, `ai_model`, `language`,
  `draft`, `description`, `aliases`, `weight`, `author`, `url`.

  **Front matter Hugo reads:** `build`, `cascade`, `expirydate`, `headless`,
  `iscjklanguage`, `keywords`,
  `kind`, `lang`, `layout`, `linktitle`, `markup`, `menu`, `menus`, `modified`,
  `outputs`, `params`, `path`, `pubdate`, `publishdate`, `published`,
  `resources`, `sitemap`, `sites`, `summary`, `translationkey`, `type`,
  `unpublishdate`, `authors_weight`, `reaction_types_weight`, `tags_weight`.

  **Procedure catalogue:** `tag`, `created`, `text`, `q`, `sort`, `view`.

Procedure choice fields use the terms of their named registry vocabulary.
A choice may name a term at any level of that vocabulary.

Set procedure values as top-level keys in Markdown TOML front matter,
before any table. The demo's aspirin procedure sets these after `scale`:

```toml
notebook = "AE-1/2"
project = "first-year-practical"
working_time = 2.5
inert_atmosphere = false
```

The demo declares `working_time` as `number` with `unit = "h"` and `min = 0`,
and `inert_atmosphere` as `boolean` with `facet = true`. None of its four
procedure fields is required. A new demo procedure may omit them; any
`notebook` it sets must match the pattern and be unused.

Every Markdown procedure and Org export is checked against the procedure
declarations. Value errors use the field's key on the procedure's path and
the [procedure value messages](#procedure-values-and-messages), including
`required field missing`, type, pattern, bound and choice-list errors.
For `unique`, the message is `"<value>" is also set by <other procedure IDs>`;
numbers appear without quotes. The comparison uses one reference variant
per procedure ID and only values that pass the field checks. A file whose
front matter cannot be parsed supplies no value. All variants must repeat
the same declared values; see [Languages and variants](#languages-and-variants).
For Org syntax and its string-typing limit, see
[Org file-level keywords](#org-file-level-keywords).

### Vocabularies

A vocabulary lists the terms a choice field accepts. All four vocabularies
come from the registry: `chemical-classes`, `inventory-groups`, `projects`
and `reaction-types`. Create and edit terms in the lab application.
A procedure stores a term's key; the site shows its label.

Each term has an English `label` and may have `label_de`, its German label.
A German site uses `label_de` when supplied, otherwise `label`.
`chemical-classes`, `inventory-groups` and `projects` may have several
levels: a term's `parent` names another term in the same vocabulary.
Following parents must reach a term without a parent; a term cannot be its
own ancestor. There is no limit on the number of levels. Choices may select
terms at any level. For example, the demo's `esters` is filed under
`acid-derivatives`, which is filed under `carbonyl-compounds`.
Reaction types have one level.

Filters and tabs list each term followed by the terms filed under it,
recursively, with siblings in key order. Selecting a parent in a filter
also matches values filed under its descendants.

### Compound values and messages

The lab application checks substance values. The collection validator does
not report field-value errors on individual substances.

A substance keyed `group` conflicts with `/compounds/group/`, the directory
of the group tabs. The lab application refuses this key, so only a snapshot
file made another way can hold it. The validator reports one error on the snapshot path
as passed to `--registry`, under `substances`:

```text
the substance "group" has the key of the directory of the compound tabs, /compounds/group/, which no substance may take
```

### Procedure values and messages

Set declared procedure fields as top-level keys in front matter. Value
problems are errors on the procedure file's path, under the declared key:

| Field type or rule | Message | Meaning |
|---|---|---|
| `required = true` | `required field missing` | Set the field in every procedure, including a general procedure. |
| `text`, single `choice` | `must be a string` | Put the value in quotes. |
| `text` | `must not be empty` | Supply non-empty text. |
| `text` with `pattern` | `must match the pattern <pattern>` | The whole string must match the declared pattern. |
| `number` | `must be a number, unquoted` | Supply a finite TOML integer or float, without quotes or units; a boolean is not a number. |
| `number` with `min` | `must be at least <min>` | Increase the value to the inclusive lower bound or above. |
| `number` with `max` | `must be at most <max>` | Reduce the value to the inclusive upper bound or below. |
| `boolean` | `must be true or false, unquoted` | Use `true` or `false` without quotes. |
| `choice` | `unknown value "<v>" of the vocabulary <name>` | Use a term key from the named registry vocabulary, at any level. |
| `choice` with `multiple = true` | `must be a list of strings, e.g. ["<a term>"]` | Supply a list of quoted term keys. The example uses the first term in the snapshot, or `a term` if the vocabulary is empty. |
| `choice` with `multiple = true` | `must not be empty` | Supply at least one choice. |
| `choice` with `multiple = true` | `repeats "<v>"` | Remove the repeated value. |
| `unique = true` | `"<value>" is also set by <other procedure IDs>` | Use a value no other procedure sets. For numbers, the message shows the value without quotes. |

A value of the wrong type produces only that type error. Empty text with a
pattern produces only `must not be empty`. A list of choices produces one
`unknown value` error per unknown string. Uniqueness checks compare values
that pass their field's checks and report every procedure sharing a value,
using one reference variant per procedure ID.

### Configuration errors

The validator rejects settings that break a declaration rule, including
invalid regular expressions, non-finite bounds, `min` greater than `max`
and duplicate declarations. A file explicitly named by `--settings` must
exist. Settings must be readable UTF-8 TOML. A registry file must exist,
be readable UTF-8 JSON and contain a format-1 snapshot with the four
vocabularies and a list of substances.

These are configuration errors: exit status 2, nothing on standard output,
and `validate.py: error: ...` on standard error. Messages identify the
settings or registry file, the field key when valid, and the offending key
or value. An option for another type produces a message such as
`a number field does not take pattern`; an unknown option produces
`unknown key <key>`. An unknown top-level setting produces
`unknown key <key>; only format, registry, fields are allowed`.

`fields` accepts only `procedure`. An entry such as `fields.compound` or
`fields.reagent` produces `unknown key fields.<key>; only fields.procedure
is allowed: a collection declares the fields of its procedures, and its
compounds have the registry's`. A single `[fields.procedure]` table produces
`fields.procedure must be an array of tables, each written [[fields.procedure]]`.

| Problem | Message or identifying text |
|---|---|
| Missing registry file | `registry file not found` |
| Registry is not JSON | `not UTF-8 JSON: <reason>` |
| Registry is not a snapshot | `not a registry snapshot: <reason>` |
| Invalid `registry` setting | `registry must be the address of the lab application's registry snapshot or the path of a snapshot file, a non-empty string` |
| Missing choice vocabulary | `vocabulary missing; a choice field names one of the registry's vocabularies, chemical-classes, inventory-groups, projects, reaction-types` |
| Unknown choice vocabulary | `vocabulary '<name>' is not one of the registry's vocabularies, chemical-classes, inventory-groups, projects, reaction-types` |
| Withheld option | `a procedure field does not take column` (or `search`, `tabs`, `beside`), even when set to `false` |
| Procedure-schema key | `declaration 5 of fields.procedure: key 'status' is a key of the procedure schema` |
| Hugo key | `declaration 5 of fields.procedure: key 'layout' is a front-matter key that Hugo reads` |
| Catalogue key | `declaration 5 of fields.procedure: key 'tag' is reserved by the procedure catalogue; the reserved keys are tag, created, text, q, sort, view` |

The declaration number is its position within `fields.procedure`. Key errors,
including duplicates and invalid spelling, identify `fields.procedure`.
Malformed snapshot errors identify the offending vocabulary, term or
substance. These check the snapshot's shape and types, not substance values.

Commands that read the registry also require a registry source. Without
`registry` or a non-empty `ORGSYNDB_REGISTRY`, they report `no registry named; set
registry to the address of the lab application's registry snapshot`,
followed by an example address and the file-path and environment options.
An address that cannot be read and has no matching kept copy produces
`cannot read the registry: <address>: <reason>; there is no copy of it in build/registry.json`.

The build program checks the settings file's TOML, `format`, top-level keys
and `registry` value before running a command. The validator checks the
procedure declarations, so a broken declaration does not prevent `clean`
or `new`.

### Display on the site

Procedure pages show each declared field the procedure sets in the metadata
panel, in declaration order, after **Checked by** and before **Created**.
Labels use `label_de` on a German site when present, otherwise `label`.
Text appears as written; numbers use the site's decimal separator and unit,
such as `2,5 h`; booleans show **Yes**/**No** or **Ja**/**Nein**. Choices show
the path of labels joined by ` › `, such as **Lehre › Grundpraktikum**;
multiple choices are separated by `, ` in the procedure's order. The panel is
indexed, so catalogue search finds these displayed values.

Each boolean or choice procedure field with `facet = true` adds a filter
between **Status** and **Tag**, in declaration order, open by default and
without an “all values” link. Boolean filters list **Yes**, then **No**,
each only when some published procedure sets it. Choice filters list used
values and their ancestors as an indented tree in vocabulary order.
Selecting a parent also matches procedures filed under its descendants.
These filters appear on `/procedures/`, every reaction-type, tag and author
page, and `/general-procedures/`. Every page offers values from the whole
collection. The address uses the declared key, for example
`/procedures/?project=research&inert_atmosphere=true`. Selections use the same
OR/AND and count rules as compound filters below. Procedure fields do not
add table columns, values to the **Details** view, or tabs.

Compound pages show the four built-in fields after Formula, MW, CAS and
SMILES, omitting absent values. They appear in this order: **Article no.**,
**Short name**, **Chemical class**, **Group**, with their German labels on a
German site. Article numbers and short names appear as written.

The metadata panel's **Product**/**Products** and **Starting materials**, a
general procedure's scope table, a sequence page's scheme, the sequence
directory's target and compound-page route trees show the substance's
article number and short name after each compound link. The link text stays
the compound's name. One space separates the link from a muted note in
parentheses, such as **Acetic anhydride (Ac2O)** or
**Acetylsalicylic acid (CH-0010, ASA)** in the demo. The note contains only
values the substance has, article number first, without labels and separated
by `, `. A substance with neither gets no note. Key facts, the catalogue's
**Details** view, image alt texts and page titles carry no note. The metadata
panel is indexed, so procedure search also finds these values.

A choice on a compound page shows the labels of its ancestors and its own
label joined by ` › `, such as **Carbonyl compounds › Carboxylic acid
derivatives › Esters**. Multiple chemical classes are separated by `, ` in
the substance's order. The compound directory adds **Article no.** and
**Chemical class** columns after CAS. It shows only each class's own label
and leaves unset values as empty cells.

`/compounds/` and each group tab page begin with a row of tabs, styled like
the procedure tabs. **All compounds** (**Alle Verbindungen** in German)
links to `/compounds/`. The remaining tabs use the labels of the
`inventory-groups` vocabulary's top-level terms, in key order, including
only terms some substance uses directly or through a term filed under them.
The current page's tab is marked.

A tab page lives at `/compounds/group/<value>/`, with the value's label as
its heading and title. It lists substances that set the value or a value
filed under it, in name order. Its count, filters and search work within that
list, as on `/compounds/`. The demo's **Purchased** and **Synthesised** pages
are `/compounds/group/purchased/` and `/compounds/group/synthesised/`, with
ten and eleven substances respectively.

On a tab page, filters list only values carried by its substances. The
**Group** filter leaves out the tab's value and moves values filed under it
up one level. A filter with no values to list is omitted. The header search
is labelled **Search compounds: \<label\>** (**Verbindungen durchsuchen:
\<label\>** in German). Tab links carry no query or filters. Without
JavaScript, a tab page shows its whole list.

At `/compounds/`, the directory is a searchable, filterable catalogue of
every registry entry. Rows stay in order of the name shown in the site's
language. **Chemical class** and **Group** appear as filters in that order.
Each lists values used by substances and their ancestors as an indented
tree. Each term is followed by its descendants, with siblings in key order.
Selecting a parent also matches compounds filed under its descendants:
**Carbonyl compounds** includes ketones and esters.

Selections within one filter combine with OR; different filters combine
with AND. Each value's count includes the search and every other filter,
excluding its own filter's selections. Selected values appear as small
buttons (chips) that remove a selection. **Clear all** clears the query and
selections. The catalogue shows a total count, or **{shown} of {total}
compounds** while filtering.

The header's **Search compounds** field matches English and German names,
formula, CAS number, SMILES, article number and short name.
Every query word must match a substring, ignoring case and characters other
than letters and digits. Searches such as `50-78-2`, `salicyl` and
`c1ccccc1O` work without a Pagefind index. Outside these catalogues, including
individual compound pages, the header searches procedures; compound pages
remain outside the procedure search index.

The address preserves the query and selections, for example
`/compounds/?q=ester&chemical_class=esters&group=final-products`. Parameters
the page cannot apply are named in a notice and removed from the address. Search and
filters need JavaScript. Without it, the page shows the complete table and a
note explaining this.

## Synthesis sequences

A sequence records an ordered route through at least two procedures. Write it
in Markdown, including when its steps refer to Org procedures. Copy
[templates/sequence.md](../templates/sequence.md) into the collection's
`md/sequences/`. `orgsyndb init` creates this directory; a missing directory
holds no sequences. `orgsyndb new` creates procedures, so sequence files are
copied by hand.

A sequence records the route your group runs. The compound page's
**Routes** tree is derived from the collection's procedures.

Name the file `SEQ-NNNN-short-slug.md`, optionally with `.de` or `.en` before
`.md`. The short slug matches `[a-z0-9]+(-[a-z0-9]+)*`. The filename's ID must
equal `id`. `SEQ-0000` and `seq-0000` are template placeholders; replace them
with an unused ID from `SEQ-0001` through `SEQ-9999` and its lowercase form.
The page URL is `/sequences/seq-NNNN/`.

The validator reads only the directory's top level. Subdirectories are errors;
dotfiles and `_index.md` are skipped silently. A file without the `.md` suffix
produces `not a sequence file; ignored`; a Markdown file with a malformed name
is a `file_name` error.

### Sequence fields

Keep all seven required keys between the two `+++` lines. Replace the
template's target and steps with your own. Do not add `authors`: each step
credits its procedure's authors. The procedure taxonomy keys `authors`,
`tags` and `reaction_types` are errors in a sequence, which stop the build:
Hugo would otherwise list the sequence among the procedures of an author,
tag or reaction type. Every other key outside this schema produces an
`unknown field` warning. Unknown step keys produce a warning under
`steps[n].<key>`.

| Field | TOML type | Required | Rule | Example |
|---|---|---|---|---|
| `id` | String | Yes | `SEQ-0001` through `SEQ-9999`; unique once per language code and once without one. | `id = "SEQ-0001"` |
| `slug` | String | Yes | Exactly the lowercase `id`. | `slug = "seq-0001"` |
| `title` | Non-empty string | Yes | Page heading. | `title = "Aspirin from oil of wintergreen"` |
| `date` | Offset datetime | Yes | Unquoted; the same date rules as procedures. | `date = 2026-10-23T09:15:00+02:00` |
| `lastmod` | Offset datetime | Yes | The same rules as `date`; not earlier than `date`. | `lastmod = 2026-10-23T09:40:00+02:00` |
| `target` | String | Yes | Existing substance key in the registry; a product of the last step. | `target = "acetylsalicylic-acid"` |
| `steps` | Array of tables | Yes | At least two steps, in execution order. | `steps = [{ procedure = "OSDB-0001" }, { procedure = "OSDB-0002" }]` |
| `steps[n].procedure` | String | In every step | Procedure ID found in the validated content roots, whether exported from Org or written in Markdown. | `procedure = "OSDB-0009"` |
| `steps[n].entry` | Integer | For general procedures only | Scope entry number from 1 through the number of entries; forbidden for a specific procedure. A boolean is not an integer. | `entry = 1` |

Write notes after the closing `+++`, for example under `## Notes`. The eight
procedure-body sections are not required for a sequence. The demo's
[SEQ-0002](../examples/demo/md/sequences/SEQ-0002-biphenylyl-ethanol.md)
shows a step through a general procedure:

```toml
target = "1-biphenyl-4-yl-ethanol"
steps = [{ procedure = "OSDB-0004" }, { procedure = "OSDB-0009", entry = 1 }]
```

### Continuity, variants and yield

Each step after the first must take at least one product of the previous step
as a starting material. For a general procedure, only the chosen scope entry's
substrates and products count. The target must be a product of the last step.
The validator checks continuity on the reference sequence variant only: the
untagged file, otherwise the `.de` file, otherwise `.en`. These checks require
at least two step tables. A step with an unresolved procedure or an absent,
invalid or forbidden entry is omitted from continuity checks. The target
check also requires a known compound key.

Variants share the base name, `id`, `slug`, `target` and ordered `steps`.
Each language code, and the absence of a code, may occur once per ID. Title,
dates and body may differ. Differences in shared fields are errors on the
other variant, naming the reference file. The build publishes one variant:
the one tagged with the site's language, else the untagged file, else the
other language. It stages that file under `build/content/sequences/`.

Overall yield multiplies each step's yield of the product carried into the
next step and the final step's yield of the target. If several products carry
on, the first in product order supplies that step's yield. Display rounds to a
whole percent, with halves rounded up. The sequence page shows **Steps** and
**Overall yield**, a scheme of linked compounds and steps, a list linking the
procedures with entry numbers where needed, reaction type, yield and status,
then the notes. `/sequences/` lists sequences by ID with title, target, step
count and overall yield. Sequence pages are absent from the search index.

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

A key declared under `fields.procedure` is checked as a procedure field
and produces no `unknown field` warning.

Any other top-level key produces an `unknown field` warning. This includes
misspellings such as `checkedby` and the fields `product`, top-level
`yield_percent`, `precursors` and `structure_image`. An unknown key in a
`products` entry produces a warning such as `products[1].colour`.

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

Set declared procedure fields on additional `#+HUGO_CUSTOM_FRONT_MATTER:`
lines before `:products`, for example after `:scale`:

```org
#+HUGO_CUSTOM_FRONT_MATTER: :notebook "AE-1/1" :project "first-year-practical" :working_time 3 :inert_atmosphere false
```

Double-quote strings; leave numbers and booleans unquoted. A multiple choice
uses a quoted list, for example `:project '("first-year-practical" "advanced-practical")`
when the collection declares `project` with `multiple = true` and uses the
demo registry’s `projects` vocabulary.

The ox-hugo/tomelr export cannot preserve every quoted string as text. It
writes a string without quotes when it reads `true` or `false`, has the form
of a date or date-time (`2026-01-01`, `2026-01-01T10:00:00+01:00`), or is an
integer: an optional sign followed by digits and underscores (`1234`, `-7`,
`7_000`, `0012`). This applies even to quoted source values and entries in
lists. Such values cannot be text, choice keys or multiple-choice entries
in an Org source. Validation reports `must be a string`, or the exported
front matter fails to parse; for example, unquoted `0012` is invalid TOML.
If authors use Org, choose patterns and vocabulary keys that avoid these
forms. Markdown sources have no such limit.

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

`reaction_types` contains exactly one slug, a key such as `esterification`,
from the registry's `reaction-types` vocabulary. Use the same slug in front
matter in every language. Create and edit reaction types in the lab
application. A procedure naming a key the registry does not contain fails
validation with:

```text
unknown reaction type "<value>"; the registry has no such reaction type
```

The demo registry contains these reaction types:

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

An English site shows the term's `label`. A German site shows `label_de`
when supplied, otherwise `label`. The `/reaction_types/` list and the
catalogue's reaction-type filter sort by the displayed label. Reaction
types have one level.

A registry with no reaction-type terms gives the collection none, so each
procedure's reaction type is unknown. A collection containing only
substances still validates. A declared procedure choice field may name
`vocabulary = "reaction-types"` like any of the other registry vocabularies.
A malformed snapshot is a configuration error; both `orgsyndb validate` and
`build` fail on it.

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
  `tags`, `products`, `substrates`, `scope`, `scheme_image` and every declared
  procedure field;
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

For a declared procedure field, a changed value, a missing key or an added
key produces an error under that key:
`must equal the value in <path of the reference variant> (<value>); the variants of a procedure share it`.
Repeat values without translating them. The displayed field label comes
from `label_de` on a German site when supplied.

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
Product yields in `products` or `scope` and scope temperatures stay TOML
numbers with a decimal point in every language; a German site shows them
with a comma. Molar mass comes from the registry and also uses the site’s
decimal separator.

## Reading validator output

Run the validator with at least one Markdown content root:

```text
tools/validate.py [--settings FILE] [--static-dir DIR] [--registry FILE] [--sequences DIR] CONTENT_ROOT...
```

Each positional `CONTENT_ROOT` is a directory of Markdown procedures.
`--static-dir` defaults to `static` in the current directory.
It resolves a procedure's `scheme_image` under that directory.
`--registry` defaults to `build/registry.json` in the current directory.
It takes a snapshot file, not an address. The validator checks procedure
and sequence compound keys, reaction types and declared procedure values
against that snapshot. It checks no substance values. An unreadable file
or a file that is not a snapshot is a configuration error, exit status 2.
`--compounds` and `--vocabulary` are not accepted; either is a usage error,
also exit status 2.

`orgsyndb validate` reads the registry named by the collection, keeps it in
`build/registry.json`, exports Org sources, then passes
`--settings orgsyndb.toml --static-dir static --registry build/registry.json --sequences md/sequences`
and the existing procedure roots `build/export` and `md/procedures` from
the collection root.

`--settings` names the collection's `orgsyndb.toml`. Without the option,
the validator uses `orgsyndb.toml` in the working directory; a missing
default declares no extra fields. A file explicitly named by `--settings`
must exist. The validator checks procedure declarations against the four
registry vocabularies, then checks each procedure's declared values. Org
procedures reach this check as Markdown exports.

`--sequences` defaults to `md/sequences` in the working directory. A missing
directory holds no sequences; an existing path that is not a directory is a
configuration error. Sequence steps resolve against procedures from the
positional content roots, and targets resolve against the compound registry.

Each problem is one line on standard output:

```text
<path>:<field>: <severity>: <message>
```

The field is normally a front-matter key. Product fields use dotted names,
such as `products[1].yield_percent`, counting products from 1. A non-table
entry is reported under `products[n]`. A registry error uses the snapshot
path as passed to `--registry` and field `substances`: a substance keyed
`group` conflicts with the group tabs. Change its key in the lab application.
Other possible fields are `file_name`, `front_matter`, `toml` and `body`.

Declared procedure-field errors name the Markdown source or Org export
and the declared key, such as `notebook` or `project`. Look up their type,
pattern, bounds and choice messages under
[Procedure field declarations](#procedure-field-declarations). An
`also set by` message names other procedure IDs; a `must equal the value in`
message names the reference language variant whose value you must repeat.

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
is reported as `unknown compound "<key>"; the registry has no substance of this key`.
Check the spelling and the substance in the lab application. `lists <key>
twice` means a duplicate product or substrate; `<key> is also a product`
means a starting material repeats a product.

`orgsyndb export` prints Org-source problems on standard output in the same
line format. Its fields can also be Org keywords such as `#+CREATED`,
properties such as `#+PROPERTY` or `:EXPORT_DATE:`, and drawers such as
`:LOGBOOK:`.

An `error` means a procedure, sequence or registry is invalid. A `warning`
identifies a problem that does not make validation fail, such as a missing
body section or an
unknown field. After the problem lines, the validator writes a summary to
standard error. The file count includes procedures and sequence files,
including all language variants; it counts no substances or snapshot file.
For the demo collection, including existing Org exports:

```text
validated 24 files: 0 errors, 0 warnings
```

The first three lines below are real validator output. The last is the same
line form produced by `orgsyndb export` for an Org source:

```text
tests/fixtures/invalid/yield-out-of-range/OSDB-0110-yield-out-of-range.md:products[1].yield_percent: error: 104.5 must be between 0 and 100
tests/fixtures/invalid/unknown-compound/OSDB-0123-unknown-compound.md:products[1].compound: error: unknown compound "no-such-compound"; the registry has no substance of this key
tests/fixtures/warn/missing-section/OSDB-0151-missing-section.md:body: warning: missing section "Notes"
tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org:#+CREATED: error: weekday "Tue" does not match 2026-10-19 (Mon)
```

The exit status tells a calling command whether validation succeeded:

| Exit status | Meaning |
|---|---|
| `0` | No errors were found. Warnings may still have been printed. |
| `1` | At least one procedure, sequence or registry error was found. |
| `2` | The invocation or validator configuration is invalid, such as no root, a root that is not a directory, a missing explicitly named settings file, invalid settings or declarations, or an unreadable or malformed registry snapshot. |

Usage and configuration failures are written to standard error and include
`validate.py: error:`; standard output is empty. The validator suppresses
checks that depend on a missing or malformed value, so one mistake does
not usually produce a chain of secondary messages.

### Sequence messages

Sequence problems use the sequence file's path, such as
`md/sequences/SEQ-0002-biphenylyl-ethanol.md`, with fields `steps[n]` or
`steps[n].<key>`; step numbering starts at 1. The table gives message text or
the identifying part of a longer message. Date and TOML errors use the same
rules as procedures.

| Field | Message | What to correct |
|---|---|---|
| Any required key | `required field missing` | Add the key from the sequence field table. |
| `id` | `must match SEQ-NNNN` or `must be between SEQ-0001 and SEQ-9999` | Use `SEQ-` and four digits from `0001` through `9999`. |
| `id` | `duplicate id <id>, also used by <path>` | Assign a free ID; one file per language code, and one untagged file, may share it. |
| `slug` | `must be "<value>" (the lowercased id)` | Use the lowercase `id`. |
| `file_name` | `must be named SEQ-NNNN-short-slug.md` or `does not match id <id>` | Correct the file name or its ID. |
| `target` | `unknown compound "<key>"; the registry has no substance of this key` | Correct the key or add the substance in the lab application. |
| `steps` | `must list at least two steps` | Add enough steps to describe a sequence. |
| `steps` or `steps[n]` | `must be an array of tables` or `must be a table` | Use the TOML forms shown above. |
| `steps[n].procedure` | `<id> not found in any content root` | Use an existing procedure ID; include its directory in a direct validator call. |
| `steps[n].entry` | `OSDB-NNNN is a general procedure; name one of its entries 1 to <count>` | Add the chosen scope entry number. |
| `steps[n].entry` | `OSDB-NNNN has no scope entries; remove entry` | Remove `entry` for a specific procedure. |
| `steps[n].entry` | `must be between 1 and <count>, the number of an entry of OSDB-NNNN's scope` | Choose an existing entry as an unquoted integer. |
| `steps[n]` | `starts from none of the products of step <k> (<keys>)` | Check step order and the selected entries' starting materials and products. |
| `target` | `<key> is not a product of the last step, step N` | Check the target and final procedure or entry. |
| `target` or `steps` | `must equal the value in <path>` | Keep the same target and ordered steps in every variant. |
| `authors`, `tags` or `reaction_types` | `must not be set; a sequence joins no procedure taxonomy` | Remove the key; the steps' procedures carry these. |
| Any other key | `unknown field` | Remove or correct the key. |
