## Why

The table diagram leaves out the links a reader most needs to follow:
the eight foreign keys to `accounts_user` are marked but not drawn, and
tasks reach the inventory only through values, the product through the
collection index and the batch, which the diagram does not show at
all. The routing rules cannot reach a table that lies in another band
more than one column away, so such links could not be drawn even when
declared. Drawing everything at once would clutter the diagram.

## What Changes

- A channel rule routes any reference the shorter rules cannot: along
  the gaps between columns and the corridors between bands, which hold
  no box. Gaps and corridors widen to hold the lines that share them.
- Every foreign key is drawn, those to `accounts_user` in the accounts
  colour.
- Two declared links join tasks to the inventory: the product to the
  item's article number, the batch to the lot's batch.
- Lines have three kinds, foreign keys, links to `accounts_user` and
  links matched by value, each with a switch above the diagram. Links
  to `accounts_user` start switched off.
- Hovering, focusing or tapping a table shows its lines whatever their
  switches; hovering a column shows the lines through it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `database-diagram`: links of every foreign key and the two task
  links, line kinds and their switches, the channel rule and widened
  gaps and corridors.

## Impact

- Changed: `orgsyndb_web/schema_diagram.py`, its template, the tests and
  the generated `webapp/docs/database-schema.html`.
