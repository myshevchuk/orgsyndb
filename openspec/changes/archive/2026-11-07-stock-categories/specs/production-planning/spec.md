## MODIFIED Requirements

### Requirement: Demand models
An item's demand SHALL be described by one of two models, estimated from its history window: the last `history_quarters` complete quarters, leaving out quarters before the item's first quarter with data. An item whose history window is empty or holds no consumption has no demand and no forecast, and so has an item whose level is `dormant` or `undelivered` (end-product-inventory "Stock levels"), whatever its history. Orders are the item's delivery-note lines that count as consumption, each with its date and count.

The order window is the latest quarters of the history window back to the latest quarter with an entered consumption value, not including it, or the whole history window when none has one. When it holds at least `min_orders` orders, the **order model** applies:

- the order rate `λ`, per day, is the larger of the number of orders in the order window divided by its calendar days and the number in its latest four quarters, or all of them when it has fewer, divided by their calendar days;
- the order size follows the empirical distribution of the counts of the orders in the order window;
- the demand over `H` days is compound Poisson: a Poisson number of orders with mean `λH`, each of a size drawn independently from that distribution;
- the need for `H` days at a certainty `q` is the smallest whole number `n` with `P(demand ≤ n) ≥ q`.

Otherwise the **quarterly model** applies, and every figure it gives is marked `grob` (`rough`):

- `m` is the larger of the mean consumption of the history window's quarters and that of its latest four quarters, or all of them when it has fewer;
- `v` is the larger of the sample variance of the history window's quarters, zero for one quarter, and `m`;
- per day, `μ = m / 91.3125` and `σ = √(v / 91.3125)`;
- the need for `H` days at a certainty `q` is `μH + z_q σ√H`, `z_q` being `statistics.NormalDist().inv_cdf(q)`.

The demand per year shows as `365.25 λ` times the mean order size, or as `4m`.

#### Scenario: Order model
- **WHEN** on 2026-11-04 an item has one delivery note of 10 containers in each of the eight quarters from the fourth of 2024 to the third of 2026 and no entered values
- **THEN** the order model applies with `λ` 8/730 per day and every order of size 10

#### Scenario: Entered values leave too few orders
- **WHEN** an item has entered values up to the second quarter of 2026 and two delivery notes in the third
- **THEN** the quarterly model applies and its figures are marked `grob`

#### Scenario: Rising demand in the quarterly model
- **WHEN** on 2026-11-04 an item's twelve last complete quarters hold entered values of 4 each for the first eight and 12 each for the last four
- **THEN** `m` is 12 and `v` is 15.52 to two places

#### Scenario: A dormant size plans nothing
- **WHEN** on 2026-11-04 with the default parameters an article has an item of 1 mg with 10 containers and twelve quarters of 9 in the quarterly model, and an item of 5 mg with 0 containers, the same history and the `status` `discontinued`
- **THEN** the article's runway and slack are those of the first item alone, 60 and 11 days, and the second item has no runway on hand

### Requirement: Item forecast
An item's forecast, shown on the item page, SHALL hold for an item with demand: its model, with `λ`, the number of orders and their median and largest size, or `m`, `v` and the number of quarters, marked `grob`; its runway on hand; and for its article the bulk, runway, synthesis time with its basis, slack, latest start and priority. It shows the amount a new synthesis must yield: for the converting items with demand, the sum of the whole containers each lacks for `L + buffer_days + target_days` days at `q_k`, its need minus its quantity where positive, rounded up, times its container size, minus the usable bulk, at least zero, in the bulk unit rounded up to a whole mg or µmol, and, when the bulk unit is µmol, also in mg, the unrounded amount converted and rounded up to a whole mg; and for each item that does not convert, the whole containers it lacks for that time, rounded up, as a count of its own size. It shows the delivery rhythm: the last delivery's date, the number of delivery notes in the past 365 days, and, given at least three notes in the past 730 days, the median number of days between their consecutive dates, rounded half up to a whole day, and the next delivery expected that many days after the last. Lines of reversed movements and reversed historical notes do not count. Each figure names the parameters it used. A dormant item shows `Ruhend, keine Prognose.` (`Dormant, no forecast.`), and every other item without demand `Kein Verbrauch, keine Prognose.` (`No consumption, no forecast.`).

