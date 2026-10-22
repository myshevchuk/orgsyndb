## Layout

Use the desktop layout as the screen default. A 96rem shell provides room
for data tables without stretching indefinitely on very wide monitors.
The home page has a flexible recent-procedures column and a 19rem browse
column. Procedure pages have a 23rem details column and a flexible body;
paragraphs and lists keep a 78ch reading measure while tables use the
available width. Smaller browser windows reduce or stack these columns.

## Rendering and accessibility

Keep layout rules in screen.css so browsers and WeasyPrint retain the
existing single-column A4 flow. Add neutral wrappers around the procedure
details and body without changing document or Pagefind indexing order.
Keep keyboard-focusable table scrolling, headings, labels and navigation.
Both color schemes continue to use the existing contrast-tested tokens.

## Design exploration

The reference-library concept uses editorial typography and a light
paper surface. The research-workbench concept uses persistent sidebar
navigation and denser data panels. The night-lab concept uses dark
surfaces and a compound preview. These concepts are static review aids;
the application change retains the established visual style.

## Verification

Build the German demo and run the full suite, including English/German
index queries and A4 PDF content checks. Inspect static desktop renders.
Live browser visual checks remain unavailable because this session has no
browser-control tool; static renders are not browser screenshots.
