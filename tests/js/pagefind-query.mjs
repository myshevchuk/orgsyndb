// Test-only helper: runs searches against a built Pagefind bundle.
//
// Usage: node pagefind-query.mjs <pagefind.mjs> <bundle base URL>
//                                <search-terms.js>
//
// <pagefind.mjs> is a copy of public/pagefind/pagefind.js, renamed so that
// Node loads it as a module. <search-terms.js> is the site's classic script
// that defines globalThis.OrgSynSearch. stdin holds a JSON list of
// {"term", "filters", "normalise"} requests ("term" may be null). stdout
// gets {"results": [[{"id", "title", "excerpt", "meta"}, ...], ...],
// "filters": <the bundle's filters()>}, one result list per request. Any
// error prints to stderr and exits non-zero.

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

async function main() {
  const [pagefindPath, basePath, termsPath] = process.argv.slice(2);
  if (!pagefindPath || !basePath || !termsPath) {
    throw new Error(
      "usage: pagefind-query.mjs <pagefind.mjs> <base URL> <search-terms.js>");
  }
  await import(pathToFileURL(termsPath).href);
  const search = globalThis.OrgSynSearch;
  if (!search || typeof search.normaliseTerm !== "function") {
    throw new Error("search-terms.js did not define OrgSynSearch");
  }
  const pagefind = await import(pathToFileURL(pagefindPath).href);
  await pagefind.options({ basePath });
  const requests = JSON.parse(readFileSync(0, "utf8"));

  const load = async (result) => {
    const d = await result.data();
    return {
      id: d.meta.id,
      title: d.meta.title,
      excerpt: d.excerpt,
      meta: d.meta,
    };
  };

  const results = [];
  for (const request of requests) {
    const term = request.term !== null && request.normalise
      ? search.normaliseTerm(request.term)
      : request.term;
    const options = request.filters ? { filters: request.filters } : {};
    const found = await pagefind.search(term, options);
    results.push(await Promise.all(found.results.map(load)));
  }
  const filters = await pagefind.filters();
  const output = JSON.stringify({ results, filters });
  process.stdout.write(output, () => process.exit(0));
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
