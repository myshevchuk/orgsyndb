## Why

Today a task's priority is a person's estimate, read off the
end-product inventory's colours and weighed by a feeling for how
important the product is. The owner wants that judgement replaced by
a calculation. The calculation should say how long the stock will last
given how much and how unevenly it is consumed, and how long a
synthesis takes. From those it should give the date by which the next
synthesis must start, with generous margins, because a large external
order can empty the production department's supplies early. The
inventory now records dated delivery notes, past syntheses record
their durations, and bulk lots record what can still be filled, so the
application has what the calculation needs.

## What Changes

- A forecast for every item with consumption:
  - demand as it arrives: orders at a measured rate, with sizes like
    past orders, taken from the delivery notes, the probability of
    lasting computed exactly; where too few notes exist, a rough
    approximation from the quarterly totals, marked as such;
  - the runway: how many days a stock lasts at a chosen certainty
    (95 % by default);
  - per article, the runway of all its sizes together, the bulk shared
    out between them so that it counts once;
  - the synthesis time, from the longest of the last three syntheses
    of the article, the default counting until three exist;
  - the latest start: the article's runway, minus a buffer, minus the
    synthesis time;
  - the amount a new synthesis must yield to last a year;
  - the delivery rhythm: last delivery, deliveries per year, the
    usual interval and the next expected delivery.
- A computed priority from the days left before the latest start:
  high under two weeks, medium under eight, low beyond. It replaces
  the entered priority for every planned or running task whose product
  the inventory knows; a running task's own slack counts only its
  remaining synthesis time and shows whether it will be late.
- Planning parameters (certainty, buffer, default synthesis time,
  history, minimum orders, priority bands, target coverage), kept by
  staff in the admin, with their history.
- `/lab/planning/` (`Planung`, `Planning`): the articles most urgent
  first, and any with filling due, with runway, synthesis time, latest
  start, priority, active tasks marked when they will finish late, and
  the actions due: fill a size from bulk, check bulk, plan a
  synthesis.
- The item page shows its forecast with every figure's basis; the task
  page shows the forecast of its product.
- An ended task with a batch offers to record it as a bulk lot; tasks
  and lots of the same batch link to each other.

## Capabilities

### New Capabilities

- `production-planning`: matching tasks and articles, the demand
  models, the forecast, the computed priority, the parameters, the planning list, and the links
  between tasks and bulk lots.

### Modified Capabilities

- `web-app`: the page shell lists `Planung` between `Bestand` and
  `Aufgaben`.
- `task-tracker`: the task list shows, orders and filters by the
  computed or entered priority; the task page shows its product's
  forecast, the bulk lots of its batch and the link to record it as
  bulk; the task form's help text and its `product` from the query.
- `end-product-inventory`: the item page shows the forecast, the lot
  page the tasks of its batch, and the new-lot form takes `batch` and
  `made_on` from the query.

## Impact

- New: `webapp/planning/` with its models, migrations and templates;
  its tests in `webapp/tests/`. The forecast uses only the standard
  library (`math`, `statistics.NormalDist`).
- Docs: `README.md`, and a help page explaining the forecast in plain
  words.
- Not included: printing delivery notes, notifications, forecasts for
  inventories other than the end products.
