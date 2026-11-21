## ADDED Requirements

### Requirement: Form dialogs
Where a page opens a form in a dialog, as the specs of its pages say, the application SHALL show the form in a modal dialog over the page, which stays as it is behind it; the address does not change. The dialog is headed by the form's title and holds the form's fields and buttons. `Abbrechen` (`Cancel`), the Escape key and the dialog's close button close it and save nothing. Invalid input, and a booking the application refuses, show the form again in the dialog with the errors beside their fields and save nothing; a button that only fills in the form, such as `Menge vorschlagen` (`Propose amount`), fills it in the dialog. Once the form is saved, the dialog closes, the message naming the record shows as it does above a page, and the page shows the changed record as a reload would, without being loaded anew: its scroll position, the item chosen in it, the selections and view controls a user set in it, and what else it shows stay as they were. A user who is no longer signed in when the form is requested or saved is led to the sign-in page, which leads back to the page. A form opened so keeps its URL: requested as a page, by a reload or a link opened in a new tab, it shows as a complete page and leads where it led before (Scripts).

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
- **WHEN** a page requests an item's filling form for a dialog without a signed-in user
- **THEN** the answer leads the page to the sign-in page with the page's address to return to
