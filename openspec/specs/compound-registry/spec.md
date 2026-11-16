# compound-registry Specification

## Purpose
Define where a collection's compounds come from: the lab application's registry the collection names, how every tool reads it and keeps a copy, the checks the validator makes of it, and the structure images the build stages from it.
## Requirements
### Requirement: Registry source
A collection SHALL name its registry in its `orgsyndb.toml` as `registry`, a non-empty string: an address beginning with `http://` or `https://`, of a lab application's snapshot (lab-registry "Snapshot"), or a path of a snapshot file, relative to the collection directory unless it is absolute. The environment variable `ORGSYNDB_REGISTRY`, when set and not empty, takes its place. A collection that names none, or names a value of another type, is a configuration error naming `registry`. The registry's substances are the collection's compounds: a procedure, a sequence and every page of the site name a compound by its substance's key, and two of them name the same compound exactly when they name the same key. The collection holds no `compounds/` and no `vocabularies/` directory; one that does is read as if it had none.

#### Scenario: Registry named by a path
- **WHEN** a test writes a snapshot file `registry.json` into a temporary collection whose `orgsyndb.toml` holds `format = 1` and `registry = "registry.json"`
- **THEN** `pipeline.registry` on that collection returns the file's table

#### Scenario: The environment wins
- **WHEN** the collection names `registry.json` and `ORGSYNDB_REGISTRY` names another snapshot file
- **THEN** `pipeline.registry` returns the other file's table

#### Scenario: No registry named
- **WHEN** a collection's `orgsyndb.toml` holds `format = 1` alone and `ORGSYNDB_REGISTRY` is not set
- **THEN** `pipeline.registry` raises `validate.ConfigError` naming `registry`

### Requirement: Reading the registry
`pipeline.registry(collection, store=True)` SHALL return the collection's registry as a table, and every tool SHALL take the registry from it: the validator, through the file `orgsyndb validate` passes it; the build, which `serve` and `pdf` run; and `orgsyndb index`. For a path it reads the file. For an address it requests the snapshot with a timeout of 30 seconds and takes the body of an answer of status 200 that is a snapshot. It then writes the snapshot to `build/registry.json` in the collection, unless the path is that file, and the source, as the collection or `ORGSYNDB_REGISTRY` names it, to `build/registry.source`, and returns the snapshot; so `build/registry.json` holds the registry the tools last read. When the request fails, or the answer is not a snapshot, it returns the snapshot in `build/registry.json` when `build/registry.source` holds the same source, and writes to stderr a warning naming the address and the copy's `digest`; without such a copy, a copy of another source among them, it raises `validate.ConfigError` naming the address. With `store` false it writes no file, and falls back to a copy as above. A table is a snapshot when its `format` is `1` and its `vocabularies` and `substances` have the shapes lab-registry "Snapshot" states; any other content, or a file that is not UTF-8 JSON, raises `validate.ConfigError` naming the file or the address.

#### Scenario: Fetched and kept
- **WHEN** a test serves a snapshot on a local HTTP server and calls `pipeline.registry` on a collection that names its address
- **THEN** it returns the snapshot and the collection's `build/registry.json` holds the same table

#### Scenario: Offline with a copy
- **WHEN** the address of the previous scenario no longer answers and `pipeline.registry` is called again
- **THEN** it returns the copy and warns on stderr naming the address and the copy's digest

#### Scenario: Offline without a copy
- **WHEN** a collection names an address that does not answer and has no `build/registry.json`
- **THEN** `pipeline.registry` raises `validate.ConfigError` naming the address

#### Scenario: A copy of another registry
- **WHEN** a collection's `build/registry.json` was read from one address, and `ORGSYNDB_REGISTRY` then names another address that does not answer
- **THEN** `pipeline.registry` raises `validate.ConfigError` naming the second address and returns nothing of the first

#### Scenario: Not a snapshot
- **WHEN** a collection names a file holding `{"format": 2}`
- **THEN** `pipeline.registry` raises `validate.ConfigError` naming the file

### Requirement: Registry checks
The validator SHALL take the registry from the snapshot file its `--registry` option names (procedure-validation "Command-line interface"): the compound keys are the keys of its substances, and its vocabularies are those procedure fields and reaction types name (procedure-fields "Procedure field declarations", reaction-types "Reaction-type vocabulary"). It checks no substance's values: the lab application checks them.

#### Scenario: Unknown compound
- **WHEN** a registry variant run removes the substance `ethyl-acetate` from the fixture snapshot
- **THEN** it reports one error for each procedure of the run that names `ethyl-acetate`, containing `unknown compound "ethyl-acetate"`

#### Scenario: A substance with the key group
- **WHEN** a registry variant run adds a substance with the key `group` to the fixture snapshot
- **THEN** it reports no problem

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

