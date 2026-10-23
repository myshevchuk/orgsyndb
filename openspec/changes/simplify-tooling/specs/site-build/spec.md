## MODIFIED Requirements

### Requirement: Pagefind binary acquisition
`build` SHALL index with the Pagefind 1.5.2 standalone binary at `<app>/.tools/pagefind-1.5.2/pagefind`, obtained through `pipeline.ensure_pagefind(<app>/.tools)`, which returns the binary's path and works as follows:
- It accepts a cached binary only when its SHA-256 is `c4b86009ce5420dc2a1748ab2705bef6ba730ed883f684fd52ef6008bd600532`.
- Otherwise it downloads `https://github.com/Pagefind/pagefind/releases/download/v1.5.2/pagefind-v1.5.2-x86_64-unknown-linux-musl.tar.gz` into an empty download directory and requires the tarball's SHA-256 to be `afb824a9e7f64905a934900481cea5be679c03975e527329e0e5e6cc70f5feda`.
- From the tarball it extracts only the regular-file member `pagefind`. It requires that file's SHA-256 to be the binary hash above, makes it executable, and moves it into place.
- Any mismatch or download error removes everything that run wrote and raises `PagefindError`, so that `build` exits 1, with a message giving the URL or the expected and actual hashes.

No Node, npm or pip is used.

`pipeline.install_pagefind(tarball, tar_sha256, bin_sha256, dest)` performs the verification and extraction, and raises `PagefindError` on a mismatch.

#### Scenario: Valid tarball installs the binary
- **WHEN** a test builds a local tarball whose only member is a regular file `pagefind`, and calls `install_pagefind` with that tarball's hash and that member's hash
- **THEN** `dest` holds an executable `pagefind` whose bytes equal the member's

#### Scenario: Wrong tarball hash
- **WHEN** a test calls `install_pagefind` on the same tarball with a different `tar_sha256`
- **THEN** it raises `PagefindError`, whose message contains both the expected and the actual hash, and `dest` holds no `pagefind`

#### Scenario: Wrong binary hash
- **WHEN** a test calls `install_pagefind` with the correct `tar_sha256` and a different `bin_sha256`
- **THEN** it raises `PagefindError`, and `dest` holds no `pagefind`

#### Scenario: Unsafe member is refused
- **WHEN** a test calls `install_pagefind` on a tarball whose `pagefind` member is a symbolic link, giving the tarball's correct hash
- **THEN** it raises `PagefindError`, and nothing is written outside `dest`

