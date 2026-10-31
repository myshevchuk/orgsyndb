## Context

The compound catalogue is one page, `/compounds/`, made by
`site/layouts/compounds/section.html`; compound pages come from a Hugo
content adapter at `/compounds/<key>/`. Each row carries its facet
values, a value of a vocabulary flattened with its ancestors. The
procedure section has tabs (`site/layouts/_partials/section-tabs.html`)
and term pages, static pages that scope the procedure catalogue to one
term.

## Decisions

- **One field drives the tabs, by an option on its declaration.** Tabs
  are one division, so a second tabs field has no meaning; `tabs =
  true` keeps the choice beside the field's other options, where the
  validator already checks types.
- **Only top-level values become tabs.** Lower levels stay as filters
  inside a tab, so a deep classification does not become a long row of
  tabs.
- **Tab pages are static pages with their own rows.** A tab page is
  built from the compounds filed under its value, so it works without
  JavaScript, can be linked, and its counts and facets describe only
  those compounds. The catalogue's fixed facet, which a term page uses,
  is not needed: no row outside the tab exists on the page.
- **The tab's value leaves its own facet.** Every row of the tab
  carries it, so ticking it would change nothing; the levels below it
  move one step out, as they now head the tab's tree.
- **`/compounds/<field key>/<value>/`.** The field's key keeps tab
  pages apart from compound pages, which sit at `/compounds/<key>/`.
  A compound key can equal a field key only when the field key is one
  word, and the validator refuses that case.
- **Tab links carry no state.** Switching tabs starts the catalogue
  afresh, as the procedure section's tabs do; a query or filter that
  suits one tab may name values another tab does not have.
- **The demo gets a field for its internal scheme.** The chemical
  classes are a chemist's classification and already filter; a group's
  own scheme — bought or made — is what tabs are for.

## Alternatives rejected

- **A settings key naming the tabs field** (`[compounds] tabs =
  "group"`). A second place to check the field's type and existence,
  for no gain over the option.
- **One tab per value at every level.** Floods the tab bar and repeats
  what the facet already does.
- **Tabs as client-side filters on one page.** Would need JavaScript
  and give no page to link.
- **Tab pages at `/compounds/<value>/`.** Value keys and compound keys
  share one shape, so a value could take a compound's address.
