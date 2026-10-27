# site-help Specification

## Purpose
Define the help section: the staging of the application's `docs/` into help pages, the rewriting of their links, the help index and the help pages.
## Requirements
### Requirement: Help pages staged from docs
Before it runs Hugo, `tools/orgsyndb build` SHALL call `pipeline.stage_help(<app>/docs, build/content/help)`. `stage_help(docs, target)` stages the application's documents as help pages and returns how many it staged:
- **Sources.** The sources are the regular files directly in `docs` whose names end in `.md` or `.org`, in name order. When `docs` does not exist, there are none.
- **Names.** `help_slug(name)` is `name` without its suffix, lowercased, with every `.` replaced by `-`: `AUTHORING-ORG.de.org` gives `authoring-org-de`. A source `<name>` is staged as `<help_slug(name)>.<suffix>`, its text being `help_page(name, text, names)` of its text read as UTF-8 (a byte-order mark is dropped), where `names` is the set of source names.
- **Target.** `target` is emptied and created first, and holds the staged files and nothing else afterwards.
- **Errors.** It raises ValueError, before writing anything to `target`, when two sources have the same slug (naming both), when a source name carries a language code other than `de` or `en` (naming the file and the code), or when `help_page` raises (naming the file).

The build stops with exit 1 on such an error, naming the problem.

#### Scenario: Slugs
- **WHEN** a unit test calls `help_slug` on `AUTHORING.md`, `AUTHORING.de.md`, `AUTHORING-ORG.de.org` and `GLOSSARY.de.md`
- **THEN** it returns `authoring`, `authoring-de`, `authoring-org-de` and `glossary-de`

#### Scenario: Staging a docs directory
- **WHEN** a unit test stages a directory holding `A.md`, `B.de.org`, `notes.txt` and a subdirectory `sub/` with `C.md`, into a target holding a stale file
- **THEN** it returns 2, and the target holds exactly `a.md` and `b-de.org`

#### Scenario: Staging errors
- **WHEN** a unit test stages a directory holding `A.md` and `a.md`; then one holding `A.fr.md`; then one holding `A.md` whose first line is not a title; each time into a target holding a stale file
- **THEN** each call raises ValueError, naming both files, the file and `fr`, and the file in turn, and the stale file is still in the target

#### Scenario: No docs directory
- **WHEN** a unit test stages a path that does not exist into a target holding a stale file
- **THEN** it returns 0 and the target exists and is empty

### Requirement: Help page text
`pipeline.help_page(name, text, names)` SHALL return the staged text of the document `name`, whose text is `text`, given the set `names` of all source names:
- **Title.** A Markdown document's first line is `# <title>`; an Org document has a line `#+TITLE: <title>` (the keyword in any case) before its first heading. That line is removed. A document without it raises ValueError.
- **Front matter.** The result begins with a TOML front matter block between `+++` lines holding exactly:
  - `title`: the title;
  - `help_group`: `"glossaries"` when `name` begins with `GLOSSARY`, else `"guides"`;
  - `help_base`: `help_slug` of the name without its language code, such as `authoring-org` for `AUTHORING-ORG.de.org`;
  - `help_language`: the language code of `name` (`de` in `AUTHORING.de.md`), or `"en"` when it has none.
- **Links.** The rest of the text follows unchanged except for its links. The links are Markdown inline links `[text](target)`, and Org bracket links `[[target][description]]` and `[[target]]`, where an Org target loses a leading `file:` before it is examined. For each link:
  - A target that begins with `#`, `/` or `*`, or with a URI scheme such as `https:` or `mailto:`, is left unchanged.
  - A target whose part before any `#` is in `names` becomes `/help/<slug>/`, followed by the `#` and the fragment when the target has one. An Org link without a description gets the original target, without `file:`, as its description.
  - Any other target is a file that is not published: the link is replaced by its text (Markdown), or by its description, else its target without `file:` (Org).
- **Code is left alone.** Nothing inside a Markdown fenced code block or code span, or inside an Org block (`#+begin_…` to `#+end_…`, in any case) or an Org `=verbatim=` or `~code~` span, is changed.

#### Scenario: Markdown page
- **WHEN** a unit test calls `help_page` with name `A.md`, names `A.md`, `B.de.md` and `GLOSSARY.de.md`, and a text whose first line is `# Writing things`, followed by the links `[B](B.de.md#x-y)`, `[glossary](GLOSSARY.de.md)`, `[template](../templates/p.md)`, `[web](https://example.org/a.md)`, `[top](#z)` and `[root](/help/)`, a code span `` `[c](B.de.md)` `` and a fenced code block holding `[d](B.de.md)`
- **THEN** the front matter has `title = "Writing things"`, `help_group = "guides"`, `help_base = "a"` and `help_language = "en"`, and the body has no `# Writing things` line
- **AND** the body links `/help/b-de/#x-y` and `/help/glossary-de/`, has the text `template` in place of the third link, and keeps the web, fragment and root links, the code span and the code block unchanged

