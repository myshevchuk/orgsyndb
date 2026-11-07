## Context

The lab application serves `/lab/` beside the static site, which
`orgsyndb-deploy` builds ahead of time; Caddy forwards `/lab/` to the
application and serves everything else from the build. `/lab/` now
redirects to `/lab/tasks/`. Lab pages carry no script (web-app "Page
shell"); the static site may run scripts that only add to its content
(site-theme "Content does not need JavaScript") and link exactly the
theme's three stylesheets (site-theme "Stylesheets by medium"). A
build with `ORGSYNDB_LAB=true` sets `params.lab`, and its header then
links the lab's views. The data the overview shows lie in three
packages: levels and consumption in `inventory`, forecasts and task
slack in `planning`, tasks in `tasks`.

## Goals / Non-Goals

**Goals:**

- One page that answers how the stock stands, what to make next and
  how much went out, readable without signing in.
- How the stock stands on the site's home page wherever the lab runs.

**Non-Goals:**

- Figures the lab does not keep: intermediates, QC, purchases.
- Choosing the period or the articles shown.
- Keeping the overview up to date without reloading.

## Decisions

### A package of its own

`overview` reads `inventory`, `planning` and `tasks` and owns none of
their records, so it depends on them and they on nothing of it. Its
figures are functions of the delivery lines, items, forecasts and tasks
read once per request; the volumes, some hundred notes a year, need no
aggregation in the database.

### Deliveries from the notes

"Delivered" counts the delivery lines that count as consumption, dated
by their note: a reversed delivery does not count, a note entered later
does. Entered quarterly consumption has no day, so it cannot be split
into months or cut at today's date a year ago, and the overview leaves
it out. Past years entered only as quarterly values therefore show no
deliveries; the comparison with last year is meaningful from the first
year of notes on.

### A stock bar without a script

The bar is a flex row of links, each `flex-grow` set to its count by a
`style` attribute, the one inline style of the lab, with a minimum width
so that a level of one item stays a target. Its colours are the level
classes of the item list.

### The next syntheses are the planning list's first

Ordering by slack, then article number, is the planning list's order,
taken over the articles with a forecast, whether listed there or not, so
the overview's first five are the planning list's first five with
`all=1`. "Syntheses due" counts the high and medium priorities the
planning list lists without `all=1`; late tasks are those whose slack
the planning computes below zero.

### The chart drawn on the server

Like the consumption chart of an item's page, the deliveries per month
are an inline `svg` drawn in Python: twelve pairs of bars, the year
before's grey and beside, each titled with its month and value so a
pointer or a screen reader reads the numbers.

### The home page frames a summary

The home page is built before the lab knows its numbers, so it cannot
carry them. The theme allows three stylesheets on its pages and no
script that adds content, so the home page cannot take the lab's markup
and styles in. In a lab build `home.html` writes `section.home-lab`
with an `iframe` of `/lab/summary/` and a link to `/lab/`. The framed
page is a lab page: it links the lab's stylesheets, follows the same
colour scheme, and needs no script. Its `base target="_top"` opens
every link in the window, not the frame.

A frame does not size itself to its content without a script, so the
summary holds only what fits a fixed height: the stock bar and the
four figures. The site's stylesheet gives the frame the content's width
and a height that shows them whole, taller where the figures wrap on a
narrow screen. The rest of the overview stays at `/lab/`, one link
away.

Django refuses framing by default; the summary alone answers
`X-Frame-Options: SAMEORIGIN`. The site and the lab share a host behind
Caddy, so the frame is same-origin. Like the header's links to the
lab's views, the frame works at the host's root only, which the prefix
requirement now states.

## Risks / Trade-offs

- A fixed frame height clips the summary if its content grows. → The
  summary is the bar and four figures; a test pins its parts, and the
  frame scrolls rather than hides what does not fit.
- The home page requests the lab on every visit. → One page computed
  from a small database; Caddy already sends `no-cache`.
- Without the lab running, the frame shows Caddy's error. → A lab
  build is deployed with the lab; the link below the frame stays.
- Links that expected `/lab/` to open the tasks. → The sign-in still
  redirects to `/lab/tasks/`, and the navigation links every view.
