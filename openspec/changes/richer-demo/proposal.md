## Why

The demo shows nine procedures, seven articles, a handful of
intermediates and one bought bottle. That is too little to judge the
stock views the owner approved on 2026-11-23, which split `Bestand`
into end products, self-made intermediates and commercial chemicals:
the commercial view would hold one row. Nor can the demo show
multi-step routes, since no sequence has more than two steps.

The owner asked on 2026-11-23 for a demo with:

- about thirty procedures, among them several three- and four-step
  routes;
- more end products, self-made intermediates and commercial chemicals;
- every chemical a procedure uses, solvents and catalysts included,
  traceable to a row of the inventory, and a dozen or two commercial
  chemicals that no procedure uses;
- compounds, structures and their relations chemically sound enough
  that a chemist is not distracted by wrong facts. The procedures'
  quantities and conditions need not be experimentally right.

## What Changes

- The requirements stop counting the demo. They name the samples,
  chains, sequences and articles that other requirements rely on, and
  state rules that every further sample, compound or article meets, so
  that the demo can grow without a change to them.
- The demo collection grows to about thirty sample procedures,
  counting the general procedure. The nine existing ones stay. The new
  ones are Markdown procedures. Every sample has a German variant.
- Every chemical a sample uses, except water, ice, inert gas and the
  materials of analysis (TLC plates, indicator paper, NMR solvents), is
  a row of its Reagents table: substrates, reagents, catalysts, solvents
  and workup chemicals alike. A row of a solvent or an auxiliary writes
  `–` for `mmol` and `Equiv` and is exempt from the quantity rules, as
  a catalyst row is. The nine existing samples gain these rows too.
- Every Reagents row names, by its CAS number, a substance of the demo
  registry. The registry adds these substances and twelve to
  twenty-four commercial chemicals that no sample uses, each with its
  structure where it has one.
- The rule that no compound beyond the listed chains links two samples
  goes, and so does the rule that no procedure has both a precursor and
  a use. The demo ships, besides `SEQ-0001` and `SEQ-0002`, sequences
  of three and of four steps.
- The demo inventory holds more articles. Every substance a
  sample starts from or lists in its Reagents table has an open vessel
  on the seeding day: a bought one for a purchased chemical, a made one
  for an intermediate. Every commercial chemical that no sample uses
  has an open bought vessel too. Liquids are weighed, since vessels
  have no volume units.
- A running task follows a sequence of three or more steps, with its
  first two steps done and their batches recorded.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sample-procedures`: no counts; open chains; registry contents;
  Reagents rows for every chemical; German variants of every sample;
  the test collection; sequences.
- `lab-demo`: the inventory's articles and vessels; a task of a
  sequence of three or more steps.

## Impact

- `examples/demo/md/procedures/` and `md/sequences/`, new files and
  their German variants; Reagents rows added to the nine existing
  samples in both languages and formats.
- `webapp/demo/registry.json`: new substances with molfiles, the
  digest; `webapp/demo/manifest.json` regenerated;
  `webapp/demo/data.py` and `seed.py`.
- `tests/fixtures/collection/`: the copies and converted samples the
  requirement Test collection derives from the demo.
- Tests that count the demo's procedures, substances, articles or
  sequences.
