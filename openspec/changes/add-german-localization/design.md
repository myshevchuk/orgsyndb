## Context

This is change 5. Changes 1–4 are archived, and their specs in
`openspec/specs/` govern everything this change does not modify.

The site is a single-language Hugo project. Procedures come from two
mounted trees, the Org export and the Markdown sources, and the validator
fixes eight English section headings. All interface strings are literal
English text in the layouts, the site script and the print stylesheet.

## Goals / Non-Goals

**Goals:**

- A German reader can browse, search and print the site in German.
- A co-worker can write a procedure in German, in either format, and have
  it validate cleanly.
- An English procedure and its German translation cannot drift apart in
  the facts that do not depend on language.
- The English site keeps its URLs, texts and behaviour.

**Non-Goals:**

- Languages other than English and German. The code keeps a language list
  so that adding one is a data change plus strings and sections, but this
  change ships only `de`.
- Machine translation or any check that a translation's prose matches the
  original.
- Showing an English procedure on the German lists when it has no
  translation (content fallback).
- Localised URL paths (`/de/vorschriften/`); paths stay English.

## Decisions

### D1 Hugo multilingual mode, English at the root

`site/hugo.toml` declares `languages.en` (weight 1) and `languages.de`
(weight 2), `defaultContentLanguage = "en"`,
`defaultContentLanguageInSubdir = false` and
`disableDefaultLanguageRedirect = true`. English pages keep their URLs;
German pages live under `/de/`. Hugo's redirect page at `/en/` is
suppressed because it is not a page of the theme and would break the page
shell contract.

Rejected: a per-collection language setting in `orgsyndb.toml`. A group
with readers of both languages would have to pick one, and translated
procedures could not coexist.

### D2 The language is part of the file name

`OSDB-0001-x.md` is English and `OSDB-0001-x.de.md` German, for Org
sources as well. This is Hugo's own translation-by-file-name convention,
so the two files become translations of each other without any front
matter. The validator reads the code from the name; `.en` is refused (the
default language has no code), and so is any code outside the language
list.

Because Org replaces the extension of an export file name,
`export.el` passes `#+EXPORT_FILE_NAME: <stem>.md`; a bare
`OSDB-0001-x.de` would be exported as `OSDB-0001-x.md`.

Rejected: a `lang` front-matter field. It would need a schema field, an Org
keyword and an export mapping, and would still need distinct file names.

### D3 IDs are unique per language; translations share their facts

An ID may appear once per language. When an ID has a file in the default
language, every other file with that ID is a translation and must have the
same base name (`OSDB-0001-x`) and the same value, or absence, of
`status`, `reaction_types`, `tags`, `yield_percent`, `precursors`,
`structure_image` and `product.formula`, `product.mw`, `product.smiles`,
`product.cas`. Each mismatch is an error on the translation, naming the
original. Free per language: `title`, `product.name`, `scale` (decimal
comma), `hazards`, `references`, `authors`, `checked_by`, `ai_model`,
`date`, `lastmod` and the body.

Tags are shared, not translated: they are identifiers, the
`sample-data` tag drives the banner, and a shared set keeps the two tag
taxonomies parallel.

Rejected: requiring a translation for every procedure. Real collections
will be mostly English; translation is optional.

### D4 German sections and table columns

German bodies use `Zusammenfassung`, `Reagenzien`, `Durchführung`,
`Aufarbeitung und Reinigung`, `Charakterisierung`, `Anmerkungen`,
`Gefahren und Entsorgung`, `Literatur`, with the same rules as the English
ones. The Reagents columns are `Reagenz | CAS | M (g/mol) | Menge | mmol |
Äquiv.`; the table hook marks `M (g/mol)` and `Äquiv.` as numeric columns
too. German text uses decimal commas, and `scale` accepts them
(`^\d+([.,]\d+)?\s+\S+$`); front-matter numbers stay TOML numbers with a
decimal point, and the German panel prints them with a comma.

### D5 Interface strings in Hugo's i18n files

Every visible string of the layouts is a key of `site/i18n/en.toml` and
`site/i18n/de.toml`, looked up with `T`. Status values are shown through
`status_<value>` keys, so `draft` reads `Entwurf` on German pages while the
badge class and the stored value stay English. Reaction-type labels live
in the vocabulary as `label_de`, beside `label`, so that the list of types
stays in one file; the label partial falls back to `label`. Pagefind
filter names are interface strings too (`Reaktionstyp`, `Schlagwort`,
`Autor`, `Status`). The copy button carries its two messages as
`data-copied` and `data-selected` attributes, so `site.js` holds no
language. The per-page `@page` rule, which already sets the running
header, also sets the footer text; `print.css` keeps the English footer
for pages without that rule.

### D6 Cross-language links

The language switch lists `.Translations`, so it appears only where a
translation exists. Precursor and used-in links use the current language's
page of an ID and fall back to the page in another language, marked with
`hreflang`, so a German page never loses a link because its precursor is
not translated yet. Lists, taxonomies and search show only the current
language's procedures (no content fallback, see Non-Goals).

### D7 Search per language

Pagefind already splits its index by the `lang` attribute of `<html>`;
the layouts now set it from the page's language. The German UI of
Pagefind is chosen automatically from the same attribute.

### D8 German stubs and templates

`new --lang de` uses `templates/procedure.de.org` or `.de.md`, which carry
the same anchor lines as the English templates, German comments and
section headings, and writes `OSDB-NNNN-<slug>.de.<ext>`. The slug of a
German title writes umlauts and ß out (`Größe` → `groesse`) before the
usual ASCII folding.

### D9 Documentation

German readers get German versions of the co-worker guide, the Org guide
and the schema reference, next to the English ones with a `.de` suffix.
The README, the decision record and the specs stay English.

## Risks / Trade-offs

- [An English-only collection shows an empty German section] → The
  language switch only appears where a translation exists; the German home
  is reachable from English pages that have a German twin (home, lists,
  taxonomy pages), and states the count of German procedures.
- [Shared tags read English on German pages] → Accepted; tags are search
  identifiers, and translating them would split the taxonomy.
- [Two places to change a shared fact] → The validator reports every
  disagreement as an error, so a build cannot publish drifting facts.
