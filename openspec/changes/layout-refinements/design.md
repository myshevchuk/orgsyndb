# Design: Layout refinements

## Decisions

### 1. Width

`body` in `site/assets/css/screen.css` loses `max-width: 96rem`, as
`body.lab-frame` already did. Elements that set their own measure keep
it: `.lede`, help prose (`64ch`), `.lab-form` (`40rem`). Tables,
widget grids and cards take the full width.

### 2. Layout picker

`view_switch.html` renders one `fieldset.layout-picker` with three
radio-styled buttons, each an icon with a visually hidden label:
`Tabelle` (table only), `Details, Tabelle größer` and `Details, Details
größer` (`Details, larger table` / `larger details`). The two Details
buttons set the view cookie to `details` and the split cookie to
`first` or `second`; the table button sets the view to `table` and
leaves the split cookie. Without scripts the three radios switch the
view in CSS, as the two did before, and the ratio stays at its cookie. The picker is one tab stop; arrow keys move
within it (native radio behaviour). The `split#toggle` button and its
"Größere Fläche" label go. Rejected: one cycling button (next state
hidden, up to two clicks); two separate toggles (owner chose the
picker).

### 3. Substance pane

`c-widget-grid columns="2"` holds two `widget-grid__col` columns: the
compound widget on the left, containers, batches and tasks on the
right.

### 4. Back links

`back.html` takes the record's key and renders `href="<list>?selected=
<key>"` with `data-lab-action` on a small `back-link` controller in
`lab.js`: on a plain primary click, when `document.referrer` has this
origin and the link's path, and `history.length > 1`, it prevents the
default and calls `history.back()`. Anything else follows the link.
The notebook page passes no key. The page marks the history entry it
loaded in (`history.state.backEntry`) and goes back only from that
entry, so an entry a skip link added is never the one left.

## Risks

- A referrer from the list in another tab cannot be told apart; going
  back then leaves this tab's own history, which still shows that list.
