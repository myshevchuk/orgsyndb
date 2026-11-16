## Context

The build reads the registry from the source the collection names, an
address of the lab's snapshot or a snapshot file, keeps the last copy
in `build/registry.json`, and falls back to it when the address does
not answer (compound-registry "Reading the registry"). The deployment's
builder fetches the snapshot from the app over the internal address
`http://app:8000/lab/registry/snapshot.json` and builds when the
registry, the collection's commit or the application's commit differs
from the latest accepted import. Structure images are files under the collection's
`static/structures/`, named by key; the demo has one,
`isopentyl-acetate.svg`, drawn by hand to the rules of site-theme
"Structure images are safe SVG", and one scheme image,
`aryl-ketone-reduction.svg`. Site tests build copies of the test
collection, which mirrors the demo and names its own `registry.json`;
their helpers copy fixture images into `static/structures/`.

## Goals / Non-Goals

**Goals:** the lab keeps each substance's structure as a molfile and
serves its drawing from a cache; the build takes the images from the
registry's source; a build without the lab keeps the last images.

**Non-Goals:** a structure editor (Ketcher) in the lab; computing
SMILES, formula, molar mass or InChI from the molfile; redrawing every
cached image when the drawing code changes; PNG structure images;
procedure scheme images, which stay in the collection.

## Decisions

**A molfile, with the drawing cached on the row.** The molfile is what
an editor and a toolkit work with; an image is not. The SVG is drawn
when the substance is saved with a molfile and kept in a column the
forms and the admin do not show and the change history leaves out,
since it follows from the molfile. Rejected: keeping uploaded images
(nothing can edit or compute from them); drawing on each request (the
owner wants a cache); files on a media volume (the deployment has
none, and the database backup already covers the row). A later change
that alters the drawing redraws the cache in its migration.

**RDKit, reading the file as drawn.** RDKit has wheels for Python
3.14 and draws SVG without a display server. The lab reads a molfile
without strict valence checks, so that a drawing with an unusual
valence still shows, keeps its coordinates, and computes coordinates
only when every atom sits at the origin. It draws in black on a white
background, as the theme's structure figures are. A file is refused
when RDKit cannot read a molecule with at least one atom from it, when
it is larger than 1 MB, or when it is not UTF-8 text. Line endings are
made LF, so a file saved on Windows round-trips through the snapshot
unchanged.

**Atom labels come from the file.** An alias or label in a molfile is
drawn as text. The lab's answer forbids every script and outside
resource, and a test draws a molfile whose alias is markup and checks
that the SVG holds no element from it.

**The snapshot carries the molfile.** `registry_load` loads the demo's
structures from it, and a structure change changes the digest, which
makes the builder build. A molfile is about a kilobyte, so a registry
of a thousand drawn substances adds about a megabyte to each fetch of
the internal address. Rejected: a digest of the image in the snapshot
(`registry_load` could then not load structures).

**The build fetches the images (owner's choice).** For an address, a
substance's image is `substances/<key>/structure.svg` resolved against
the snapshot's address, which on the lab is its image address. For a
snapshot file, it is the file at that relative path beside it: the
same layout, kept by whoever keeps the file, which lets site tests and
lab-less builds of a file have images. Rejected: images inside the
snapshot (the owner chose an address); pages pointing at the lab's
address (each page view would ask the lab, and builds from a file
would show none); drawing in the build (RDKit in the builder, and a
second drawing of each structure).

**The deployment fetches beside its pinned snapshot.** The update
cycle builds from `<data>/registry.json`, the snapshot it fetched and
records the digest of, so the build reads a file, not the address.
Before the cycle's first build it fetches the images of that snapshot
beside the file, with the `Host` it sends for the snapshot, and the
build takes them by the file rule. A missing image stops the cycle's
builds, as a missing snapshot does: published with an image missing,
the site would keep the gap until the registry next changed, since an
unchanged digest builds nothing. The build's own fetching serves a
collection that names the lab's address, as in development.

**Staged images are kept.** `build/substances/<key>/structure.svg`
holds the image each build staged and survives the next; a substance
whose image cannot be had keeps its earlier copy. The first request
that gets no answer ends the requests of that build, so a lab that is
down costs one timeout, not one per substance. One warning names how
many images were not staged and the first one's address and reason.
All of this concerns a registry named by an address; from a snapshot
file the build copies the images there are.
The staged images are published at `substances/<key>/structure.svg`,
the lab's layout, not under `structures/`, which the collection's
static files own.

**The demo's structures (owner's choice).** Every demo substance with
a SMILES gets a molfile generated from it with RDKit's 2D layout, which
the lab draws; RDKit reads each back as the registry's formula. The
hand-drawn image of `isopentyl-acetate` moves to
`webapp/demo/substances/isopentyl-acetate/structure.svg` and keeps the
safe-SVG rules, so builds from the demo's registry file, and the test
collection's copy of it, still show it; it differs in look from the
lab's drawing. Beside a snapshot file, a missing image means none, not
a failure: the file's keeper chooses which images to provide, and
builds of the demo's file would otherwise warn about nineteen images
on every run. Rejected: committing RDKit's drawings there (it pins
RDKit's output and breaks the hand-drawn rules); no images for builds
from a file (the integration tests' image would go).

**Emacs reads the staged copy.** The structure window shows
`build/substances/<key>/structure.svg`, so it needs no network code
and works while the lab is down, once a build has run.

## Risks / Trade-offs

- RDKit's wheel in the Fedora-based app image is unproven: building
  the image and drawing a structure in it is a task.
- A cached image drawn by an older RDKit stays until the substance is
  saved again.
- The lab's drawing and a snapshot file's beside-file image can
  differ; only builds from a file the lab did not fill use the latter.
- Hugo gives an earlier mount the precedence for a path two mounts
  publish, so a collection's own `static/substances/<key>/structure.svg`
  would hide the staged image.
- An image drawn after the cycle fetched the snapshot can belong to a
  newer molfile than the snapshot holds; the newer molfile changes the
  digest, and the next cycle builds again.
