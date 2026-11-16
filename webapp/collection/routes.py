"""Route trees of substances, drawn from the collection's procedures the
lab keeps (synthesis-routes "Routes in the lab")."""

from dataclasses import dataclass
from typing import Any

from collection.models import EntrySubstance, Role

# The depth limit and the step budget of a route tree.
DEPTH = 6
BUDGET = 200


@dataclass(frozen=True)
class Step:
    """A step to a substance: a procedure, or one entry of a general
    procedure, that makes it at YIELD_PERCENT from SUBSTRATES, keys in
    order; ENTRY is the entry's number, or None for a specific
    procedure."""
    procedure: str
    entry: int | None
    yield_percent: float | None
    substrates: tuple[str, ...]


class _OverBudget(Exception):
    """A route tree being built has more steps than its budget."""


def steps() -> dict[str, list[Step]]:
    """Return the steps to each substance, by key: one per entry that
    is not withdrawn, of a procedure that is not withdrawn, with the
    substance among its products. The steps to a substance come by
    procedure ID, the entries of one procedure by position, which
    numbers an entry of a general procedure."""
    rows = EntrySubstance.objects.filter(
        entry__withdrawn=False, entry__procedure__withdrawn=False,
    ).select_related("entry__procedure", "substance").order_by(
        "entry__procedure__key", "entry__position", "position")
    entries: dict[Any, dict[str, Any]] = {}
    for row in rows:
        entry = entries.setdefault(row.entry_id, {
            "procedure": row.entry.procedure,
            "position": row.entry.position,
            "substrates": [], "products": []})
        if row.role == Role.SUBSTRATE:
            entry["substrates"].append(row.substance.key)
        else:
            entry["products"].append((row.substance.key, row.yield_percent))
    found: dict[str, list[Step]] = {}
    for entry in entries.values():
        procedure = entry["procedure"]
        for key, made in entry["products"]:
            found.setdefault(key, []).append(Step(
                procedure.key,
                entry["position"] if procedure.general else None,
                made, tuple(entry["substrates"])))
    return found


def route_tree(root: str, made: dict[str, list[Step]],
               depth: int = DEPTH,
               budget: int = BUDGET) -> list[dict[str, Any]]:
    """Return ROOT's route tree from the steps MADE gives each
    substance, drawn to at most DEPTH steps within BUDGET steps by the
    rules of synthesis-routes "Routes in the lab", or an empty list when
    the tree does not go past one step.

    A substance keeps every step to it except those that start from a
    substance on its path, from ROOT down to it. The tree is the one to
    the largest depth from 1 to DEPTH that holds at most BUDGET steps,
    or the one to the depth 1. It is a list of the steps ROOT keeps,
    each a table of ``procedure``; ``entry``, only for an entry of a
    general procedure; ``yield_percent``; and ``substrates``, a table
    per substance it starts from of ``compound``, its key, ``steps``,
    its own steps when it is expanded, and ``more``, true exactly when
    it is cut off.
    """

    def kept(key: str, path: frozenset[str]) -> list[Step]:
        return [found for found in made.get(key, [])
                if path.isdisjoint(found.substrates)]

    def tree(limit: int, cap: int | None
             ) -> tuple[list[dict[str, Any]], bool]:
        # ROOT's tree to the depth LIMIT, and whether it cuts a
        # substance off; raises _OverBudget past CAP steps.
        size, cut = 0, False

        def grow(key: str, path: frozenset[str],
                 level: int) -> list[dict[str, Any]]:
            nonlocal size, cut
            drawn = []
            for found in kept(key, path):
                size += 1
                if cap is not None and size > cap:
                    raise _OverBudget
                substrates = []
                for substrate in found.substrates:
                    under = path | {substrate}
                    item: dict[str, Any] = {
                        "compound": substrate, "steps": [], "more": False}
                    if level + 1 < limit:
                        item["steps"] = grow(substrate, under, level + 1)
                    elif kept(substrate, under):
                        item["more"] = cut = True
                    substrates.append(item)
                each: dict[str, Any] = {"procedure": found.procedure}
                if found.entry is not None:
                    each["entry"] = found.entry
                drawn.append(each | {"yield_percent": found.yield_percent,
                                     "substrates": substrates})
            return drawn

        return grow(root, frozenset({root}), 0), cut

    # Deepen one level at a time and stop as soon as a tree passes the
    # budget; a tree that cuts nothing off is the same at every greater
    # depth.
    drawn, cut = tree(1, None)
    for limit in range(2, depth + 1):
        if not cut:
            break
        try:
            drawn, cut = tree(limit, budget)
        except _OverBudget:
            break
    past = any(substrate["steps"] or substrate["more"]
               for each in drawn for substrate in each["substrates"])
    return drawn if past else []
