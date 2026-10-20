// Query normalisation for Pagefind, as a classic script (no import or
// export) that defines globalThis.OrgSynSearch. The search page loads it
// before search.js; the search tests load it under Node.
//
// normaliseTerm(term): splits term on whitespace, removes from each word
//   every character that is not a Unicode letter or number, drops empty
//   words, and joins the rest with single spaces. A SMILES substring then
//   becomes a prefix of one of the page's indexed SMILES suffixes, and
//   "50-78-2" matches the CAS number as Pagefind indexed it.
// cleanResult(result): deletes meta.smiles_index from a Pagefind result,
//   so the UI does not list the index, and returns the result.
(function () {
  "use strict";

  const squash = (word) => word.replace(/[^\p{L}\p{N}]/gu, "");

  globalThis.OrgSynSearch = {
    normaliseTerm(term) {
      return String(term).split(/\s+/).map(squash).filter(Boolean).join(" ");
    },
    cleanResult(result) {
      if (result && result.meta) delete result.meta.smiles_index;
      return result;
    },
  };
})();
