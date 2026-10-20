// Mounts Pagefind's default UI into [data-search], with the query
// normalisation of search-terms.js, and runs the search named by the
// page's ?q= parameter. Needs pagefind-ui.js and search-terms.js loaded
// first.
(function () {
  "use strict";

  const mount = document.querySelector("[data-search]");
  if (!mount || typeof PagefindUI !== "function") return;

  const ui = new PagefindUI({
    element: "[data-search]",
    showImages: false,
    processTerm: OrgSynSearch.normaliseTerm,
    processResult: OrgSynSearch.cleanResult,
  });

  const query = new URLSearchParams(location.search).get("q");
  if (query) ui.triggerSearch(query);
})();
