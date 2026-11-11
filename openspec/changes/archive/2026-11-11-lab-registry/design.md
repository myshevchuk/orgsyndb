## Context

The application reads compounds from the collection index
(`orgsyndb_web.index`): `compound_for(token)` resolves a compound key or
the value of a unique text field, such as an item number, to a
compound. Items carry `inventory`, `article_number` and a typed `name`;
lots carry `inventory` and `article_number`; a task names its `product`
as free text. Planning (`planning.plan`) groups items of one article
number into an article, matches a task to it through `compound_for` or
equal text, takes molar masses from the compound, and pairs a task with
a lot by equal batch. The demo data set names compounds of
`examples/demo` by key and item number and warns when the index lacks
them; the application image holds `webapp/` only, not `examples/`.

The design was settled with the owner in schema drafts kept outside the
repository; its rules that concern this change are:

- every article is exactly one substance; a substance need not be an
  article;
- a container size, an item, is the unit of the stock the lab delivers,
  has no article number of its own and is discontinued on its own;
- made or bought is a property of the lot, and one substance may have
  both;
- a lot fills only items of its own substance's article;
- substances, articles and every vocabulary are created and edited in
  the application only.

## Goals / Non-Goals

**Goals:**

- Substances and vocabularies in the application, referred to by
  foreign key from items, lots and tasks.
- One JSON document that holds the registry, served for the collection
  change that follows and loaded for the demo data.
- A way to fill the registry from an existing collection.

**Non-Goals:**

- The collection reading the registry: `compounds/`, `vocabularies/`,
  declared compound fields, the validator, the export, the site and
  Emacs stay as they are until the next change. Until then the two
  registries are kept apart and may disagree.
- Procedures, sequences, task steps, notebooks and the import of the
  collection: a later change. A task's `sequence` and its steps stay as
  they are, read from the index.
- Accounts, notebooks, issued ids and the latest import in the
  snapshot: they join it with the changes that need them.
- Carrying records over: the application has no users, so the
  migration empties the tables it reshapes.

## Decisions

### Two packages, one for substances and one for vocabularies

