## MODIFIED Requirements

### Requirement: serve subcommand
`tools/orgsyndb serve [--port N]` SHALL run `build`, bind `127.0.0.1:<N>`, print the line `serving http://127.0.0.1:<N>/ (Ctrl-C to stop)` once the port is bound, and then serve the collection's `public/` with the standard library's HTTP server until interrupted. Every response carries `Cache-Control: no-cache`, so a browser revalidates each file and shows a new build instead of cached pages of an earlier one. The default port is 8000; a port outside 1–65535 or not a number is a usage error. It never binds an address other than `127.0.0.1`.

#### Scenario: Site and search bundle are served
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> serve --port <free port>` in its own process group and waits for the `serving` line
- **THEN** HTTP GET requests to `/`, `/procedures/osdb-0001/`, `/pagefind/pagefind.js` and `/pagefind/pagefind-entry.json` on `127.0.0.1:<free port>` return status 200 with the header `Cache-Control: no-cache`
- **AND** the test then terminates the process group

#### Scenario: Port out of range
- **WHEN** a test runs `tools/orgsyndb -C <collection> serve --port 70000`
- **THEN** it exits 2, and the collection's `build/` was not created

### Requirement: Caddyfile example
The file `deploy/Caddyfile.example` SHALL serve a copy of `public/` as static files with `file_server`, and sets the response header `Cache-Control: no-cache` with a `header` directive, explained in a comment. It uses a placeholder site address and a placeholder `root` path, explained in comments, and references no external resource and no user- or machine-specific identifier.

#### Scenario: Example is generic
- **WHEN** a test reads `deploy/Caddyfile.example`
- **THEN** it contains `file_server`, a `root` directive and the line `header Cache-Control "no-cache"`, and contains neither `/home/` nor a host name ending in `.local`, `.lan` or `.home.arpa`

#### Scenario: Example parses when Caddy is installed
- **WHEN** a test runs `caddy adapt --adapter caddyfile --config deploy/Caddyfile.example`, skipping when `caddy` is absent
- **THEN** it exits 0
