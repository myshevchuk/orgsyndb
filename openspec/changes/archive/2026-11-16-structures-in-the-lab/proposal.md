## Why

A substance's structure image is a file the collection keeps by key,
`static/structures/<key>.svg` or `.png` (compound-registry "Structure
images by key"), drawn by hand or exported from a drawing program, and
the lab knows nothing of it. The registry lives in the lab, and the
lab's substance page now shows everything the site's compound page
shows but the image; the site's compound pages are to retire next.
The owner wants the structure kept in the lab's database as a molfile,
the form a structure editor such as Ketcher reads and writes and a
chemistry toolkit computes from, with the drawn image cached so that a
request never redraws it. The build takes the images from the lab, as
it takes the registry.

## What Changes

- A substance keeps an optional molfile. The lab draws its structure
  image with RDKit when the substance is saved with a molfile, keeps
  the SVG, and serves it at
  `/lab/registry/substances/<key>/structure.svg`; the substance page
  shows it.
- The substance forms take a molfile file and, on the edit form, a box
  that removes the structure; a file RDKit cannot read is refused.
- The snapshot carries each substance's `molfile`, so `registry_load`
  loads structures and a structure change changes the digest.
- The build stages the image of every substance with a molfile from
  the registry's source: for an address, the image's address beside
  the snapshot's; for a snapshot file, the file
  `substances/<key>/structure.svg` beside it. It publishes them at
  `substances/<key>/structure.svg` and keeps them between builds, so
  an unreachable lab leaves the last images in place.
- The deployment's update cycle, which pins the snapshot in a file,
  fetches the images beside that file before it builds, and builds
  nothing when an image cannot be fetched.
- **BREAKING**: the collection's `static/structures/<key>.svg` and
  `.png` are no longer structure images; PNG structure images end.
  `static/structures/` keeps scheme images.
- Every demo substance with a SMILES gets a molfile generated from
  it, so the lab demo shows structures throughout. The demo's one drawn
  image, of `isopentyl-acetate`, moves from the demo collection's
  static files to `webapp/demo/substances/isopentyl-acetate/structure.svg`,
  beside the registry file, for builds from that file; a substance with
  no image beside the file has none there. The test collection mirrors
  it.
- The Emacs structure window shows the image the last build staged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lab-registry`: "Substances", "Registry pages", "Registry forms" and
  "Snapshot" add the molfile and the image; new "Structure images".
- `compound-registry`: "Structure images by key" gives way to
  "Structure images", staged from the registry's source.
- `site-build`: "Hugo configuration" mounts the staged images and sets
  `structure_image` from them.
- `site-theme`: "Theme sources and constraints", "Structure image
  slot", "Structure images are safe SVG" and "Compound pages" name the
  staged images.
- `collection`: "Collection layout" keeps scheme images, not structure
  images, in `static/structures/`.
- `sample-procedures`: "Theme sample set" and "Demo collection" move
  the demo's image beside its registry.
- `build-script`: "Ignore rules" names a file the demo still tracks
  under `static/structures/`.
- `emacs-mode`: "Structure window" shows the staged image.
- `container-deployment`: "Update cycle" fetches the images beside the
  kept snapshot.
- `web-app`: "Change history" leaves a cached drawing out of the
  copy.

## Impact

- `webapp/registry/` (model fields and migration, rendering, forms,
  views, templates, snapshot), translations, `webapp/pyproject.toml`
  and `uv.lock` (RDKit), the app image.
- `webapp/demo/registry.json` and `webapp/demo/substances/`,
  `examples/demo/static/structures/`, `tests/fixtures/collection/`.
- `tools/pipeline.py` (staging, `compound_data`, the overlay's mounts),
  `tools/validate.py` (`molfile` as a substance text).
- `emacs/` (the structure window).
- `deploy/docker/orgsyndb-deploy` (the images beside the kept
  snapshot).
- README, `docs/SCHEMA*.md`, `docs/AUTHORING*.md` and
  `docs/AUTHORING-ORG*.org`, which tell authors to put structure images
  under `static/structures/`.
- Deployment: the builder fetches the images from the app over the
  address it fetches the snapshot from; the app image must be rebuilt
  before the builder's next build shows images.
