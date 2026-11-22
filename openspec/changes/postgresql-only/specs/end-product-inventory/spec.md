## MODIFIED Requirements

### Requirement: Item movements
Every change of an item's quantity SHALL be a movement holding `kind`, `count`, `quantity_after`, `date`, `booked_at`, `user`, `note`, and `delivery_note`, `vessel_movement` and `reverses` where they apply:

- `opening` (`Anfangsbestand`, `Opening count`): the first movement of every item, its `count` the quantity entered on creation;
- `delivery` (`Abgabe`, `Delivery`): `count` containers out, more than zero and at most the quantity, booked by a line of the current delivery note `delivery_note` and dated as the note;
- `filling` (`Abfüllung`, `Filling`): `count` containers in, more than zero, taken from a vessel (Filling from bulk), `vessel_movement` the vessel's filling;
- `correction` (`Korrektur`, `Correction`): `count` the quantity counted, at least zero; a note is required;
- `reversal` (`Storno`, `Reversal`): undoes one delivery or filling, named by `reverses`, adding back a delivery's count or taking back a filling's, and returning a filling's amount to its vessel with a vessel reversal; a movement is reversed at most once, a reversal of a filling whose containers are no longer there is refused, and a note is required.

`date` is the day the movement took place, today by default and never after today; `booked_at` is the time it was booked. The quantity changes by one atomic conditional update in the transaction that stores the movement, so two bookings prepared from the same quantity can never take more than it holds, and `quantity_after` is the quantity after that update. A refused movement changes nothing. Movements are never edited or deleted, in the views or the admin, except that deleting an item in the admin deletes its opening movement with it.

#### Scenario: Delivery
- **WHEN** user `KL` books a delivery note `LS-2026-117` to `Produktion` with one line of 2 containers of an item with 5
- **THEN** the item has 3, and its newest movement is a delivery of 2 with `quantity_after` 3, by `KL`, naming that note

#### Scenario: Concurrent deliveries
- **WHEN** two deliveries of 4 are validated against an item with 5 and then stored one after the other
- **THEN** the first is stored, the second is refused, and the item has 1

#### Scenario: Correction needs a note
- **WHEN** a signed-in user posts a correction to 4 without a note
- **THEN** the form shows an error at the note and nothing changes

#### Scenario: Reversing a delivery
- **WHEN** a signed-in user reverses a delivery of 2 dated in the third quarter of 2026, with the note `falsch gebucht`
- **THEN** the item has 2 containers more, the delivery no longer counts in that quarter's consumption, and a second reversal of it is refused