#### Scenario: Forecast figures
- **WHEN** on 2026-11-04 with the default parameters the page of the 1 mg item with 10 containers, `m` 9, `v` 9, no bulk and an article number that names no compound of the index is requested
- **THEN** it shows the runway 60 days, the synthesis time 21 days by default, the slack 11 days, the latest start 2026-11-15, the priority high, and 42 mg for a new synthesis, all marked `grob`

#### Scenario: Delivery rhythm
- **WHEN** on 2026-11-04 an item has delivery notes dated 2026-06-01, 2026-07-01, 2026-08-31 and 2026-10-01
- **THEN** the page shows the last delivery 2026-10-01, four deliveries in the past year, a usual interval of 31 days and the next delivery expected on 2026-11-01

### Requirement: Runway
The runway of an item for a stock of `S` containers at a certainty `q` SHALL be the longest number of days `H` whose need at `q` is at most `S`, the same rule holding for `S` zero. In the quarterly model it is `((−z_q σ + √(z_q²σ² + 4μS)) / (2μ))²`, zero for `S` zero; in the order model, the `H` at which `P(demand over H ≤ S)` falls to `q`, to 0.01 days, which for `S` zero is the time within which no order arrives with probability `q`. An item's runway on hand is that of its quantity at `certainty`.

An article's runway uses, for each of its `k` items with demand, the certainty `q_k = 1 − (1 − certainty) / k`, so that by the union bound all of them are covered together with probability at least `certainty`, whatever the relation between their demands. Its bulk unit is µmol when the compound has a molar mass, else the kind of unit, mass or amount of substance, of the article's first item by unit and size among those whose level is neither `dormant` nor `undelivered`. An item converts when its container size converts into that unit; `s_max` is the largest container size, in that unit, among the converting items with demand, and zero when none has demand. Each open lot that converts counts with its amount in that unit minus `s_max`, where positive, so that whatever is counted can be filled in whole containers of any size. The usable bulk is the sum of those amounts. The article's runway is the longest `H` that meets two conditions:

- the sum, over the converting items with demand, of the whole containers each lacks for `H` days at `q_k`, its need minus its quantity where positive, rounded up, times its container size, does not exceed the usable bulk;
- `H` is at most the runway on hand at `q_k` of every item with demand that does not convert.

An article has a forecast when one of its items has demand. Runways show as whole days, rounded down; comparisons use the unrounded values.

#### Scenario: Even demand
- **WHEN** with the default parameters an item of 1 mg with 10 containers, no bulk and the quarterly model with `m` 9 and `v` 9 is its article's only item
- **THEN** the item's runway on hand and the article's runway are 60 days, and at a certainty of 0.5 they are 101 days

#### Scenario: Lumpy orders
- **WHEN** with the default parameters the item of the order-model scenario holds 9, 10 or 20 containers
- **THEN** its runway on hand is 4, 32 or 74 days, where the quarterly model of the same history would give 47 days for 9

#### Scenario: Bulk shared by two sizes
- **WHEN** with the default parameters an article has items of 10 mg and 20 mg, each without containers and with twelve quarters of 9 in the quarterly model, and one open lot of 360 mg
- **THEN** each item is planned at a certainty of 0.975, the usable bulk is 340 mg, and the article's runway is 62 days, where giving each size the whole lot at 0.95 would claim 277 and 124

#### Scenario: Lots too small to fill
- **WHEN** an article's only item, of 10 mg, has 10 containers and two open lots of 6 mg each
- **THEN** its usable bulk is zero and its runway is its runway on hand

#### Scenario: A dormant size does not choose the bulk unit
- **WHEN** with the default parameters an article whose compound has no molar mass has an item of 1 mg, dormant, and an item of 1 µmol with 10 containers and twelve quarters of 9 in the quarterly model, and an open lot of 100 µmol
- **THEN** its bulk unit is µmol, the lot converts, and its runway is that of the µmol item with the lot
