## Context

`task-tracker` keeps synthesis tasks with a product, an entered
priority, start and end dates and a batch. `end-product-inventory`
keeps items (one article in one container size), their containers,
dated delivery notes, consumption per quarter, levels, and bulk lots
of an article with the number of containers they would fill.

The owner's priorities today come from the inventory's colours and a
feeling for each product's importance. On 2026-11-04 the owner asked
to replace that feeling with a calculation. It should be approximate,
with generous margins: demand is dynamic, and a large external order
can empty the production department's supplies, which this department
must then restock early. The owner invited better suggestions than the
first draft, which compared stock with a fixed multiple of the mean.

## Goals / Non-Goals

**Goals:** a priority computed from data, the same for everyone, with
every figure behind it visible; the date by which a synthesis must
start; when filling from bulk is due; how much a synthesis must yield.

**Non-Goals:** forecasting individual customers' orders; seasonal
models; scheduling people or equipment; notifications; changing the
inventory's levels, which mirror the Excel file.

## Decisions

### Runway at a certainty, not a fixed margin

The runway of a stock is how long it lasts with a chosen probability,
the certainty, 95 % by default. The margin is then one number with a
meaning, and a product consumed in irregular lumps gets a shorter
runway than an even one with the same mean, which a fixed factor on
the mean cannot do.

### Orders where the delivery notes tell them

Deliveries leave in orders, a few a quarter, of very different sizes.
Demand of that kind is described by a compound Poisson process. Orders
arrive at a rate `λ`, and each takes a number of containers drawn from
the sizes of past orders. Both come straight from the delivery notes.
The probability that the demand over `H` days stays within a stock `S`
is then computed exactly, as a sum over the number of orders of the
Poisson weight times the probability that that many order sizes add up
to at most `S`. Sizes are whole containers, so the sum is finite. The
runway is the `H` at which that probability falls to the certainty,
found by bisection, since it falls steadily with `H`.

With orders of 10 arriving about once a quarter and 9 containers on
the shelf, the stock lasts only until the next order, and the runway
at 95 % is 4 days. A normal approximation of the same history gives
47. The critic of the previous draft showed that such an
approximation promises a certainty it does not deliver when demand
comes in lumps, which is the owner's case.

The rate is the larger of the whole window's and the latest four
quarters', so rising demand counts at once. The model needs orders,
and quarters entered as totals have none. So it uses the latest run of
quarters without entered totals, and only when that run holds at least
`min_orders` orders, six by default. Entering the old delivery notes
as historical notes therefore gives it a long history from the start.

### Quarterly totals as the rough fallback

Without enough orders, the forecast falls back on the quarterly
totals. It takes their mean `m`, the larger of all quarters' and the
latest four's, and their variance `v`, at least `m`, the variance of a
Poisson process, since lumpy counts vary at least that much. It then
approximates the demand over `H` days as normal with mean `μH` and
standard deviation `σ√H`, where `μ = m/91.3125` and
`σ² = v/91.3125`. The runway solves `μH + zσ√H = S`. These figures are
marked rough, because the certainty they state is approximate: they
assume the demand within a quarter spreads evenly, which lumps
violate.

Rejected: a fixed factor on the mean; the largest past order as the
size of the next; resampling past quarters at random, whose results
vary from run to run and resist testing.

### Planning per article, bulk shared out

A synthesis replenishes an article's bulk, from which every size is
filled, while filled containers serve only their own size. So the
synthesis is planned per article. Its runway is the longest time for
which the bulk can top up every size to its need, each size first
using its own containers:

    Σ over sizes of max(0, need_i(H) − on hand_i) × size_i ≤ bulk

This shares the bulk out so that all sizes last equally long and
counts it once. The previous draft gave each size the whole bulk:
with two sizes of 10 and 20 mg and 360 mg of bulk, it claimed 277 and
124 days.

