## Why

The site-theme spec says narrower windows stack the columns in document
order, but the home page's browse lists stay side by side at every width
below 70rem, and no scenario covers narrow windows.

## What Changes

- Stack the home page's browse lists in one column below 35rem.
- Add a narrow-window scenario to the measure requirement, checked by a
  static test of the screen stylesheet.

## Impact

Affects the site-theme capability, `screen.css` and
`tests/test_theme_static.py`.
