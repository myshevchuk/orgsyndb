## Context

This is change 5. Changes 1–4 are archived, and their specs in
`openspec/specs/` govern everything this change does not modify.

The site is a single-language Hugo project. Procedures come from two
mounted trees, the Org export and the Markdown sources, and the validator
fixes eight English section headings. All interface strings are literal
English text in the layouts, the site script and the print stylesheet.

A first version of this change built an English site at `/` and a German
one under `/de/`, linked by a language switch, with each language listing
only its own procedures. The owner's review replaced it with the design
below: one site language, German by default, and every procedure on it.

## Goals / Non-Goals

**Goals:**

- The site, its search and its PDFs work entirely in German, or entirely
  in English.
- Every procedure is published whatever languages its files are in.
- A co-worker can write a procedure in German, in either format, and have
  it validate cleanly.
- Variants of one procedure cannot drift apart in the facts that do not
  depend on language.

**Non-Goals:**

- A language switch, or English and German sites side by side.
- Languages other than German and English. The code keeps a language
  list, so adding one is strings, sections and a template.
- A per-collection language. The locale belongs to the application's site
  configuration, as the owner asked.
- Machine translation or any check that a translation's prose matches the
  original.
- Localised URL paths; paths stay English.

## Decisions

### D1 One site language from `locale`

`site/hugo.toml` sets `locale = "de"`; the program reads its language
subtag (`de` from `de` or `de-AT`) and refuses a locale outside the
language list. The generated overlay sets `defaultContentLanguage` to it,
so Hugo picks `i18n/<language>.toml` and writes `<html lang>`. The
configuration has no `languages` table.

Rejected: a key in `orgsyndb.toml`. The owner asked for the site's TOML
file; one setting for all collections is also what an installation for
one group needs.

### D2 Variants by file name, chosen and staged before Hugo

`OSDB-0001-x.org` has no code; `OSDB-0001-x.de.org` and
`OSDB-0001-x.en.md` carry one. The build reads every validated content
file, groups them by `id`, and picks per ID: the file tagged with the site
language; else the untagged file; else the other tagged files in language
order. It copies the chosen files into `build/content/procedures/` under
their base names without the code, adding `language = "<code>"` to a
tagged file that lacks the field, and mounts that directory alone as
`content/procedures`. PDFs use the same choice, named after the chosen
source file.

Staging keeps Hugo single-language: Hugo would otherwise read `.de` and
`.en` in file names as its own language suffixes. Because Org replaces an
export file name's extension, `export.el` passes
`#+EXPORT_FILE_NAME: <stem>.md` so `OSDB-0001-x.de` keeps its code.

Rejected: mounting both source trees, as before. Two variants of one ID
would be two pages at one URL.

### D3 Variants share their facts

An ID may occur once per code and once without one. The reference variant
is the untagged file, else the first tagged one in language order (`de`
before `en`). Every other variant must have the reference's base name and
the same value, or absence, of `status`, `reaction_types`, `tags`,
`yield_percent`, `precursors`, `structure_image` and `product.formula`,
`product.mw`, `product.smiles`, `product.cas`. Each mismatch is an error
on that variant, naming the reference. Tags are shared, not translated:
they are identifiers, and `sample-data` drives the banner.

### D4 The `language` field

Optional, `"de"` or `"en"`. It must match the file name's code when both
exist. It chooses the section names of an untagged file. A procedure page
whose `language` differs from the site's carries `lang` on its header and
article, so the change of language is marked for readers and assistive
software. Hugo's own `lang` front-matter key was removed in Hugo 0.144 and
now fails the build, hence the longer name.

### D5 Sections, tables and numbers

German bodies use `Zusammenfassung`, `Reagenzien`, `Durchführung`,
`Aufarbeitung und Reinigung`, `Charakterisierung`, `Anmerkungen`,
`Gefahren und Entsorgung`, `Literatur`. A file's set is chosen by its
code, else its `language`, else whichever set gives the fewer problems.
German Reagents columns are `Reagenz | CAS | M (g/mol) | Menge | mmol |
Äquiv.`; the table hook marks `M (g/mol)` and `Äquiv.` numeric. `scale`
accepts a decimal comma; front-matter numbers keep a decimal point and a
German site prints them with a comma.

### D6 Interface strings

Every visible layout string is a key of `site/i18n/de.toml` and
`site/i18n/en.toml`, looked up with `T`; the site pages of `site/content/`
name their title by a `title_key`. Status values are shown through
`status_<value>` keys, so `draft` reads `Entwurf` while the badge class
and stored value stay English. Reaction-type labels live in the
vocabulary as `label_de` beside `label`, and lists sort by the shown
label. Pagefind filter names are strings too. The copy button carries its
messages in data attributes, so `site.js` holds no language. The per-page
`@page` rule, which sets the running header, also sets the footer text.

### D7 German stubs and templates

`new --lang de|en` uses that language's template and writes
`OSDB-NNNN-<slug>.<code>.<ext>`; without `--lang` the stub is the English
template without a code, as before. A German title's slug writes umlauts
and ß out (`Größe` → `groesse`).

### D8 Documentation

German readers get German versions of the co-worker guide, the Org guide
and the schema reference, next to the English ones with a `.de` suffix.
The README, the decision record and the specs stay English.

## Risks / Trade-offs

- [Existing English installations turn German] → The shipped locale is
  `de`, as the owner asked; `locale = "en"` restores an English site, and
  untagged English procedures publish unchanged in either.
- [A procedure on a German site may be in English] → Its page carries
  `lang="en"` when its language is known; tagging or the `language` field
  makes it known.
- [Shared tags read English on German pages] → Accepted; tags are search
  identifiers.