Covering each of `k` sizes at the article's certainty does not cover
them together at that certainty; the critic's counterexample came to
93.7 % instead of 95 %. So each size is planned at `1 − 5 %/k`. By the
union bound, the chance that any size falls short is then at most
5 %, whatever the relation between their demands. That costs runway,
62 days instead of 68 in the example above. Rejected: the exact
distribution of the sizes' combined shortfall, which needs their
demands to be independent and a common grid of amounts that mixed
units do not have.

A lot fills whole containers, so not all of its amount is usable. Each
lot counts its amount minus the largest container size of the
article, and each size's shortfall is rounded up to whole containers.
Whatever is counted can then be filled in whole containers of any
size: as long as some lot holds at least the largest size, the next
container fits, and a lot is left only once it holds less, having
given at least its counted amount. Two lots of 6 mg count nothing for a 10 mg size.

The runway of zero stock follows the same rule as any other. In the
order model it is the time within which no order arrives at the
certainty, a few days. The level still says `aufgebraucht`, and
filling or synthesis is due.

Filling is decided per size: it is due when a size's own containers
would not last the buffer and the bulk would fill one of them. A lot
that does not convert, for want of a molar mass, may hold enough, so
it asks for a look at the bulk instead of a synthesis.

### Synthesis time from past syntheses

The synthesis time `L` of an article is the longest duration among its
last three syntheses, chosen over a median to stay generous. Until
three exist, the default (21 days) still counts, as the larger of it
and the durations so far. Ties are broken by start date and number. A
running task needs only what remains of `L` after the days it has run.
The task tracker records durations from its first day, so the estimate
improves by itself.

### Slack, latest start, priority

An article's slack is its runway minus the buffer (28 days, for QC,
filling and the unforeseen) minus `L`. The latest start is today plus
the slack. Its priority follows the slack: high under 14 days, medium
under 56, low beyond. The article's priority answers how urgently a
new synthesis is needed, and work under way does not change it. The
planning list shows that work instead, and stops offering to plan a
synthesis. A task's own slack subtracts its remaining time rather than
`L`, and answers whether that task will deliver in time; below zero it
is late. So a running synthesis lowers its task's priority, not its
article's.

### The computed priority replaces the entered one

The owner wanted the judgement out. For a planned or running task
whose product the inventory knows, the list, the page, the order and
the priority filter all use the computed priority, marked `berechnet`.
The entered priority applies to the other tasks, and to ended and
cancelled ones as recorded, marked `manuell`. There is no override. If
one is ever needed, it should come with a recorded reason, as a change
of its own. Ordering by slack means a planned task outranks a running
one of the same article. That is accepted: its slack is smaller, and
two active tasks of one article are rare.

### How much to make

A new synthesis should yield what the article lacks for the synthesis
time, the buffer and `target_days` (365) at the certainty, beyond its
containers and usable bulk. For the sizes that convert, that is one
amount of material, rounded up to a whole mg or µmol and shown also in
mg; a size that does not convert is given as a count of its own
containers.

### The delivery rhythm, shown

The item page shows the last delivery, the deliveries of the past
year, the usual interval and the next expected delivery. That answers
the owner's question of how long until the next order. The order model
already contains the same information as its rate.

### Parameters as data

The certainty, buffer, default synthesis time, history, minimum orders,
priority bands and target are one record that staff edit in the admin,
with its history, so a change of assumptions is visible and dated.

### Matching by article number, then by compound

A task's product and an item's article number match when the two texts
are equal regardless of case, or when `compound_for` finds the same
compound for both. The plan-synthesis link fills in the article number,
so a task created from it always matches its article. Batches link
tasks and lots only where the task matches the lot's article, since
batch numbers are not unique across products.

## Risks / Trade-offs

- The order model assumes orders arrive independently at a steady
  rate. A trend shows only through the recent rate, and seasons not at
  all.
- With few orders the empirical size distribution is coarse; six is a
  low bar, chosen so the model takes over soon.
- The union bound overstates the need of an article with many sizes,
  most of all when its orders come in large lumps.
- Durations of the first syntheses recorded may be unusual; the
  default carries weight until three exist.
- A computed priority is only as good as the entered history.

## Open Questions

None. The owner confirmed the defaults on 2026-11-05, with 21 days of
synthesis rather than 28.
