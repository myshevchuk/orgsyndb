## Context

The navigation names three destinations: Procedures, Reaction types and
Help. Tags and authors left it with the unified catalogue, on the ground
that they are catalogue facets; reaction types stayed, although they are
a facet too. Further changes add compounds and synthesis sequences, which
are not groupings of procedures but things of their own.

## Decisions

- **The navigation names kinds of page; tabs name ways into one kind.**
  A link of the site navigation leads to a section about one kind of
  thing: procedures, help, and later compounds and sequences. Reaction
  types, tags and authors group procedures, so they are tabs of the
  Procedures section.
- **Tabs on listing pages only.** The catalogue, the taxonomy pages and
  the term pages list procedures and carry the tabs. A procedure page
  does not: it is one procedure, and its panel already links its terms.
- **The tabs are a `nav`, not an ARIA tab list.** Each tab is a link to
  another page, so `role="tablist"` and its keyboard model would promise
  behaviour the page does not have. The current tab carries
  `aria-current` as the site navigation does.
- **The scope line loses its directory link.** The tab of the term's
  taxonomy leads to the same page, one line above. The facet's own
  directory link stays: it is part of the facet, which is hidden behind
  the Filters toggle on narrow windows.

## Alternatives rejected

- **Fold reaction types into Procedures without tabs.** Consistent, but
  it hides reaction types as deeply as tags and authors are hidden now.
- **A Browse navigation link to one page holding the three
  directories.** Term pages are catalogue pages, yet they would mark
  Browse; and the page repeats the home page's browse list.
- **All three taxonomies in the navigation.** Five German links beside
  the search form crowd the header, which has to keep one height on
  every page.
