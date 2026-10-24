## Why

OrgSynDB uses a reading-width shell for every page. Desktop browsers have
room for the procedure tables and reference information, but the narrow
shell leaves that space empty and stacks the browse tools below the list.
The owner requested a desktop layout and several separate visual options,
then chose two of the minimalist ones for the lists and procedure pages.
A browser could also hide a rebuilt site behind cached pages.

## What Changes

- Widen the screen shell to 96rem, with desktop padding and navigation.
- Place recent procedures beside the reaction-type and tag links.
- Lists: implement a full-width table with an entry count, a
  search field, reaction-type and status filters, and a sort bar.
- Procedures: implement a Marginalia layout, with the body on the left
  and the structure and metadata as an unboxed margin on the right.
- Use the system sans-serif stack on screen; print keeps its text face.
- Mark the current page and section in the site navigation.
- Give procedure tables the width of their containing column.
- Keep narrow-window stacking and the existing A4 print flow.
- Send `Cache-Control: no-cache` from `serve` and the Caddyfile example,
  so a browser shows a new build instead of cached pages.

## Impact

The change affects the site-theme and build-script capabilities, screen
CSS, the list, procedure and header templates, a new list-filter script,
five interface strings per language, `serve`, the Caddyfile example, the
tests and the README. Search, collection content and print CSS keep
their contracts.
