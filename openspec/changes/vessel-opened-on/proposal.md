## Why

The Bestand views to come list commercial chemicals by substance and
should say which bottles are already open and since when, and filter
for sealed ones. The application records no such fact; purity, expiry
and supplier documents stay out for now, and this one date is the
field the owner chose to add.

## What Changes

- A vessel of a bought batch gets `opened_on` (`Angebrochen am`): the
  day it was first opened, or none while it is sealed. A vessel of a
  made batch has none.
- The first filling, withdrawal or transfer out of a sealed vessel
  sets the date to that movement's date. A vessel made by a transfer
  is opened on the transfer's date. A correction or a reversal leaves
  the date alone.
- The vessel's edit form takes the date for a vessel of a bought
  batch, and clearing it marks the vessel sealed.
- The vessel page and the vessel list show the date or `versiegelt`.
- The demo has opened and sealed bottles.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: Vessels, Inventory forms, Vessel list,
  Vessel page.
- `lab-demo`: Demo inventory.

## Impact

- `webapp/inventory/` model, generated migration, bookings, forms,
  templates, German translations; `webapp/demo/`; tests.
- No data is converted: existing vessels of bought batches read as
  sealed until edited, and the demo is reseeded.
