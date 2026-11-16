## 1. The lab keeps and draws structures

- [x] 1.1 Tests: lab-registry "Structure images" (the demo's image and
  its headers, drawn at each save and not on request, not in the
  history (web-app "Change history"), markup in an atom alias, coordinates computed for a molfile
  at the origin), the molfile in "Substances" and "Snapshot", the
  structure on the substance page, and the form scenarios of "Registry
  forms" (file, CR LF, not a molfile, larger than 1 MB, not UTF-8,
  removed, a file and the box together), in German and English
- [x] 1.2 RDKit as a dependency of `webapp/` (`pyproject.toml`,
  `uv.lock`)
- [x] 1.3 The substance's `molfile` and its kept drawing, the
  migration, the drawing with RDKit, the image's address and answer
- [x] 1.4 The form's file field and box, the substance page's figure,
  the snapshot's `molfile`, `registry_load`; translations
- [x] 1.5 The demo registry: a molfile from its SMILES for every
  substance with one, `molfile` `null` for `new-compound-7`, the
  digest; the test collection's `registry.json` to match

## 2. The build stages the images

- [x] 2.1 Tests: compound-registry "Structure images" (from the lab,
  beside a snapshot file with and without an image, the lab down, a
  lab that stops answering, a structure removed); site-build's eight
  mounts and staged data; site-theme's image paths and safe SVG;
  sample-procedures' structure image and test collection;
  build-script's ignore rules; `molfile` as a substance text of a
  snapshot
- [x] 2.2 Move `examples/demo/static/structures/isopentyl-acetate.svg`
  to `webapp/demo/substances/isopentyl-acetate/structure.svg`, and the
  test collection's copy to `tests/fixtures/collection/substances/`
- [x] 2.3 `tools/validate.py`: `molfile` a string or null
- [x] 2.4 `tools/pipeline.py`: staging into `build/substances/`, the
  warning, `compound_data`'s `structure_image`, the eighth mount
- [x] 2.5 Test helpers that copy fixture images give their registry a
  molfile and place the image beside it; `keep_registry_inside` copies
  the images beside the demo registry along with it

## 2a. Deployment

- [x] 2a.1 Tests: container-deployment "Update cycle" (the images
  beside the kept snapshot with the snapshot's `Host`, an image that
  cannot be fetched stops the builds)
- [x] 2a.2 `deploy/docker/orgsyndb-deploy`: fetch the images before
  the cycle's first build

## 3. Emacs

- [x] 3.1 ERT test of "Structure window" with the staged image
- [x] 3.2 The structure window reads `build/substances/<key>/structure.svg`

## 4. Verification

- [x] 4.1 Build the app image with podman and draw a structure in it
- [x] 4.2 In a browser: the lab's substance page of
  `isopentyl-acetate`, its edit form with a molfile and the removal;
  a site built against the running lab shows the image on
  OSDB-0003's page
- [ ] 4.3 Run the stack on the test server

## 5. Docs, review and archive

- [x] 5.1 README, `docs/SCHEMA*.md`, `docs/AUTHORING*.md`,
  `docs/AUTHORING-ORG*.org`: structure images come from the lab
- [x] 5.2 Codex reviewer
- [x] 5.3 Archive; bring compound-registry's Purpose in line;
  squash-merge into `develop`