`registry.Substance`: `key` (`^[a-z0-9]+(-[a-z0-9]+)*$`, at most 100
characters, unique, fixed once set, the compound-file key rule),
`name` (required, at most 200), `name_de`, `short_name` (at most 50),
`group` (required foreign key to a group), `formula` (at most 100),
`mw` (decimal, greater than zero, three places, optional), `smiles`,
`cas` (the compound files' form and check digit, unique where given)
and `note`, with a change history. Its chemical classes are a
many-to-many relation through `registry.SubstanceClass`, a model of its
own so that the table diagram shows it; the form requires at least one
class, the table does not. A substance shows as `name_de` on a German
site when it has one, else `name`, as compounds do.

`vocabulary` holds four models with a change history each:
`ChemicalClass`, `Group` and `Project`, trees with an optional `parent`
of the same model, and `ReactionType`, flat. A term has `key` (the
substance key rule, at most 50, unique, fixed once set), `label` and
`label_de`. A term is never filed under itself or under a term filed
under it; the form and the admin check it. Foreign keys to terms
protect them, so a term in use cannot be deleted. Projects and reaction
types have no user in the application yet; they are here so that the
collection change finds every vocabulary in the registry.

The group vocabulary is the collection's `inventory-groups`; the
snapshot and `registry_import` use that name for it, the application
`Gruppen` (`Groups`), the label of the collection's declared field.

### Articles carry the article number

`inventory.Article` has the substance as its primary key
(`OneToOneField(primary_key=True)`), so an article is that substance and
a substance has at most one article; `article_number` (at most 30,
unique when given, fixed once set) and `category`, with a change
history. `inventory.Item` keeps size, unit, quantity, note, status,
stocked-on date, compartment and box, gains `article` (protected) and
loses `inventory`, `article_number`, `name` and `category`; its identity
is article, size and unit. An item shows as the article number,
container and substance name, or container and name without a number.

The item forms keep the fields people use there: the new-item form
names a substance by key and creates its article when it has none; both
item forms show the article's number and category and save them on the
article, for every size of it. The rules that an item without an article
number cannot be delivered, gets no consumption and has no forecast
become rules of the article.

Alternatives: an article page of its own with its own form. It would
duplicate the item page for the common case of one size and adds a
step; it can come later if articles gain more fields.

### Lots of any substance

`inventory.Lot` gains `substance` (protected), `source` (`made`,
`hergestellt`; `bought`, `gekauft`) and `supplier` (at most 100), and
loses `inventory` and `article_number`. Filling an item from a lot
needs the lot's substance to be the item's article's substance, as the
bookings check today for the article number. The bulk list shows every
open lot, of articles and of other substances, at its present address.
A lot's source is fixed once it is created.

### Tasks name a substance

`tasks.Task.product` (text) becomes `substance`, a protected foreign
key. The form takes a substance key, offered through a `datalist` of
the keys labelled with their names, and refuses an unknown key. Search
finds a task by its substance's key and names.

### Substance links

Wherever a substance shows, its name links to its page
`/lab/registry/substances/<key>/`. That page links to the site's
compound page `/compounds/<key>/` when the collection index lists the
key; the index keeps the compound keys for that alone, and
`compound_for` goes. The mark `nicht in der Sammlung` goes: every
substance is in the registry.

### The snapshot

`registry.snapshot.build()` returns the registry as a JSON-ready table:

```json
{"format": 1,
 "digest": "<sha256 hex>",
 "vocabularies": {
   "chemical-classes": [{"key": "...", "label": "...", "label_de": null,
                         "parent": null}],
   "inventory-groups": [...], "projects": [...],
   "reaction-types": [{"key": "...", "label": "...", "label_de": null}]},
 "substances": [{"key": "...", "name": "...", "name_de": null,
                 "short_name": null, "group": "...",
                 "chemical_classes": ["..."], "formula": null,
                 "mw": 148.16, "smiles": null, "cas": null,
                 "note": null, "article_number": null}]}
```

Substances are ordered by key, a substance's classes by key, and the
terms of a vocabulary so that a parent precedes the terms filed under
it and siblings follow in key order; empty text is `null`; `mw` is a
number. `digest` is the SHA-256 of the
table without `digest`, serialized with sorted keys, no spaces and
ASCII escapes, so the same registry always gives the same digest. As a
parent precedes its children, a loader can create terms in order. `GET /lab/registry/snapshot.json` serves it,
with no sign-in.

`manage.py registry_load FILE` fills an empty registry from a snapshot
in one transaction, articles with numbers included, and refuses a
registry that holds substances or terms, an unknown format, a broken
reference or a value a form would refuse. `manage.py registry_import
COLLECTION` builds a snapshot from a collection directory and loads it
the same way: `vocabularies/chemical-classes.toml`,
`inventory-groups.toml`, `projects.toml` and `reaction-types.toml`, and
`compounds/<key>.toml` with the declared fields `short_name`,
`chemical_class`, `group` and `item_number`; other declared fields and
`structure_image` are left out with a warning naming them. It is how
the owner's own collection moves into the application.

### The demo registry

`webapp/demo/registry.json` is the demo data set's registry: the
snapshot `registry_import` makes of `examples/demo`, plus the substance
`new-compound-7` (`New compound 7`, `Neuverbindung 7`) for the article
`NV-0007`, which names no compound of the collection. A test keeps the
file equal to that import plus the one addition, so the two cannot
drift until the collection change removes the collection's files.
`demo_data` loads it after the accounts, as the data set's first
changes, on the opening day and by `klehmann`, so that its history
follows the recorded past like every other record; `--replace` deletes
the registry with the other lab records. Item names no longer depend on the index's
language: they are the substances' names, and the warning about
compounds missing from the index goes.

### Migrations empty what they reshape

The `inventory` and `tasks` migrations delete every item, lot,
movement, delivery note, entered consumption and task with their
histories before they change the tables, so that no non-null column
needs a default and no value is guessed. The test server's demo data is
written again with `demo_data --replace` after the deploy.

### The table diagram

The grid gains the `registry` and `vocabulary` packages, each with a
colour of its own, and `inventory_article`. The declared links from a
lot's and a task's text to an item's article number go: both are
foreign keys now. The link from a task's batch to a lot's batch stays,
matching on equal batch and substance.

## Risks / Trade-offs

- [Two registries until the collection change] → The site and validator
  still read `compounds/`; a substance added in the application does
  not show on the site until then. The demo keeps both equal by test.
- [Article fields edited on item forms] → Editing the category of one
  size changes it for all sizes. The form says so beside the fields.
- [A long substance `datalist`] → A few hundred keys are fine for a
  `datalist`; a search field can replace it if the registry grows.
- [Emptying tables on migrate] → Only the test server holds data, demo
  data that the command writes again.
