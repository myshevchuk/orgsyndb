## MODIFIED Requirements

### Requirement: Demo inventory
The data set SHALL open the inventory on the opening day `O`, `D` less 400 days, and hold in the inventory `end-products`:

- items of seven articles: `CH-0001`, `CH-0002`, `CH-0010`, `CH-0012`, `CH-0013` and `CH-0016`, the final products of `examples/demo` that set `item_number`, each item named as its compound is there, with `name_de` when the language is German; and `NV-0007`, named `Neuverbindung 7` (`New compound 7`), which names no compound of `examples/demo`. At least one article has three sizes, and the sizes use the units `mg`, `g` and `umol`;
- one item without an article number, named `1-Phenylethanol` as the compound `1-phenylethanol` of `examples/demo`, opened after `O`, filled without a lot 89 days before `D`, and never delivered;
- sizes that planning leaves out: `CH-0012` in 1 g, `discontinued`, and `CH-0010` in 25 g, `not_needed`, each set aside after its opening count and never delivered; and `CH-0001` in 250 mg, whose consumption is entered for the four quarters from the eighth to the fifth before the quarter of `O` and is none since;
- `CH-0013` in 1 g, opened 60 days before `D`, with a delivery of one container every 15 days from then on;
- each item's opening count, dated `O`, or later for a size added afterwards;
- for the items that have them, entered consumption for each of the seven quarters from the eighth before the quarter of `O` to the second before it, and for `CH-0001` in 250 mg for the four from the eighth to the fifth, entered in the 30 days from `O`;
- historical delivery notes dated from the first day of the quarter before that of `O` to the day before `O`, entered in the 30 days from `O`, one of them later reversed with a note;
- current delivery notes from `O` on, each with a recipient, some with several lines;
- every delivery note numbered `LS-<year>-<nnn>`, where `<year>` is the year of its date and `<nnn>` counts the notes of that year in the order of their dates from `001`;
- one delivery reversed with a note, and one correction with a note;
- bulk lots, each with a batch, a location and the date it was made, and fillings from them, each naming its lot's movement; one lot used up, one lot corrected with a note, and one lot of `NV-0007` in `umol`.

#### Scenario: Item list
- **WHEN** the data set is written as of `D` with the demo collection's index and a test client requests `/lab/inventory/end-products/`
- **THEN** the list shows the seven article numbers, the name of each item of the six final products linking to its compound's page, the name `Neuverbindung 7` without a link to a compound, and last the item `1-Phenylethanol` without an article number, its name linking to its page

#### Scenario: Levels on any seeding day
- **WHEN** the data set is written, each time into an empty database, as of 2026-01-01, 2026-02-14, 2026-03-31, 2026-11-07 and 2028-02-29, with the demo collection's index, and a test client requests `/lab/inventory/end-products/` on that day
- **THEN** on each day the list has stock cells with each of the classes `level-out`, `level-critical`, `level-low`, `level-watch`, `level-ok`, `level-undelivered` and `level-dormant`

#### Scenario: Notes
- **WHEN** the data set is written as of `D` and a test client requests the delivery list
- **THEN** it lists notes numbered `LS-<year>-<nnn>`, historical notes among them, one historical note shown as reversed, and one current note shown as reversed or partly reversed

#### Scenario: New positions
- **WHEN** the data set is written as of 2026-11-07 and a test client requests `/lab/inventory/end-products/`
- **THEN** the items `1-Phenylethanol` and `CH-0013` of 1 g are marked `neu` and no other item is, and the means of `CH-0013` of 1 g are projected
