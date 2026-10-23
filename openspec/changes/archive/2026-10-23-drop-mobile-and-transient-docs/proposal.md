## Why

The site is used on desktop browsers only, yet the theme still carries
phone-width rules, a viewport meta and a manual phone-width review. The
owner asked to drop mobile compatibility entirely; mobile support, if it
is ever wanted, will be a change of its own.

The design concepts under `docs/designs/` were transient material for
choosing the desktop layout and have served their purpose. The specs
still point at them. `docs/DECISIONS.org` duplicates what OpenSpec
records: the rationale lives in the archived change designs, and the
tool versions belong in the specs. One of them, the Emacs and Org
versions the export targets, is recorded nowhere else.

## What Changes

- Remove the screen stylesheet's width media queries and the viewport
  meta. The desktop grids already shrink their flexible columns, so a
  smaller desktop window keeps working without them.
- Replace the manual phone-width scenario with an automated check that
  no stylesheet has a width media query.
- Drop the references to `docs/designs/` from the site-theme spec, and
  delete `docs/designs/`.
- Delete `docs/DECISIONS.org`; record the Emacs 30.2 and Org 9.7.11
  target in the org-export spec.
- Remove the README's "Moving from `tools/build.fish`" section, its
  link to the decisions file and its mentions of responsive layout.

## Impact

Affects the site-theme and org-export capabilities, `screen.css`,
`baseof.html`, the theme tests and the README. Print, search, the build
program and collections keep their contracts.