#### Scenario: Org page
- **WHEN** a unit test calls `help_page` with name `GLOSSARY.de.org`, names `GLOSSARY.de.org` and `S.md`, and a text with `#+title: Glossar`, then `#+AI_MODEL: m`, then the links `[[file:S.md][the schema]]`, `[[file:S.md]]`, `[[file:../templates/p.org][the template]]`, `[[file:../x.org]]` and `[[https://example.org][web]]`, a span `=[[file:S.md]]=`, and a `#+BEGIN_SRC org` block holding `[[file:S.md]]`
- **THEN** the front matter has `title = "Glossar"`, `help_group = "glossaries"`, `help_base = "glossary"` and `help_language = "de"`, the `#+title:` line is gone and `#+AI_MODEL: m` stays
- **AND** the body has `[[/help/s/][the schema]]`, `[[/help/s/][S.md]]`, the texts `the template` and `../x.org` in place of the next two links, and the web link, the span and the block unchanged

### Requirement: Help index
The site SHALL publish `/help/` from `site/content/help/_index.md`, whose `title_key` is `title_help`, with the layout `site/layouts/help/section.html`. Its `main` holds:
- the `h1` with the display title, `Help`;
- a `p.lede` with the text `Guides to writing procedures, and glossaries.`;
- for each group that has help pages, first `guides` then `glossaries`, an `h2` reading `Guides` or `Glossaries`, followed by a `ul.help-list`. A group without help pages has neither.

The list holds one `li` per `help_base` of the group, in `help_base` order. The help pages that share a `help_base` are its versions. The `li` begins with a link to its preferred version, whose text is that page's title: the version in the site's language, else the English one, else the first by language code. The link carries `hreflang` with the version's language, and also `lang` when that differs from the site's language. After it, for each other version in language-code order, the `li` holds ` · ` and a link to that version whose text is the language's own name, `Deutsch` or `English`, carrying `hreflang`.

These texts are those of an English site; a German site shows `Hilfe`, `Anleitungen zum Schreiben von Vorschriften und Glossare.`, `Anleitungen` and `Glossare`, as the localization spec's interface-string rule requires. The language names are the same on both.

#### Scenario: English help index
- **WHEN** a test reads `public/help/index.html` of a theme build in locale `en`, whose application copy holds the repository's `docs/`
- **THEN** its `h1` is `Help`, it has the lede, and its `h2` headings are `Guides` and `Glossaries`, in that order
- **AND** each list has one `li` per base name of its group's documents in `docs/`, in base-name order, whose first link is the preferred version's page with that document's title and `hreflang`, and whose further links are the other versions with their language names

#### Scenario: German help index
- **WHEN** a test reads `public/help/index.html` of a German build of the test collection
- **THEN** its `h1` is `Hilfe` and its `h2` headings are `Anleitungen` and `Glossare`
- **AND** the first `li` of the guides links `/help/authoring-de/` with the title of `docs/AUTHORING.de.md` and `hreflang="de"`, then `/help/authoring/` with the text `English` and `hreflang="en"`

### Requirement: Help pages
Each staged help page SHALL be published at `/help/<slug>/` with the layout `site/layouts/help/page.html`. Its `main` holds one `article.help-page` whose `lang` is the page's `help_language`, and which holds the `h1` with the page's title followed by the rendered document. A help page carries no `data-pagefind-body`, so search does not index it: the site-build "Search index" page count stays the number of published procedures. Every link in it to a staged document leads to that document's help page, and a fragment to an element with that `id` there.

#### Scenario: Help pages of a build
- **WHEN** a test reads every page under `public/help/` except the index, of a theme build in locale `en` whose application copy holds the repository's `docs/`
- **THEN** there is one per document in `docs/`, at `/help/<slug>/`, each with one `article.help-page` whose `lang` is the document's language and whose `h1` is its title, and none has `data-pagefind-body`
- **AND** every `a href` in an article either has a URI scheme, begins with `#`, or resolves to a published help page, and a fragment resolves to an element with that `id` in the target page
- **AND** no `a href` ends in `.md` or `.org`, or contains `.md#` or `.org#`

