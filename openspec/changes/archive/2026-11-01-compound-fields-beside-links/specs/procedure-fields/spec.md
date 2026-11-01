## MODIFIED Requirements

### Requirement: Procedure field declarations
A collection SHALL declare the fields its procedures carry beyond the procedure schema in its `orgsyndb.toml`, as the array of tables `fields.procedure`, one table per field, in the order the site shows them. A collection whose `fields` holds no `procedure` declares no procedure field. A declaration holds the keys of a compound field declaration (compound-fields "Field declarations"), with the same meanings, defaults, types and vocabularies, except:
- it takes neither `column`, nor `search`, nor `tabs`, nor `beside`;
- for a `boolean` or `choice` field, `facet = true` makes the field a filter of the procedure catalogues (site-catalogue "Catalogue controls");
- `required` and `unique` concern procedures, not compounds: under `required` every procedure sets the field, and under `unique` no two procedures set the same value;
- its `key` matches `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, does not end in `_de`, no other declaration of `fields.procedure` has it, and it is none of these reserved keys:
  - the keys of the procedure schema: `id`, `slug`, `title`, `date`, `lastmod`, `authors`, `status`, `reaction_types`, `tags`, `products`, `scale`, `hazards`, `substrates`, `scope`, `scheme_image`, `checked_by`, `references`, `ai_model`, `language`, `draft`, `description`, `aliases`, `weight`, `author` and `url`;
  - the other front-matter keys Hugo reads for itself, written in lower case: `build`, `cascade`, `expirydate`, `headless`, `iscjklanguage`, `keywords`, `kind`, `lang`, `layout`, `linktitle`, `markup`, `menu`, `menus`, `modified`, `outputs`, `params`, `path`, `pubdate`, `publishdate`, `published`, `resources`, `sitemap`, `sites`, `summary`, `translationkey`, `type` and `unpublishdate`, and the weight Hugo reads for each taxonomy, `authors_weight`, `reaction_types_weight` and `tags_weight`;
  - the record keys and address parameters of the procedure catalogue that these lists do not already name: `tag`, `created`, `text`, `q`, `sort` and `view`.

A procedure field and a compound field may have the same key. The vocabularies a procedure field names are those of compound-fields "Vocabularies", shared with the compound fields.

#### Scenario: The fixture declarations are accepted
- **WHEN** a procedure-field run makes no change
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Facets on a boolean and a choice field
- **WHEN** a procedure-field run adds `facet = true` to the declarations of `inert_atmosphere` and `project`
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: One key for a compound and a procedure field
- **WHEN** a procedure-field run adds to its `orgsyndb.toml` a `[[fields.compound]]` declaration with `key = "notebook"`, `type = "text"` and `label = "Notebook"`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Procedure declaration errors are configuration errors
The validator SHALL exit with status 2, print nothing to stdout, and write `validate.py: error:` and a message to stderr when its settings file breaks a rule of the requirement "Procedure field declarations", as compound-fields "Declaration errors are configuration errors" states for the compound declarations. In particular this holds when `fields.procedure` is not an array of tables; when a declaration lacks `key`, `type` or `label`, has a value of the wrong type, or holds a key that is unknown, that its type does not take, or that is `column`, `search`, `tabs` or `beside`; when a `key` breaks its pattern, ends in `_de`, is reserved or is declared twice in `fields.procedure`; and when a `pattern`, a bound or a vocabulary breaks the rules of the compound declarations. The message names the settings file or the vocabulary file, the field's key when the declaration has a valid one, and the offending key or value; a message about a declaration's `key` also names `fields.procedure`.

#### Scenario: Options a procedure field does not take
- **WHEN** a procedure-field run adds `column = true` to the declaration of `notebook`; separately, adds `search = true` to the declaration of `notebook`; separately, adds `tabs = true` to the declaration of `project`; and separately, adds `beside = true` to the declaration of `working_time`
- **THEN** each exits 2, stdout is empty, and stderr contains `validate.py: error:` and, respectively, `notebook` and `column`, `notebook` and `search`, `project` and `tabs`, and `working_time` and `beside`

#### Scenario: Reserved keys
- **WHEN** a procedure-field run adds a declaration with `type = "text"`, `label = "X"` and, in three separate runs, `key = "status"`, `key = "layout"` and `key = "tag"`
- **THEN** each exits 2, and stderr contains `fields.procedure` and, respectively, `status`, `layout` and `tag`

#### Scenario: A key declared twice
- **WHEN** a procedure-field run adds a second declaration with `key = "notebook"`, `type = "text"` and `label = "Notebook"`
- **THEN** it exits 2, and stderr contains `notebook` and `fields.procedure`

#### Scenario: A single table instead of an array
- **WHEN** a test runs the validator with `--settings` naming a settings file that holds `format = 1` and one `[fields.procedure]` table with `key`, `type` and `label`
- **THEN** it exits 2, and stderr contains `fields.procedure`

#### Scenario: A missing vocabulary
- **WHEN** a procedure-field run sets `vocabulary = "no-such-vocabulary"` in the declaration of `project`
- **THEN** it exits 2, and stderr contains `no-such-vocabulary`
