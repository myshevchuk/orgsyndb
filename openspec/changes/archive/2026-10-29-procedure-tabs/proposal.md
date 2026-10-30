## Why

The reaction-type directory has its own navigation link, which its term
pages mark as the current section, while the tag and author directories
are reached only from the home page, the foot of a collapsed facet and
the scope line of their term pages, and mark Procedures. Yet all three
are classifications of the same procedures, and their term pages are the
same catalogue with one facet fixed. The site navigation should name the
kinds of page the site holds; the ways into the procedures belong inside
the Procedures section, side by side.

## What Changes

- The site navigation links only to `/procedures/` and `/help/`.
  Every procedure page, the three taxonomy pages and their term pages
  lie in `/procedures/`.
- The catalogue, the three taxonomy pages and every term page open their
  `main` with section tabs: `All procedures`, `Reaction types`, `Tags`
  and `Authors`. The tab of the page itself is marked as the current
  page; a term page marks its taxonomy's tab.
- The scope line of a term page drops its directory link, which the
  tabs now carry.
- The print check that the navigation is not printed looks for the new
  navigation texts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-theme`: the page shell's navigation and current section, the
  new section tabs, and the links to the taxonomy pages.
- `site-catalogue`: the scope line of a term page.
- `localization`: the German navigation and tab texts.
- `print-layout`: the navigation texts the PDF check looks for.

## Impact

- Layouts: `site-header.html`, a new `section-tabs.html` partial,
  `catalogue.html`, `taxonomy.html`; both i18n files; `screen.css`.
- Tests: the page shell, the current section, the tabs, the scope line
  in both languages, the PDF chrome check.
- Docs: `README.md` and the help pages where they describe the
  navigation.
