## Context

The menu `main` of `site/hugo.toml` alone decides the navigation's
entries and grouping (site-theme "Navigation"); the site and the lab
render it alike. The vocabularies live in the `vocabulary` app, their
pages in `registry/views.py` under `/lab/registry/<vocabulary>/`.
Projects and reaction types are named by imported procedures
(`collection.Procedure.project` and `.reaction_type`, both protected).

## Goals / Non-Goals

**Goals:** substances and the technical tables in groups of their own;
every vocabulary, the notebooks and the imports reachable from the
menu; a use count that is true for every vocabulary.

**Non-Goals:** merging the site's compound pages into the lab's
substance pages, which follows as its own change; changing URLs or
tables; the site's label of the group field (compound-fields), which
goes with the compound pages.

## Decisions

**Sections by path.** `Substanzen` claims `/lab/registry/substances/`
besides its own URL, and each vocabulary claims its own subtree, so
that a vocabulary's forms mark the vocabulary, not the substances: the
current link is the first whose paths match, and `Substanzen` comes
first.

**Uses counted where the protection lies.** A term is in use where a
row names it: a substance or its class row for the chemical classes
and inventory groups, a procedure for the projects and reaction types.
Withdrawn procedures count, since they too keep a term from being
deleted.

**Labels only.** `Group` becomes `Inventory group` in the model, form
and templates; the field stays `group` and the vocabulary's page
`groups`. Django records the new verbose names in migrations that
change no table.

## Risks / Trade-offs

- `Reaktionstypen` names both the lab's vocabulary in `Stammdaten` and
  the site's taxonomy tab under `Vorschriften` → the two lists differ
  in what they show (terms against procedures by type), and the menu
  places them in different groups.
