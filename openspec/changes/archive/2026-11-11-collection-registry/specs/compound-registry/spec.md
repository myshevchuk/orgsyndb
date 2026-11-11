## ADDED Requirements

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
The validator SHALL take the registry from the snapshot file its `--registry` option names (procedure-validation "Command-line interface"): the compound keys are the keys of its substances, and its vocabularies are those procedure fields and reaction types name (procedure-fields "Procedure field declarations", reaction-types "Reaction-type vocabulary"). It checks no substance's values: the lab application checks them. A substance whose key is `group`, the directory of the compound tabs (site-catalogue "Compound tabs"), is an error on the snapshot file, under the field `substances`, containing `group`.

#### Scenario: Unknown compound
- **WHEN** a registry variant run removes the substance `ethyl-acetate` from the fixture snapshot
- **THEN** it reports one error for each procedure of the run that names `ethyl-acetate`, containing `unknown compound "ethyl-acetate"`

#### Scenario: A substance named like the tabs directory
- **WHEN** a registry variant run adds a substance with the key `group` to the fixture snapshot
- **THEN** it reports exactly one error, on the snapshot's path, field `substances`, containing `group`

### Requirement: Structure images by key
A substance's structure image SHALL be the file `static/structures/<key>.svg` of the collection, or `static/structures/<key>.png` when there is no SVG, `<key>` being the substance's key. A substance without either file has no structure image. No file names it otherwise, and no check reports a substance without an image. The data the build stages for a substance with an image sets `structure_image` to `structures/<key>.svg` or `structures/<key>.png` (site-build "Hugo configuration"); that is what the site's requirements mean by a compound that sets `structure_image`.

#### Scenario: Image found by key
- **WHEN** the demo collection is built and its static files hold `structures/isopentyl-acetate.svg`
- **THEN** the page of `isopentyl-acetate` shows that image, and the page of a substance without a file of its key shows none

## REMOVED Requirements

### Requirement: Compound files
**Reason**: Substances are created and edited in the lab application; a collection holds no compound files.
**Migration**: `manage.py registry_import COLLECTION` moves a collection's compound and vocabulary files into the lab application's registry; the collection then names the registry as Registry source states.

### Requirement: Compound fields
**Reason**: The lab application checks a substance's values when it is created or edited (lab-registry "Substances").
**Migration**: None; a value the application refuses cannot reach the snapshot.

### Requirement: Structure image path
**Reason**: A structure image is found by the substance's key (Structure images by key); no file names a path.
**Migration**: Name each image `static/structures/<key>.svg` or `.png`.

### Requirement: Compound template
**Reason**: There are no compound files to start from a template.
**Migration**: Create substances in the lab application's registry forms.
