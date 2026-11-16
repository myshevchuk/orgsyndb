## MODIFIED Requirements

### Requirement: Structure window
`orgsyndb-structure-mode`, a buffer-local minor mode, SHALL show the buffer `*orgsyndb structure*` in a side window and, whenever Emacs has been idle for `orgsyndb-structure-delay` seconds after a command, fill it for the compound at point: the identifier of "Definitions and references" when it is a compound key. The buffer shows the compound's structure image, the file `build/substances/<key>/structure.svg` of the collection, which the last build staged (compound-registry "Structure images"), when there is one and Emacs can display SVG, and below it the compound's name and formula from the index, those it has. When point is on no compound the buffer keeps its content. Turning the mode off deletes the side window.

#### Scenario: Image and text
- **WHEN** an ERT test turns on `orgsyndb-structure-mode` in a buffer holding `isopentyl-acetate` and `acetone` of a copy of the demo collection whose `build/substances/isopentyl-acetate/structure.svg` is a copy of `webapp/demo/substances/isopentyl-acetate/structure.svg`, and runs the update with point on each in turn
- **THEN** after the first the structure buffer holds an image whose file is the collection's `build/substances/isopentyl-acetate/structure.svg`, where Emacs can display SVG, and the text `Isopentyl acetate`; after the second it holds no image and the text `Acetone`
