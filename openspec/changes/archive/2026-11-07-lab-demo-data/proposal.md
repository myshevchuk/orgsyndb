## Why

The lab application starts empty, and most of what it shows needs a
past: the planning list needs quarters of consumption, delivery notes
and ended syntheses before it computes a single priority, and the item
and task pages show histories that only time fills. Trying the
application on the test server or locally therefore shows little, and
entering a believable past by hand takes days. The owner wants a test
deployment that opens on a populated lab: one that shows every list,
state and planning action, uses the demo collection's compounds,
cannot be mistaken for real records, and never replaces records it did
not write.

## What Changes

- `manage.py demo_data`, which fills an empty database with the demo
  data as of the day it runs. It writes only with `ORGSYNDB_DEMO` set,
  refuses a database that holds lab records, and with `--replace`
  replaces only a database it seeded before.
- A demo database carries a mark of its own: every lab page then shows
  a banner saying its records are invented, with the day they were
  seeded, and the sign-in page lists the demo accounts and their shared
  password.
- The demo data: five accounts, eight articles in the end-product
  inventory about thirteen months after their opening counts, the
  consumption entered for the two years before, current and historical
  delivery notes with reversals and a correction, bulk lots and
  fillings, tasks in every state, including the two demo sequences,
  and planning parameters with a change in their history. On the day
  it is seeded, the planning list shows every priority and action.
  Each change is made with the application's clock at its own moment,
  so histories and booking times read as if the lab had kept them.
- The application container seeds an empty database when it starts
  with `ORGSYNDB_DEMO` set.

## Capabilities

### New Capabilities

- `lab-demo`: the demo mark with its banner and sign-in note, the
  `demo_data` command with its guards, and the demo data set.

### Modified Capabilities

- `web-app`: the settings read `ORGSYNDB_DEMO`.
- `container-deployment`: the application image's command seeds an
  empty database with `ORGSYNDB_DEMO` set before it serves, and the
  example settings name the flag.

## Impact

- New: a `demo` application in `webapp/` with the demo mark's model and
  migration, the data set, the code that writes it and the command;
  its tests in `webapp/tests/`. No new dependency.
- Changed: the page shell and the sign-in template, the settings, the
  German translations, `deploy/webapp/Dockerfile` and
  `deploy/orgsyndb.env.example`.
- Docs: `README.md`, on running the lab locally or in containers with
  the demo data.
- Not included: a publicly reachable demo, resetting the data on a
  schedule, and demo data for collections other than `examples/demo`.
