## Context

The lab keeps every accepted import's procedures, scope entries with
their substances by role and yield, and sequences with their targets
and steps (collection-import "Imported rows"); a row the collection no
longer has is withdrawn, not deleted. The site's compound page draws
the same relations from the procedure files at build time, and its
route trees from `pipeline.routes_data`. The lab loads the site's
`site.js`, which wires the SMILES copy button.

## Goals / Non-Goals

**Goals:** the lab's substance page shows everything the site's
compound page shows but the structure image; the substance list
filters as the compound catalogue does by group and class; no build
data the lab must read beyond the manifest.

**Non-Goals:** structure images, which move into the lab's database in
their own change; retiring the site's compound pages and catalogue,
and the pipeline's routes, which follow; the catalogue's other facets
and columns.

## Decisions

**The latest accepted import, not the served release.** A procedure or
sequence the latest accepted import has is one whose row is not
withdrawn, and an entry of it one whose row is not withdrawn either:
withdrawing a procedure leaves its entries as they were, so both must
be checked. The builder publishes that import's release after the lab
accepts it, so after a lost answer, or for the demo data set's own
import, a link may lead to a page the site does not serve yet, as the
link `In der Sammlung` may.

**The route tree is drawn for one substance at a time.** The lab
builds the steps to each compound from the rows once per request and
draws only the page's tree, by the rules of "Derived routes": the same
depth limit, step budget, cycle rule and order. The pipeline's
function stays until the site's compound pages retire; until then the
two draw from the same procedures and agree.

**Status comes with the manifest.** A procedure's status is in its
front matter, which only the build reads; the manifest's procedure
tables gain `status`, the published variant's, and the procedure row
keeps it. Rows written before the field exists keep an empty status,
shown without a badge, until the next accepted import gives them one.

**Filters by GET parameters.** `group` and `class` take a term's key
and match a substance filed under that term or a term below it, as the
compound tabs and the class facet do; with `q` they narrow together.
The form submits on its button, without a script.

**Links leave the lab for procedures and sequences.** They lead to the
site's pages, `/procedures/<id>/` and `/sequences/<id>/` with the ID in
lower case, which the lab already links.

## Risks / Trade-offs

- Two route implementations until the compound pages retire → the
  lab's tests repeat the scenarios of "Derived routes", and the next
  change removes the pipeline's.
- A page with a large route tree draws it on every request → the
  step budget bounds it, as on the site.
- Yields are stored as floats → the page writes them as numbers, `80`
  rather than `80.0`, with the language's decimal mark.
