## Context

`validate.check_step` requires `entry` for a general procedure and
refuses it for a specific one; continuity checks read the step's
entry by number. The site's `sequence-steps.html` indexes
`Params.scope` by `entry`; `pipeline.manifest_data` copies `entry`;
Emacs completes entry numbers. The import matches scope entries by
the signature `substrates >> products` of sorted keys.

## Goals / Non-Goals

**Goals:**

- A step's text names chemistry, so a reordered scope table keeps
  every sequence on the same entries.
- Everything downstream of the validator keeps working with entry
  numbers it derives.

**Non-Goals:**

- Issued IDs and authors as accounts: a later change.

## Decisions

### One resolver

`pipeline.step_entry(step, procedure)` returns the number of the entry
a step names, from 1 in file order, or None: by `product` when exactly
one entry has it among its products, else by `substrates` and
`products` compared as sets with an entry's substrates and product
compounds. The validator, the staging of sequences, the manifest and
continuity use it, so they cannot disagree. A product in two entries
is ambiguous, not resolved to the first: the author must write the
full signature, as the owner chose. A full signature is unique because
the validator now refuses two entries of one procedure with the same
substrates and products, which the import refused already; a step's
own lists may not repeat a compound. Variants of a sequence compare
their steps as written, lists in order, as they do today.

### The staged copy carries the number

The build already transforms what it stages; it adds `entry` to each
step of a general procedure in the staged sequence, and the layouts
read it as before. The source file never holds a number.

Alternatives: resolve in the Hugo layouts. Comparing two key sets per
entry in Go templates is long and duplicates the resolver.

## Risks / Trade-offs

- [Existing sequences stop validating] → The demo and the test
  fixtures are converted in this change; the product has no other
  collections.
