## Context

The generator places boxes on a grid of bands and columns and routes
each reference by four rules: elbow, vertical, under and loop. A
reference none of them fits stops generation. References to
`accounts_user` are skipped, and two declared links are dashed.

## Goals / Non-Goals

**Goals:**

- Every link drawable wherever its tables sit, so that the grid is
  arranged for legibility rather than for the router.
- Each kind of link visible on demand, without the page carrying every
  line at once.

**Non-Goals:**

- Choosing the shortest or least crossing route among several.
- Remembering the switches between visits.

## Decisions

### Gaps and corridors as the channels

A column gap and the space between two bands never hold a box, so a
line kept to them crosses lines but never a box. The channel rule
leaves the referencing box towards the referenced one into the gap
beside it, travels that gap to a corridor, the corridor to the gap
beside the referenced box, and that gap to the row of the key. When
both gaps are the same, as for two tables of one column, the line
stays in the gap. It is the last rule, so the shorter ones keep the
lines they drew. The under rule now gives way to the later rules when
its line would cross a box stacked below the referencing one, instead
of stopping generation.

### Lanes, and room for them

Lines sharing a gap over overlapping heights, or a corridor over
overlapping gaps, take distinct lanes 12 and 10 units apart. Lanes
need room beside the line ends of the boxes, so a gap is 66 units wide
plus 12 for each lane beyond the first, and a corridor 70 units high
plus 10 for each lane beyond the first. Corridor lanes are counted
first, by gap indices, since they do not depend on positions; the
bands are then placed, the gap lanes counted from the heights, and the
columns placed.

### Kinds and switches

A line's kind is a class on its group: `kind-key`, `kind-user` or
`kind-value`. The switches are checkboxes the script reveals and
applies, so a page read without a script shows every line. A switched
off kind is hidden by a class on the `svg`; a line marked as shown by
the highlighting is exempt, which is how hovering reveals it.

### Labels that fit

A value link's description is long, so it goes into the line's
tooltip, and its short label is drawn above its longest horizontal
segment only where that segment holds it. Delete rules keep their
placement.
