## Context

The compound page (`site/layouts/compounds/page.html`) already finds the
procedures that make a compound, one level deep, in a Hugo template.
The build stages per-collection data for the site as JSON under
`build/data/` (`fields.json`, `reaction_types.json`), mounted as
`site.Data.collection`. `run_build` in `tools/orgsyndb` holds the
published procedures, one variant per ID, as `(path, front matter)`
pairs before Hugo runs.

## Goals / Non-Goals

**Goals:** a route tree per compound, derived at build time from the
published procedures, safe against cycles, bounded in depth and size,
and testable as a pure function.

**Non-Goals:** an overall yield per route; choosing a best route;
routes on procedure or sequence pages; a route search.

## Decisions

### Derive in Python, render in Hugo

`pipeline.routes_data(files, depth, budget)` builds every tree from the
front matter of the published procedures; the build writes it to
`build/data/routes.json`; a recursive partial draws it.

Rejected: recursion in Hugo templates. A cycle guard needs the path
carried through every call, Hugo has no early return, and the result
could be tested only through full site builds.

### A tree of alternatives, not a list of routes

The tree alternates compounds and steps: under a compound, every step
that makes it (any one will do); under a step, every compound it starts
from (all are needed). This is the AND-OR tree that the owner's
description gives.

Rejected: enumerating complete routes. Every choice multiplies the
count, a shared intermediate is repeated in every route that uses it,
and the reader has to diff long lists to see where routes part.

No overall yield is shown: a tree has no single yield until a route is
chosen. The written sequence, which is one chosen route, keeps its
overall yield.

### The cycle rule drops the step

A step that starts from a compound on the path from the page's compound
down to the compound being made is left out. Every compound on a path is
therefore new to it, so recursion terminates even without a depth
limit, and a compound whose only steps cycle back becomes a plain leaf:
in that context it has to be obtained some other way.

Rejected: keeping the step and marking the repeated compound as a
cycle. That presents, as a way to make the compound, a route that
needs the compound itself.

### A fixed depth and a step budget

The depth limit is 6 and the step budget 200, both fixed. The depth
keeps the nesting readable on a narrow screen; the cycle rule alone
would bound it only by the number of compounds. The budget bounds the
size: four steps per compound, each starting from two made compounds,
already give about 150,000 steps at depth 6. A tree over budget is
drawn to the largest depth whose tree fits, found by deepening one level
at a time, so the oversized tree is never built. Each compound the
smaller depth cuts off is marked `more steps on its page`, where its
own tree is drawn under its own budget. `routes_data` takes both as
parameters so that tests can use small values.

Rejected: a `[routes] depth` setting in `orgsyndb.toml`. It adds a public
option and a validator rule, and the budget already adapts the drawn
depth to a dense collection; no collection is known to need deeper
nesting than six steps on one page.

Rejected: a depth limit alone. It does not bound the size of a tree in
a dense collection.

Rejected: expanding each compound only once per page and referring back
to it elsewhere. It bounds the size, but the cycle rule depends on the
path, so a compound expanded once under one path would be shown wrongly
under another.

### When the section appears

Only when the tree goes past one step: some step of the compound starts
from a compound that is itself made (expanded with a step, or cut off).
Otherwise the tree repeats `Made by` exactly. The data holds only those
compounds, so the template needs no test of its own.

### Placement and markup

The section is the last of the compound page, after the written
sequences, since it can be long. A step item reuses the `Made by` item's
text and order; a compound item is a compound link, so it carries the
note of compound-fields "Values beside compound links" like every other.
Published procedures of every status take part, with their badges, as
in `Made by`.

## Risks / Trade-offs

- A shared intermediate is repeated under every step that uses it.
  Bounded by the step budget; accepted for the clarity of a plain tree.
- A dense collection may see trees drawn shallower than six steps. The
  cut-off marks say so, and each marked compound's page continues.
- `routes.json` holds every tree in full, so its size grows with the
  same repetition. It is build output, never committed.
