## Context

The site is static, built by Hugo; the lab application is Django,
served under `/lab/` on the same host, and already links the site's
stylesheets collected from the same checkout. Each side renders its
own header. site-build forbids a `site/data/` directory: every Hugo
data entry comes from the collection.

## Goals / Non-Goals

**Goals:** one definition of the menu; every lab page that is a list
or an overview reachable from it; a shell that does not move between
the site and the application; specs without layout or menu items.

**Non-Goals:** sub-entries for a section's own tabs (the inventory's
lists, the registry's vocabularies, the procedure tabs) stay on their
pages; a footer on the application's pages; the wider pass over
layout in other specs, logged in `openspec/STATE.md`.

## Decisions

**The menu lives in `site/hugo.toml` as Hugo's own menu `main`.** A
data file is ruled out by site-build, and a Hugo menu needs no
template machinery: entries have `identifier`, `url`, `weight`,
`parent` and `params`. Each `identifier` is the key of its text in
`site/i18n/`. The application parses both TOML files with `tomllib`,
once per process. Two definitions with a parity test was the
alternative; it still lets a change touch one copy, and the test
would need a Hugo build inside the application's suite.

**Groups are entries with children.** A group has no `url`; its links
name it as `parent`. The markup is the same on both sides: a top-level
`ul` whose items are links, or a group's label in a `span` followed by
a nested `ul`. A label is not a heading, so the page's heading order
still starts at its `h1`.

**Whether a link belongs to the lab follows from its URL.** A build
without the lab drops every link under `/lab/` and every group left
empty, so the menu needs no flag that could disagree with the URL.

**Sections are path prefixes in `params.paths`.** The procedures link
lists `/procedures/`, `/general-procedures/`, `/reaction_types/`,
`/tags/` and `/authors/`; each lab view lists its own subtree. The
overview at `/lab/` lists none, since every lab path begins with it.

**The sidebar is a grid on `body` in `screen.css`.** Two columns,
the header in the first, sticky at the top and scrolling on its own
when taller than the window; `main` and the footer in the second.
Below 55rem the grid becomes one column and the header stacks above
the content, its groups wrapping as rows. Paper is untouched:
`print.css` already hides the header. The framed summary sets its
`body` back to a block.

**Search in the sidebar on every page.** The owner chose this over a
search bar above the content. The application's pages get the
site's default form, searching procedures; the catalogues keep their
own forms as before. The field fills the 17rem sidebar, its button a
magnifier inside the field's end. That leaves about 205 CSS pixels of
text at 1280, so the longer hints shorten: `Produkt, CAS oder SMILES`
measures 171, `Name, Formel, CAS, SMILES` 181 and
`In diesen Vorschriften` 144.

**The account sits after the menu, and in the title's row on narrow
windows.** On a wide window it is at the foot of the sidebar, where it
moves nothing. On a narrow one the header stacks, so the account
shares the title's row, which has a fixed height, and `main` starts at
the same place on the site's pages and the application's.

## Risks / Trade-offs

- The application now reads two files of the site at run time; the
  image must copy them, and a missing file fails at the first request
  rather than at build time → the shell tests read the real files, and
  the image test checks the `COPY` lines.
- A shorter hint names less of what the search matches; keywords and
  formulas still match, and the field's label is unchanged.
- A sticky sidebar taller than the window scrolls separately → only
  on short windows with every group shown.
