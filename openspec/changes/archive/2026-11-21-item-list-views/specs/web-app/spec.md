## MODIFIED Requirements

### Requirement: Form dialogs
Where a page opens a form in a dialog, as the specs of its pages say, the application SHALL show the form in a modal dialog over the page, which stays as it is behind it; the address does not change. The dialog is headed by the form's title and holds the form's fields and buttons. `Abbrechen` (`Cancel`), the Escape key and the dialog's close button close it and save nothing. Invalid input, and a booking the application refuses, show the form again in the dialog with the errors beside their fields and save nothing; a button that only fills in the form, such as `Menge vorschlagen` (`Propose amount`), fills it in the dialog. Once the form is saved, the page shows what a reload would show, without being loaded anew, and then the dialog closes: the message naming the record shows as it does above a page, and every part of the page that the save changed, such as the record's heading and links, the rows and their order, colours and counts of a list, shows its new state. Its scroll position and the selections and view controls a user set in it stay as they were, and so does the item selected in it while that item is still listed; otherwise the item a reload would select is selected, and the address names it. A user who is no longer signed in when the form is requested or saved is led to the sign-in page, which leads back to the page with its address unchanged, and nothing is saved (Permissions). A form opened so keeps its URL: requested as a page, by a reload or a link opened in a new tab, it shows as a complete page that posts as a page and leads where it led before (Scripts).

#### Scenario: The form alone for a dialog
- **WHEN** a signed-in user's page requests the filling form of an item for a dialog, and requests the same URL as a page
- **THEN** the first answer holds the form headed by its title and no page header or navigation, and the second is the complete form page

#### Scenario: Errors stay in the dialog
- **WHEN** a signed-in user's page posts the count correction of an item for a dialog with a count that is not a number
- **THEN** the answer is the form alone with the error at the count, and the item's count is unchanged

#### Scenario: Saved in a dialog
- **WHEN** a signed-in user's page posts a valid count correction of an item for a dialog
- **THEN** the count is corrected, the answer shows nothing in the dialog and tells the page that the item was saved, and the next page the user requests shows the message `Bestand von <item> korrigiert.`

#### Scenario: Signed out meanwhile
- **WHEN** the page `/lab/inventory/end-products/?q=CH&selected=3`, without a signed-in user, requests an item's filling form for a dialog, and posts it
- **THEN** each answer leads the page to `/lab/accounts/login/` with `next` the page's whole address, and nothing is booked

#### Scenario: The form page posts as a page
- **WHEN** a signed-in user requests the filling form of an item as a page
- **THEN** its form posts to its URL without htmx, and a valid post redirects to the item's page

#### Scenario: Refreshed parts come from the page
- **WHEN** a signed-in user requests the item list and an item's page
- **THEN** the list marks as refreshed parts its count, its summary, its stock filter, its table body and its details, and the item page everything below the page's header

