// Test-only helper: runs searches against a built Pagefind bundle.
//
// Usage: node pagefind-query.mjs <pagefind.mjs> <bundle base URL>
//                                <search-terms.js> <catalogue-core.js>
//                                [<language>]
//
// <pagefind.mjs> is a copy of public/pagefind/pagefind.js, renamed so that
// Node loads it as a module. <search-terms.js> and <catalogue-core.js> are
// the site's classic scripts that define globalThis.OrgSynSearch and
// globalThis.OrgSynCatalogue. <language> (default en) is the index
// searched, as a page with <html lang="<language>"> would. stdin holds a
// JSON list of {"term", "filters", "normalise", "sort"} requests ("term"
// may be null; "filters" and "sort" are optional Pagefind search options).
// stdout gets
//   {"results": [[{"id", "title", "excerpt", "meta"}, ...], ...],
//    "searched": [null | {"ids": [...]} | {"error": "..."}, ...],
//    "filters": <the bundle's filters()>},
// with one entry of "results" and of "searched" per request. "results"
// holds a plain Pagefind search of the term (normalised when the request
// says so), each hit read with data(). "searched" is null for a null term
// and otherwise holds what OrgSynCatalogue.searcher(pagefind) returns for
// the raw term, one searcher for the whole run, or the error it raised.
// Any other error prints to stderr and exits non-zero.

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

async function main() {
  const [pagefindPath, basePath, termsPath, corePath, language = "en"] =
    process.argv.slice(2);
  if (!pagefindPath || !basePath || !termsPath || !corePath) {
    throw new Error(
      "usage: pagefind-query.mjs <pagefind.mjs> <base URL> "
      + "<search-terms.js> <catalogue-core.js> [<language>]");
  }
  await import(pathToFileURL(termsPath).href);
  const search = globalThis.OrgSynSearch;
  if (!search || typeof search.normaliseTerm !== "function") {
    throw new Error("search-terms.js did not define OrgSynSearch");
  }
  await import(pathToFileURL(corePath).href);
  // Pagefind picks its index from the lang attribute of the page's html.
  // With a document, its WebAssembly glue also reads location.
  globalThis.document = {
    querySelector: (selector) => selector === "html"
      ? { getAttribute: (name) => (name === "lang" ? language : null) }
      : null,
  };
  globalThis.location = new URL(basePath);
  const pagefind = await import(pathToFileURL(pagefindPath).href);
  await pagefind.options({ basePath });
  const requests = JSON.parse(readFileSync(0, "utf8"));

  let searcher = null;
  let searcherError = null;
  try {
    searcher = globalThis.OrgSynCatalogue.searcher(pagefind);
  } catch (error) {
    searcherError = String(error && error.message ? error.message : error);
  }

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
  const searched = [];
  for (const request of requests) {
    const term = request.term !== null && request.normalise
      ? search.normaliseTerm(request.term)
      : request.term;
    const options = {};
    if (request.filters) options.filters = request.filters;
    if (request.sort) options.sort = request.sort;
    const found = await pagefind.search(term, options);
    results.push(await Promise.all(found.results.map(load)));
    if (request.term === null) {
      searched.push(null);
    } else if (searcher === null) {
      searched.push({ error: searcherError });
    } else {
      try {
        searched.push({ ids: await searcher.search(request.term) });
      } catch (error) {
        searched.push({
          error: String(error && error.message ? error.message : error),
        });
      }
    }
  }
  const filters = await pagefind.filters();
  const output = JSON.stringify({ results, searched, filters });
  process.stdout.write(output, () => process.exit(0));
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
