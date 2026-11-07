## Why

The lab's start pages say nothing about the lab: `/lab/` redirects to
the task list, and the site's home page lists procedures. Whoever opens
either sees neither how the stock stands, what to synthesize next, nor
how much went out this year. The owner asked for overview statistics
about the inventory on the start page.

## What Changes

- `/lab/` becomes `Labor auf einen Blick` (`Lab at a glance`): a stock
  bar split by level, each part linking to its items; four figures
  (containers delivered this year against the same date last year,
  syntheses due with late tasks, running and planned tasks, open bulk
  lots); the five next syntheses; deliveries per month over twelve
  months beside the year before; the most requested articles, the
  recipients and the latest delivery notes. **BREAKING** for links
  that relied on `/lab/` opening the task list.
- `/lab/summary/` shows the stock bar and the figures alone, as a page
  made to be framed.
- In a build that links the lab, the site's home page frames that
  summary in a section `Lab at a glance`, with a link to `/lab/`.
  Without the lab the home page is as before.
- Lab builds work at their host's root only, which the prefix
  requirement now says.

## Capabilities

### New Capabilities

- `lab-overview`: the overview page at `/lab/` and its summary.

### Modified Capabilities

- `web-app`: `/lab/` shows the overview instead of redirecting; the
  summary's shell, which may be framed by the same host.
- `site-theme`: the home page's lab section.
- `site-build`: the root-only exception of a lab build.

## Impact

- New: the `overview` package with its view, templates, figures, chart
  and German translations.
- Changed: the application's URLs and installed apps, `lab.css`,
  `site/layouts/home.html`, the site's stylesheets and translations,
  their tests.
- Docs: `README.md`, on the lab and the home page.
- Not included: an overview of the intermediates or QC, which the lab
  does not keep yet.
