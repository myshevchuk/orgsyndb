# Understanding production planning

The forecast helps you decide when to fill containers from bulk, when to
start a synthesis, and how much it needs to produce. Bulk is material held
in lots for filling containers. The forecast replaces a personal estimate
of urgency with the same calculation for everyone. You can see the stock,
demand, synthesis time, and assumptions behind the result.

Diese Anleitung gibt es auch auf Deutsch: [PLANNING.de.md](PLANNING.de.md).

## Find the figures behind a priority

Open **Planning (Planung)** between **Inventory (Bestand)** and **Tasks
(Aufgaben)** in the navigation. The list shows articles with high or medium
priority and articles with an action due. It puts the smallest **Slack
(Spielraum)** first: this is the time left before a new synthesis needs to
start. Choose **All articles (Alle Artikel)** to see every article with a
forecast.

An *article* groups all container sizes with the same article number. Each
size has its own stock and demand. Follow a container size to its inventory
page and the **Forecast (Prognose)** section for the calculation's basis.
The task page also shows the forecast for its product.

The line above the planning table gives the parameters currently in force.
The defaults in this guide apply unless staff have changed them.

## How the application estimates demand

The forecast uses deliveries recorded in the inventory as consumption. It
looks back over the last 12 complete quarters by default. A quarter is
three months. It leaves out quarters before the first recorded data and
does not use the current, incomplete quarter to estimate demand.

It chooses between two *demand models*: two ways to describe how many
containers future deliveries may need.

### When there are enough individual orders

The **order model** uses dated delivery-note lines, each with the number of
containers delivered. It needs at least six orders by default. Those orders
must fall within the history period, in quarters after the latest quarter
with a manually entered consumption total. If there is no entered total,
the whole history period is available.

The calculation uses how often orders arrive and how large they have been.
It compares the order rate over the available period with the rate over its
last four quarters and uses the higher one. With fewer than four quarters,
it uses all available quarters. This lets a recent increase in demand count
without waiting for the older history to catch up.

Future orders are assumed to arrive independently at that rate. Each order
is assumed to have a size drawn at random from the past orders. The
application calculates the chance that their combined demand fits within
the stock. The probability calculation is exact for these assumptions.

On the page, **λ** means orders per day. The **median** order size is the
middle size after sorting the past orders, or the average of the two middle
sizes. The page also shows the number of orders and the largest order.

You can give this model more history by entering old paper delivery notes
as **entered later – stock unchanged (nachgetragen – Bestand bleibt
unverändert)**. These historical notes contribute to demand without
changing today's stock.

### When there are too few individual orders

The **quarterly model** uses consumption totals per quarter instead. It
compares the average over the history period with the average over the last
four quarters and uses the higher one. It also uses how much the quarterly
totals vary.

On the page, **m** is the average number of containers per quarter used in
the forecast. **v** measures the variation between quarters. The calculation
sets v at least as high as m, so identical past totals do not make the
forecast treat demand as perfectly steady.

Figures from this model carry **rough (grob)**. Quarterly totals do not tell
the application when individual orders arrived or how large they were.
The stated certainty is therefore approximate. If any size uses this
model, the article's forecast is also marked rough.

An item with no consumption in the history period has no forecast. Its
page says **No consumption, no forecast. (Kein Verbrauch, keine Prognose.)**
Missing history does not establish that stock will last indefinitely.

**Demand per year (Bedarf/Jahr)** shows the model's expected annual
consumption in containers, separately for each size.

## Read runway as time at a chosen certainty

**Runway (Reichweite)** is how many days the stock covers the forecast
demand at the chosen **Certainty (Sicherheit)**. The default is 95%: under
the model's assumptions, the stock covers demand over that period with at
least a 95% chance. A higher certainty calls for more stock for the same
period and gives the existing stock a shorter runway.

Large, occasional orders matter. Suppose orders take 10 containers about
once a quarter, and you have nine containers. You cannot cover the next
order. At 95% certainty, the order model gives a runway of **4 days**. A
rough calculation from the quarterly totals of the same history gives
**47 days**. Average consumption alone hides the risk of one large order.

In the order model, even zero stock can have a short positive runway. This
is the period during which no order arrives with the chosen certainty.
It does not mean any containers are available; the inventory still shows
the stock as used up.

### Several sizes share one supply of bulk

**Runway on hand (Reichweite des Bestands)** uses only the filled containers
of that size. The article's runway also includes usable bulk.

