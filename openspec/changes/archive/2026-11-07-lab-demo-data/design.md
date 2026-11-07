## Context

Lab records change only through the application's own write paths:
counts and amounts through `inventory.bookings`, which keeps every
quantity equal to its movements and refuses dates after today, and
tasks through their model, which numbers them from a counter. Every
write reads the time from `django.utils.timezone`: bookings stamp
`booked_at` and `entered_at` and take today from it, `auto_now_add`
stamps `created_at`, a reversal is dated today, and
django-simple-history dates each history record when the save writes
it. The planning list reads up to twelve quarters of consumption, the
delivery notes of the latest of them and the durations of ended tasks,
so a database without a past shows almost nothing there.

Two deployments run the lab: `manage.py runserver` on SQLite, and the
Compose stack on PostgreSQL on a test server. That server binds the web
service to loopback through a Compose override of its own, outside the
repository, and is reached through an SSH tunnel. Both use the demo
collection `examples/demo`. The owner keeps the demo private to these
two, seeds when the database is empty, and accepts one shared,
published password for the demo accounts.

## Goals / Non-Goals

**Goals:**

- A populated lab on the day it is seeded: every list, state, level
  and planning action visible, with histories that read as a past.
- No path by which the command deletes records it did not write, and
  no database it wrote whose pages do not say so.
- The same records on SQLite and PostgreSQL, from one image.

**Non-Goals:**

- A demo reachable from the internet, with abuse limits and resets.
- Keeping the data current as days pass after seeding.
- Demo data for another collection.

## Decisions

### A runtime flag, not a demo build

`ORGSYNDB_DEMO` permits the command to write demo data, in the image and
checkout that serve real records. The settings already come from the
environment, and the Compose stack reads `orgsyndb.env`, so the switch
sits next to the database it concerns.

Rejected:
- A separate image or Dockerfile target: two images to keep in step
  for one switch.
- A demo settings module: a second place where settings are decided,
  beside `config.settings_from`.

### The database carries the mark, the process carries consent

The flag describes a process, not a database: set on a stack whose
database holds real records, it could not by itself keep `--replace`
from deleting them, and a database seeded under it would lose its
banner when the flag was switched off. The data set therefore writes a
demo mark, a row of its own model holding the seeding day, into the
database it fills. `--replace` deletes only a database holding the mark
or no lab records at all; any other is left to an explicit
`manage.py flush`. The banner and the sign-in note follow the mark,
one query per page, so a demo database says what it is whatever the
flag, and a real one is never labelled invented. The flag remains the
operator's consent to write demo data at all, which keeps an empty
production database from being seeded at its first start.

Rejected:
- The flag alone as the gate: it cannot tell a real database from a
  disposable one.
- Recognising a demo database by its accounts: a person could create an
  account named `klehmann` in a real one.

### A timeline replayed through the write paths, on its own clock

The data set is a list of dated changes, produced by a pure function of
the seeding day: create an item with its opening count, enter a
quarter's consumption, book a current or historical note, fill from a
lot, correct, reverse, create or correct a lot, create, start, end or
flag a task, store or change the planning parameters. The writer makes
the changes in order through `inventory.bookings` and the models' own
saves, each with `django.utils.timezone.now` patched to the change's
moment, as the tests already freeze the clock. Every write path then
stamps the right time itself: the history record written by the save
that makes a change, `created_at` through `auto_now_add`, `booked_at`,
`entered_at`, a reversal's date, and the "today" against which future
dates are refused. No record is moved after it is written and no
history record is added to repair one. Moments rise through the day
from 08:00, so the lists that order by recording, movements and
histories, read in date order, and task numbers follow creation dates.

Tasks are saved after `full_clean()`, so their dates and steps obey the
rules the task form applies. Sequence steps are part of the data set,
written to `sequence_steps` with `steps_total`, so a task does not
depend on the index; the form's lookup through `sequence_for` is not
used.

The change list is pure data, so its own rules are tested without a
database: no moment after the seeding day, moments in order, and every
replayed quantity and amount at least zero.

Rejected:
- Moving times after each write: the history record already written
  keeps the time of its save, and saving again adds a change that never
  happened.
- A `now` parameter on every booking: it widens the application's
  interface for the seeder's sake.
- Django fixtures: their dates are fixed and age at once; their rows
  bypass the bookings, so a quantity and its movements could disagree;
  their histories would be written by hand.
- Random factories such as factory_boy or Faker: a dependency, and
  random records do not reach chosen planning states.

### Dated back from the seeding day

Every moment is the seeding day `D` less a number of days, from the
opening day `O`, `D` less 400 days, to `D`. What the records name may
lie earlier: the quarters of entered consumption, counted back from the
quarter of `O`, and the dates of historical notes, in the quarter
before it. Both are entered in the first 30 days from `O`, as a lab
would enter its paper records when it starts using the inventory. The
data never lies in the future and is fresh when seeded. It ages
afterwards, its runways shortening and its running tasks growing
older; `--replace` renews it. The owner chose this over reseeding on
every start, which would lose what was changed while trying the
application.

### Outcomes held by calibration

Quarter and year boundaries move relative to `D`, so the figures vary
with the seeding day, and not only slightly: the order window holds
six complete quarters for some days and five for others, a model can
switch at `min_orders`, and the mean per quarter behind the levels
divides by every calendar year from the first with data, so a partial
first year lowers it to between three quarters and all of the rate.
The data is calibrated to margins rather than trusted to steadiness:

- an article meant for the order model has at least twice
  `min_orders` orders in its shortest order window, and one meant for
  the quarterly model at most half of it in its longest;
- each article's slack lies at least ten days inside its priority band
  on every tested day, and a task meant to be late has a slack below
  minus ten days;
- each item meant for a level holds a quantity inside that level's
  range for every mean between three quarters of its rate and its
  rate.

The tests seed at the start, middle and end of quarters, on a day whose
order window has six quarters, and on a leap day, and check the levels
and the planning list on each.

### The same records whatever the index

The writer gives every filling its amount, computed with the molar
masses the data set holds for its articles, and writes sequence steps
itself, so nothing it writes reads the index. Its free texts exist in
German and English, and the command takes the language of the index,
German without one. The data is designed for `examples/demo`: with
another index its products show as not in the collection and µmol and
mg do not convert. The command therefore warns when the index lacks a
compound the data names, and seeds all the same.

### Accounts

Five accounts with invented names. `klehmann` is a superuser, so that
the admin can be shown. `mwolf` has no usable password: a former
member named on the records of the first weeks. The other accounts'
password, `demo`, is set with `set_password`, past the validators the
forms apply, and the sign-in page of a demo database states it.

## Risks / Trade-offs

- An operator who sets the flag on a stack with an empty production
  database gets it seeded at the next start. The banner and the
  sign-in note then show on every page, and the example settings say
  the flag is for test deployments only.
- The clock is patched process-wide while the command runs. The
  command runs alone in its own process, and the tests that call it
  freeze the clock already.
- The planning figures drift as the data ages; `--replace` renews
  them, discarding what was changed since.
- Seeding books a few thousand rows. On SQLite it should take seconds;
  the tests that seed several days share one data set per day.
