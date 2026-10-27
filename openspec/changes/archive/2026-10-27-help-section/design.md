## Context

`/search/` hosts Pagefind's UI. The home page and the procedure lists
have plain GET forms whose action is `/search/`, so they depend on the
page. Dropping `/search/` outright would leave the three forms with no
results page; moving the Pagefind UI into the home page and the lists
would change both layouts and their no-JavaScript behaviour. The
narrower change is to drop only the navigation link.

## Decisions

- **Keep `/search/`, drop its navigation link.** Every search feature
  stays: free text, SMILES fragments, the four filters, `?q=`. A reader
  reaches the results page through any of the three forms.
- **Stage `docs/` in Python, not with a Hugo mount.** The documents
  link each other by repository file names (`SCHEMA.md`,
  `[[file:STYLE.de.md]]`) and link files that are not published
  (`../templates/procedure.md`). Goldmark render hooks could rewrite
  the Markdown links, but Hugo's Org renderer has no link hook, so a
  mount would leave the Org guides' links broken. Staging rewrites both
  formats with one tested function, and writes front matter Hugo can
  read uniformly.
- **Publish every language.** The site is built in one language, but
  the English guides link the German style guide and glossary, and
  every guide links its other-language version. Publishing only the
  site's language would break those links. The index puts the site's
  language first.
- **Staged names carry no language code.** `AUTHORING.de.md` is staged
  as `authoring-de.md`, so Hugo, built in one language, does not read
  `.de` as a content language (as `stage_content` already does for
  procedures).
- **Language of a document.** The code before the suffix (`de`, `en`);
  a document without a code is English, as every such file in `docs/`
  is. Any other code stops the build, since the index could not name
  the language.
- **Help pages are not indexed.** They carry no `data-pagefind-body`,
  as the site-build layout contract already requires of every page but
  a procedure page, so search results stay procedures only.
- **Highlighting by class.** Hugo's default inline Monokai colours put a
  dark block in a light page and ignore the theme's dark mode. With
  classes and no Chroma stylesheet, code shows in the theme's colours.
  No procedure in the demo or test collection has a code block, so
  procedure pages do not change.
