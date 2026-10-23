// Progressive enhancement for the all-procedures lists. The table is
// complete without it.
//
// - Reveals the [data-list-filters] block and its two selects.
// - Hides each table row whose data-reaction-types or data-status does not
//   match the selected values; an empty value matches every row.
// - Reports the visible rows in the [data-list-count] element, from its
//   data-filtered template with {shown} and {total}, and restores the
//   original text when no filter is set.
//
// OrgSynListFilter.rowMatches is a pure function so that Node can test it.
(() => {
  "use strict";

  const rowMatches = (row, filters) => {
    const types = (row.reactionTypes || "").split(" ").filter(Boolean);
    if (filters.reactionType && !types.includes(filters.reactionType)) {
      return false;
    }
    if (filters.status && row.status !== filters.status) return false;
    return true;
  };

  globalThis.OrgSynListFilter = { rowMatches };

  if (typeof document === "undefined") return;
  const block = document.querySelector("[data-list-filters]");
  const table = document.querySelector("table.procedure-list");
  if (!block || !table) return;

  const type = block.querySelector('[data-filter="reaction-type"]');
  const status = block.querySelector('[data-filter="status"]');
  const count = document.querySelector("[data-list-count]");
  const original = count ? count.textContent : "";
  const rows = Array.from(table.tBodies[0].rows);

  const apply = () => {
    const filters = { reactionType: type.value, status: status.value };
    let shown = 0;
    for (const row of rows) {
      const match = rowMatches(row.dataset, filters);
      row.hidden = !match;
      if (match) shown += 1;
    }
    if (!count) return;
    count.textContent = filters.reactionType || filters.status
      ? count.dataset.filtered
          .replace("{shown}", String(shown))
          .replace("{total}", String(rows.length))
      : original;
  };

  type.addEventListener("change", apply);
  status.addEventListener("change", apply);
  block.hidden = false;
  // A browser may restore select values on back navigation.
  apply();
})();
