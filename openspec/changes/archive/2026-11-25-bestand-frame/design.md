## Context

The lab application's pages share the site's shell: a sidebar
(`header.site-header`) beside `main`. The Bestand lists today are
ordinary scrolling pages. The approved reference is the screenshot
series `widget-mockups-2` (fixed 1440 × 900 viewport, 124 px of
chrome above the table head).

## Goals / Non-Goals

Goals: the four Bestand lists fit the window with only their tables
(and the item list's details pane) scrolling; less chrome; the demo
notice in the sidebar. Non-goals: new views, new tabs, the layers of
Endprodukte, other pages' layout.

## Decisions

- **Opt-in frame.** A Bestand list marks its `body` (a class such as
  `lab-frame`) through the template's `body_class` block; only marked
  pages get the fixed height, so other pages keep scrolling.
- **Height chain.** In a marked page at `min-width: 900px`, `html` and
  `body` take the window's height with `overflow: hidden`; `main` is a
  flex column of the heading, tabs and toolbar (`flex: none`) and the
  table area (`flex: 1; min-height: 0`); the table's scroll box takes
  the remaining height with `overflow: auto` and its `thead` stays
  sticky. In the item list's details view the table and the pane each
  scroll in their own box. The sidebar is already the window's height;
  its navigation scrolls inside it when it is taller.
- **Below 900 px** the frame switches off and the page scrolls as now,
  since a fixed height leaves too little table on a small screen.
- **Chrome budget** (at 1440 × 900): heading line about 40 px, tabs
  about 36 px, toolbar about 40 px. The heading is one line: `h1` at a
  smaller size, the count beside it, actions at its right end. Filter
  labels become visually hidden labels or a prefix inside the control
  (`Kategorie: Alle`), keeping an accessible name. The item list's
  caption ("43 von 43 Artikeln · …") moves into the heading line's
  count; `Zeilenhöhe` and `Verbrauch einfärben` with its legend move
  into a `Ansicht` menu beside `Spalten`; `Tabelle | Details` is the
  toolbar's last control.
- **Demo notice** leaves `main` and stands in the sidebar between the
  navigation and the account links, smaller, wrapping in the sidebar's
  width. With the sidebar collapsed it is hidden with it; it remains
  in the document, so it shows once on every page.
- **Print** keeps today's output: the frame applies to the screen
  only.

## Risks / Trade-offs

- A page whose table is shorter than the window shows empty space
  below it inside the frame; that is accepted, as in the mockups.
- Browser-only behaviour (heights, scrolling) has no test in the
  suites; it is checked with screenshots at 1440 × 900 and 800 × 900.
