## Why

A sequence names the entry of a general procedure it runs by its
number, `entry = 2`, the line's position in the scope table. Inserting,
removing or reordering a line silently points every sequence at other
chemistry. The owner settled in draft 07 that a step names its entry
by its chemistry: by its product, or, where a product alone matches
more than one entry, by its substrates and products in full (option
C). The lab application already matches entries by that signature on
import; the collection's text now says the same.

## What Changes

- **BREAKING** A step of a general procedure names its entry by
  `product`, a product of exactly one entry, or by `substrates` and
  `products`, an entry's compounds in full; `entry` is refused.
- The validator reports a missing, unknown or ambiguous product, a
  signature no entry has, and both forms at once, naming what to write.
- The build stages each sequence with the resolved entry number, so
  the sequence pages keep reading it; `orgsyndb manifest` gives the
  resolved number, so the import is unchanged.
- Emacs completes a step's product from the procedure's entries; the
  index lists the new step keys.
- The demo and test sequences name their entries by product.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `synthesis-sequences`: the step keys, their messages, the staged
  entry number, continuity through the resolver, variants as written.
- `general-procedures`: no two entries of one procedure with the same
  substrates and products.
- `build-script`: the manifest's steps.
- `collection-index`: the step keys.
- `emacs-mode`: completion of a step's product.

## Impact

- Changed: `tools/validate.py`, `tools/pipeline.py` (resolution,
  staging, manifest), `emacs/`, `examples/demo/md/sequences/`,
  `tests/fixtures/` sequences, `templates/sequence.md` when it shows an
  entry, the tests of each.
- Docs: `README.md` (sequences), `docs/SCHEMA.md`, `docs/AUTHORING.md`
  and their German versions.
