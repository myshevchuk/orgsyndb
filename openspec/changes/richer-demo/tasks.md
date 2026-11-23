## 1. Tests

- [ ] 1.1 Sample procedures: no total counts; Org and Markdown
  samples, at least five reaction types; the named chains still Org
  to Markdown; no rule against other chains
- [ ] 1.2 Quantities: solvent and auxiliary rows of `–` exempt but
  their CAS check digit; the checker scenario with a solvent row
- [ ] 1.3 Reagents in the registry: every row's CAS is exactly one
  registry substance; German tables list the same CAS numbers in order
- [ ] 1.4 Demo collection: registry contents (named, Reagents rows,
  `new-compound-7`, commercial chemicals of their groups, some unused);
  groups of intermediates; article numbers `CH-<nnnn>`, the six named
  among them
- [ ] 1.5 German variants for every sample; test collection with one
  file per demo sample file, Markdown copies byte-identical
- [ ] 1.6 Sequences: the two named, one of three and one of four
  steps at least, every sequence chained, with German variants,
  targets with article numbers
- [ ] 1.7 Lab demo: an item of every registry article number; an
  open vessel on `D` of every substance a sample starts from or lists,
  bought where no sample makes it; an open bought vessel of every
  unused commercial chemical; made vessels of substances without an
  article; the running task of a sequence of three or more steps
- [ ] 1.8 Existing tests that count the demo's or the test collection's
  contents brought to the new counts

## 2. Data

- [ ] 2.1 Reagents rows for every chemical of the nine existing
  samples, in both languages and formats, and their test-collection
  copies and converted twins
- [ ] 2.2 Twenty-one new Markdown samples with German variants,
  sequences of three and four steps with German variants
- [ ] 2.3 Registry substances with names, formulas, weights, SMILES,
  molfiles, CAS numbers, groups and classes; the digest; the manifest
- [ ] 2.4 Demo data set: articles and items, bought and made batches
  and vessels, the task of a sequence of three or more steps
- [ ] 2.5 Test collection mirrored

## 3. Check

- [ ] 3.1 Chemistry check of compounds, structures, CAS numbers,
  relations and Reagents rows by a second model; findings judged and
  fixed; CAS numbers spot-checked against PubChem
- [ ] 3.2 Area tests, then both suites on CI
- [ ] 3.3 Demo reseeded on the test server; the owner looks at it
