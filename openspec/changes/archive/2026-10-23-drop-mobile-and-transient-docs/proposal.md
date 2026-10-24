## Why

The site is used on desktop browsers. The theme's specs still carry a
manual phone-width review, and its stylesheet a phone-only rule set.
Basic stacking for narrower windows stays, since a desktop window can
be narrow too, but mobile is no longer a goal of its own; support for
it, if it is ever wanted, will be a change of its own.

The design concepts under `docs/designs/` were transient material for
choosing the desktop layout and have served their purpose. The specs
still point at them. `docs/DECISIONS.org` duplicates what OpenSpec
records: the rationale lives in the archived change designs, and the
tool versions belong in the specs. One of them, the Emacs and Org
versions the export targets, is recorded nowhere else.

## What Changes

- Remove the screen stylesheet's phone-width (35rem) rule set; keep the
  70rem and 55rem rules that stack the columns in narrower windows.
- Drop the manual phone-width scenario, and state narrow-window
  stacking in one sentence of the measure requirement.
- Drop the references to `docs/designs/` from the site-theme spec, and
  delete `docs/designs/`.
- Delete `docs/DECISIONS.org`; record the Emacs 30.2 and Org 9.7.11
  target in the org-export spec.
- Remove the README's "Moving from `tools/build.fish`" section, its
  link to the decisions file and the word "responsive".

## Impact

Affects the site-theme and org-export capabilities, `screen.css` and
the README. Print, search, the build program and collections keep
their contracts.
