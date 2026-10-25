## Why

The demo collection holds six Org and two Markdown procedures, so it
suggests Org is the primary format and Markdown an afterthought. Both
are first-class sources and render the same; the demo should show that
with an even split.

## What Changes

- OSDB-0005 and OSDB-0006, with their German variants, become Markdown
  procedures in `md/procedures/`, with the same content and file names.
- The demo then has four Org and four Markdown samples, and each
  precursor chain leads from an Org procedure to a Markdown one.

## Impact

Affects the sample-procedures capability, `examples/demo/` and
`tests/test_samples.py`.
