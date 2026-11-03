## Why

A compound page lists the procedures that make the compound in one step
(`Made by`), and a written synthesis sequence records the one route a
group actually uses. Nothing shows what the collection as a whole can
do: that the aspirin of OSDB-0002 can be made from methyl salicylate
because OSDB-0001 makes its salicylic acid, or that a compound has two
routes through a shared intermediate. Working that out means walking
from compound page to procedure page by hand, and a protection followed
by its removal turns that walk into a loop.

## What Changes

- The build derives, for every compound, the ways to make it from the
  published procedures: each procedure (or entry of a general
  procedure) that makes it, each of those needing all of its
  substrates, each substrate in turn with the procedures that make it,
  down to compounds no procedure makes. A step that starts from a
  compound already on the way from the page's compound down to it is
  left out, so cycles such as a protection and its removal are never
  followed. A depth limit of six steps stops the tree, and a budget of
  200 steps draws a larger tree to the largest depth that fits; a
  compound the limit cuts off is marked as having more steps on its
  own page.
- A compound page whose tree goes past one step gains a last section,
  `Routes` (`Herstellungswege`), drawing the tree as nested lists: each
  step as the `Made by` list writes it (link, entry, yield, status
  badge), each compound as a compound link with its note.
- The build stages the derived routes as `build/data/routes.json`,
  which the site reads as `site.Data.collection.routes`.

## Capabilities

### New Capabilities

- `synthesis-routes`: the derivation of the routes and their data, and
  the route tree on compound pages.

### Modified Capabilities

- `general-procedures`: a route takes each entry on its own, not the
  pooled substrates of all entries.
- `build-script`: the build writes the route data.
- `site-build`: the overlay's data mount carries the route data.
- `site-theme`: compound pages end with the route tree.
- `compound-fields`: the route tree's compound links carry their notes.
- `localization`: the German strings of the route tree.

## Impact

- Code: `tools/pipeline.py` (the derivation), `tools/orgsyndb` (staging
  the data), `site/layouts/compounds/page.html` and a recursive partial
  for the tree, `site/i18n/en.toml` and `de.toml`,
  `site/assets/css/base.css`.
- Tests: a fixture procedure `tests/fixtures/theme/OSDB-0910-aspirin-hydrolysis.md`
  that closes a cycle with OSDB-0002.
- Docs: the README's feature list, and any document that describes
  compound pages.
- Compound pages carry no `data-pagefind-body`, so the search index is
  unchanged.