A synthesis replenishes the article's bulk, which serves all its sizes.
The calculation first uses each size's filled containers. It then works out
how the shared bulk can cover the missing containers so every size lasts
for the same period. It counts the bulk once.

To cover all sizes together at 95%, the calculation uses a higher certainty
for each size with demand. With two sizes, it uses **97.5% per size**. In
general, it divides the allowed 5% risk among the sizes. This is why a
size's certainty in the article calculation can differ from its certainty
under Runway on hand.

### Why usable bulk is smaller than the recorded amount

**Usable bulk (Nutzbares Bulk)** allows for filling whole containers from
separate lots. For each open lot, the calculation subtracts the article's
largest container size among the sizes with demand. A lot smaller than
that size contributes zero. Missing containers are also rounded up to
whole containers.

For example, with 10 mg and 20 mg sizes and one lot of 360 mg, the forecast
counts **340 mg** as usable bulk. With no filled containers and quarterly
demand of nine containers per size in each of 12 quarters, the article's
runway is **62 days** at the default certainty. Giving each size the whole
lot would count the same material twice.

Two separate lots of 6 mg cannot fill a 10 mg container. Their combined
12 mg therefore contributes **zero usable bulk** to that article.

Converting between mg and µmol needs the compound's molar mass. A lot that
cannot be converted is excluded from usable bulk and triggers **Check bulk
(Bulk prüfen)**. A size that cannot be converted relies on its own filled
containers and can limit the article's runway.

## Work out when synthesis needs to start

**Synthesis time (Synthesedauer)** is the longest duration of the article's
last three completed syntheses. Cancelled tasks do not count. Until three
completed syntheses exist, the calculation also includes the default of
21 days. One completed synthesis taking ten days therefore still gives a
21-day estimate; a longer recorded synthesis can raise it.

The **buffer (Puffer)** is the time between the synthesis ending and its
product being ready for delivery. It allows for quality control (QC),
filling, and the unforeseen. The default is 28 days.

The calculation subtracts both times from the runway:

**Slack = runway − buffer − synthesis time.**

Slack tells you how many days remain before a new synthesis needs to start.
**Latest start (Spätester Start)** is today plus that slack. A negative
slack puts the latest start in the past: starting today would already leave
too little time under the forecast's assumptions.

Priority follows the slack. With the defaults:

| Slack | Priority |
| --- | --- |
| Less than 14 days, including negative values | high (hoch) |
| At least 14 days, less than 56 days | medium (mittel) |
| At least 56 days | low (niedrig) |

For example, an article with ten 1 mg containers, no bulk, and quarterly
consumption of nine containers in each of 12 quarters has a displayed
runway of 60 days. With the default synthesis time and buffer, its slack
is 11 days and its priority is high.

Runway and slack are displayed as whole days rounded down. The latest
start also uses slack rounded down. Priority comparisons use the values
before rounding.

## Check whether a running task can finish in time

The article's priority answers how urgently a **new synthesis** is needed.
It continues to use the full synthesis time even when work is running.
The planning list shows planned and running tasks beside it, with their
expected end dates.

A task's own slack answers whether **that task** can supply the product in
time. A planned task needs the full synthesis time. A running task needs
only the estimated synthesis time minus the days since its start, with a
minimum of zero. Its expected end is today plus this remaining time.

The task's slack is runway minus buffer minus its remaining time. In the
example above, a synthesis started 14 days ago has a task slack of
**25 days** and medium priority. The article still has high priority. The
two priorities answer different questions.

Below zero, the task's own slack is marked **late (verspätet)**. It means
the estimated remaining work and buffer no longer fit within the runway.

For planned and running tasks with a matching forecast, the application
uses this priority everywhere it shows, sorts, or filters tasks. It marks
it **computed (berechnet)**; pointing at the priority shows the slack in days.
All other tasks, including ended and cancelled tasks, keep the priority
entered in the form, marked **entered (manuell)**. You cannot override a
computed priority by changing that field.

A task matches the article of its substance, when the substance has one.
It therefore matches at most one article. An article without an article
number has no consumption and no forecast. Tasks that match it show their
entered priority.

## Choose the next action

The **Actions (Maßnahmen)** column offers the actions whose conditions
apply:

| Action | Why it appears and what it opens |
| --- | --- |
| **Fill (Abfüllen)** followed by a size | That size's filled containers last less than the buffer, and the open lots can fill at least one container. Open the filling form for that size. |
| **Check bulk (Bulk prüfen)** | An open lot cannot be converted because the molar mass is missing. Open the bulk list to check it; the lot may contain enough material to avoid a synthesis. |
| **Plan synthesis (Synthese planen)** | Priority is high or medium, no matching task is planned or running, and every open lot of the article can be converted. Open a new task with the article's substance key filled in, together with the sequence and proposed start step when a sequence makes that substance. |

