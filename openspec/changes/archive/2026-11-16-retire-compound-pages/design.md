## Context

The site builds `/compounds/` (the compound catalogue, searched by its
own text search and filtered by chemical class and group), a tab page
per top-level inventory group under `/compounds/group/`, and a page per
substance with its facts, the procedures that make and use it, its
sequences and its route tree, drawn from `build/data/routes.json`,
which `pipeline.routes_data` derives from the published procedures.
Every `a.compound` on the site links that page. The lab's substance
page now shows all of it, the structure image included, and draws the
route tree itself (`collection/routes.py`); the site needs the lab.

## Goals / Non-Goals

**Goals:** one page per substance, the lab's; no compound pages,
catalogue, tabs or route data in the build; every remaining reference
to them in the site, the build, the validator, the lab and the specs
gone or re-pointed.

**Non-Goals:** the substance data the build stages for procedure,
scope and sequence pages (`build/data/compounds/`), which stays;
lab-less builds, whose links into the lab do not resolve, which the
retirement of the GitHub Pages demo settles (STATE.md); moving the
procedure and sequence pages into the lab.

## Decisions

**Compound links lead to the lab whatever `ORGSYNDB_LAB` says.** The
site needs the lab; a link that changes with the build setting would
make a lab-less build link pages that no longer exist. The `a.compound`
keeps its class, text and the values beside it. site-build "Deployment
under a path prefix" names these links among the references to the
lab, which resolve at the root alone. Rejected: plain-text names
without `params.lab`, a branch that goes again once the GitHub Pages
demo retires, and that would leave most site tests, which build without
the lab, with no `a.compound` to check.

**The home page counts substances and links the lab's list.** The
browse list keeps an entry for the substances, `Substanzen`
(`Substances`) to `/lab/registry/`, so the home page still leads to
every compound.

**The route rules move into "Routes in the lab".** The lab's tree
already follows them; the spec states them once, where they apply, and
`pipeline.routes_data` with its staged data and its tests goes.

**Registry fields keep `beside` alone.** `column`, `search`, `facet`
and `tabs` only told the compound directory and catalogue what to show;
with them gone the options mean nothing, so the field data and the
index stop carrying them. Before 1.0 nothing keeps a dead option.

**The catalogue script has one search.** `match` and the
`data-search="text"` mode served only the compound catalogue; every
catalogue left searches with Pagefind. The facet partials the procedure
catalogue shares stay.

**The key `group` is a key like any other.** It was refused only
because the tab pages took `/compounds/group/`.

**The lab's link `In der Sammlung` goes, with the query behind it.**
Its target retires; the page it sits on is now the compound's page.

## Risks / Trade-offs

- Bookmarks of `/compounds/...` break; the site has no users yet.
- A lab-less build keeps links into `/lab/` that do not resolve until
  the GitHub Pages demo retires.
