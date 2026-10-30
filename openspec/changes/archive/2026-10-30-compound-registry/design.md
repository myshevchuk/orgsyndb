## Context

Products live inside procedures, and procedures point at each other by
ID. The next change adds general procedures, whose scope table lists
many substrate–product pairs, and the one after it synthesis sequences,
which chain procedures through the compounds they share. Both need a
compound that exists apart from any one procedure. The application uses
only the Python standard library and Hugo, so it cannot canonicalise
SMILES or compute InChIKeys.

## Decisions

- **The key is the identity.** A compound is a file
  `compounds/<key>.toml`, the key a slug like a reaction-type slug. Two
  procedures make the same compound exactly when they name the same
  key. Nothing compares structures.
- **One file per compound, in the collection.** The registry is the
  collection's content, not the application's, so it sits beside
  `org/` and `md/`. A file per compound keeps parallel additions free
  of merge conflicts and maps one-to-one onto the compound pages.
- **The registry holds what describes the compound; the procedure holds
  what describes the run.** Name, German name, formula, weight, SMILES,
  CAS and structure image move to the registry; the yield stays with
  the procedure, per product. A procedure's language variants then share
  `products` and `substrates` and no longer copy compound data; the
  German name comes from `name_de`, and from `name` where it is absent.
- **The final procedure shape now.** `products` is already a list of
  `{ compound, yield_percent }` tables, so co-products need nothing
  further, and the next change adds general procedures without
  rewriting every procedure and fixture a second time.
- **Links follow compounds.** `precursors` goes: a procedure's
  precursors are the procedures that make one of its substrates, so a
  second route to a starting material shows up without editing the
  procedure that uses it.
- **Compound pages come from the data.** The collection's `compounds/`
  is mounted as Hugo data, and a content adapter in
  `site/content/compounds/` makes one page per entry. The pages are not
  part of the search index: the catalogue finds procedures by their
  products' names, formulas, CAS numbers and SMILES, and a compound
  page is one click from any of them.
- **A product is always linked.** The panel's `Product` pair now links
  the compound page, which the title cannot, so it is shown even when
  the product is named like the procedure. Formula, weight, CAS and
  SMILES stay in the panel for a procedure with one product; with
  several, they are on the compound pages.
- **Org sources set `products` on the last custom front-matter line**,
  for the reason `product` had to be last: tomelr writes keys in order,
  and every key after a table header would belong to that table.

## Alternatives rejected

- **Compound data inline, with a consistency check.** Each procedure
  would keep its compound's data under a key, and the validator would
  require procedures sharing a key to agree. Authors would edit one
  file, but the data would still be copied into every procedure and
  variant, and every disagreement would be an error to resolve by hand.
- **Identity by canonical SMILES or InChIKey.** Needs a cheminformatics
  toolkit, which the standard-library rule excludes.
- **One `compounds.toml` file.** Simple, but two authors adding
  compounds at once conflict, and each compound page would have no file
  of its own.
- **`product` as a single key now, `products` in the next change.**
  Would rewrite every fixture, sample and template twice.
- **Compound pages in the search index.** The catalogue would mix
  compounds with procedures in one result list and one count.