A *sequence* is an ordered route through synthesis steps. For each
sequence in the collection that makes the article's substance and is not
withdrawn, the action reads **Plan synthesis via &lt;ID&gt; (Synthese planen
über &lt;ID&gt;)**. The actions appear in sequence-ID order. If no sequence
makes the substance, the action remains **Plan synthesis (Synthese
planen)** and fills in only the substance key.

To skip work whose product is already in stock, planning proposes the
latest step whose preceding step's *intermediate* has an open lot.
The intermediate is the first product of one step that the next step
takes as a substrate. An open lot has an amount above zero; made and
bought lots both count. If none is in stock, planning proposes step 1.
For a later step, the action adds **from step &lt;k&gt;, &lt;name&gt; in stock
(ab Stufe &lt;k&gt;, &lt;name&gt; vorrätig)**, naming that intermediate.

Planning reserves nothing and does not check whether the lot holds
enough. Check the amount and confirm or change **Start at step (Beginn
ab Stufe)** in the task form. The task's sequence must make its substance;
its steps start at the step you choose. Skipping steps does not shorten
the forecast's synthesis time.

Plan synthesis is a link when you are signed in and plain text otherwise.
Saving the new task makes it appear beside the article and removes that
action while the task is planned or running.

### How much a new synthesis needs to yield

On the item's forecast, **New synthesis (Neue Synthese)** is the additional
material needed to cover:

**synthesis time + buffer + target coverage.**

Target coverage is 365 days by default. The calculation uses the same
certainty for each size as the article's runway. It deducts existing filled
containers and usable bulk, then rounds the missing material up to whole
mg or µmol. An amount in µmol is also shown in mg. If a size cannot be
converted, its missing amount appears as a count of its own containers.

After a synthesis ends, a signed-in user can use **Record as bulk (Als Bulk
erfassen)** on a task with a batch and a matching article. It opens a new
lot with the article, batch, and end date filled in. Enter the amount and
save it. The task and lot pages link records with the same batch only when
their articles also match.

## Read the delivery rhythm

The item's **Delivery rhythm (Lieferrhythmus)** shows the last delivery and
the number of deliveries in the past 365 days. With at least three
delivery notes in the past 730 days, it also shows the **Usual interval
(Übliches Intervall)**. This is the median gap between consecutive
deliveries, rounded to whole days.

**Next delivery expected (Nächste Lieferung erwartet)** adds that interval
to the last delivery date. It describes the recorded rhythm; it does not
predict a particular customer's next order. Reversed deliveries and
reversed historical notes do not count.

## Who changes the assumptions

Staff with access to the administration change one shared **Planning
parameters (Planungsparameter)** record at
`/lab/admin/planning/parameters/`. Its change history records changes to
the assumptions. The planning page shows the values in use. Without a
saved record, the defaults apply.

| Parameter | Default | Allowed values |
| --- | --- | --- |
| Certainty (Sicherheit) | 95% | 50–99.9% |
| Buffer in days (Puffer in Tagen) | 28 | 0–365 |
| Default synthesis time in days (Synthesedauer ohne Historie in Tagen) | 21 | 1–730 |
| History in quarters (Historie in Quartalen) | 12 | 4–40 |
| Minimum orders (Mindestzahl der Aufträge) | 6 | 3–100 |
| High priority below days (Hohe Priorität unter Tagen Spielraum) | 14 | At least 0; below the medium threshold |
| Medium priority below days (Mittlere Priorität unter Tagen Spielraum) | 56 | Above the high threshold |
| Target coverage in days (Zielreichweite in Tagen) | 365 | 30–1095 |

## What the forecast cannot tell you

The forecast depends on the entered history. The order model assumes
independent orders at a steady rate. A trend appears only through the
comparison with the recent rate. Neither model accounts for seasons or
predicts individual customers' orders.

With few orders, the past order sizes give a limited picture of future
sizes. The quarterly model remains rough. Covering several sizes together
can make the estimate generous, especially with many sizes and large,
occasional orders. Early recorded synthesis durations can also be unusual;
the default continues to count until three completed syntheses exist.

The forecast does not schedule people or equipment or send notifications.
It leaves the inventory's existing stock levels unchanged. Use the figures
and their basis to decide what needs attention; a displayed certainty
depends on the model's assumptions and the quality of the records.
