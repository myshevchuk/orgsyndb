## ADDED Requirements

### Requirement: Structure images
A substance SHALL have a structure image only when its snapshot entry's `molfile` is a string. The build stages the images as `build/substances/<key>/structure.svg` in the collection, `<key>` being the substance's key, creating `build/substances/` when it is missing, and removes from it everything that is not the image of a substance with a molfile.

For a registry named by an address, a substance with a molfile has the image that answers a GET of `substances/<key>/structure.svg` resolved against that address, which on a lab application is the substance's image address (lab-registry "Structure images"). The build requests it with a timeout of 30 seconds and stages the body of an answer of status 200. A substance whose request is answered with another status, or gets no answer, keeps the image an earlier build staged, if any. Once a request gets no answer, the build requests no further image in that run. When an image is not staged, the build writes to stderr one warning naming how many were not and the first one's address with the reason.

For a registry named by a path, a substance with a molfile has the image that the file `substances/<key>/structure.svg` in the snapshot file's directory holds, when that file exists; the build stages a copy of it. A substance without that file has no structure image, and its staged image is removed.

The data the build stages for a substance with a staged image sets `structure_image` to `substances/<key>/structure.svg` (site-build "Hugo configuration"); that is what the site's requirements mean by a compound that sets `structure_image`. No other file is a structure image: a file of the collection's `static/structures/` is a static file whatever its name, and no check reports a substance without an image.

#### Scenario: Images from the lab
- **WHEN** a test serves a snapshot of the test collection's registry in which `isopentyl-acetate` has a molfile and every other substance the `molfile` `null`, serves an SVG at `substances/isopentyl-acetate/structure.svg` beside it, and builds a copy of the test collection that names the snapshot's address
- **THEN** `public/substances/isopentyl-acetate/structure.svg` holds the served SVG, the staged data of `isopentyl-acetate` sets `structure_image` `substances/isopentyl-acetate/structure.svg`, and `build/substances/` holds no other file

#### Scenario: Images beside a snapshot file
- **WHEN** a test writes `static/structures/acetone.svg` into a copy of the test collection, whose `registry.json` gives `isopentyl-acetate` and `acetone` a molfile and has `substances/isopentyl-acetate/structure.svg` beside it and no image of `acetone`, and builds the copy
- **THEN** `public/substances/isopentyl-acetate/structure.svg` is byte-identical to that file, the staged data of `acetone` sets no `structure_image`, and stderr holds no warning about images

#### Scenario: The lab is down
- **WHEN** the server of "Images from the lab" stops and the copy is built again
- **THEN** `public/substances/isopentyl-acetate/structure.svg` still holds the served SVG, and stderr holds the warning of the registry's copy and one warning naming the image's address

#### Scenario: A lab that stops answering
- **WHEN** a test serves a snapshot in which two substances have a molfile, closes every connection that requests an image without answering, and builds a collection that names the snapshot's address
- **THEN** the server received one request for an image, and the build's warning names two images

#### Scenario: A structure removed
- **WHEN** after "Images from the lab" the served snapshot gives `isopentyl-acetate` the `molfile` `null` and the copy is built again
- **THEN** `build/substances/` and `public/substances/` hold no image of `isopentyl-acetate`, and its staged data sets no `structure_image`

## REMOVED Requirements

### Requirement: Structure images by key
**Reason**: Structure images come from the registry, drawn by the lab from each substance's molfile ("Structure images"); the collection's `static/structures/` keeps procedure scheme images.
