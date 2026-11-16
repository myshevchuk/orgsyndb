# synthesis-routes Specification

## Purpose
Draw, in the lab, the ways to make each substance from the collection's procedures the lab keeps, guarded against cycles and bounded in depth and size, as a tree on the substance's page.
## Requirements
### Requirement: Routes in the lab
The lab application SHALL draw a substance's route tree from the collection's procedures it keeps (collection-import "Imported rows"), with the depth limit 6 and the step budget 200; `collection.routes.route_tree` draws it for any depth limit and budget by the rules below.

A step to a substance is a specific procedure that is not withdrawn whose entry is not withdrawn and has the substance among its products, or such an entry of a general procedure that is not withdrawn, numbered by its position. The step starts from the entry's substrates, in their order, and from none when it has none; its yield is the product's. The steps to a substance are ordered by procedure ID, the entries of one general procedure by position.

A tree of a substance R is built downward from R. Every substance of the tree lies on a path, the substances from R down to it, both included, and has a level, the number of steps between it and R; R has level 0. The steps a substance of the tree keeps are the steps to it, less every step that starts from a substance on its path, so that a cycle such as a protection followed by its removal is never followed. In the tree of R to the depth `d`, a substance whose level is below `d` is expanded: under it lie the steps it keeps, and under each step the substances that step starts from, each built by the same rules. A substance whose level is `d` is not expanded; it is cut off when it keeps a step, and a plain leaf when it keeps none. The size of a tree is the number of steps in it, at every level.

The route tree of R is its tree to the largest depth from 1 to the depth limit whose size is at most the budget, or its tree to the depth 1 when even that one is larger. R has a route tree exactly when it goes past one step: when some step R keeps starts from a substance that is expanded with at least one step, or is cut off. `route_tree` returns the route tree as a list with one table per step R keeps, in order, and an empty list when R has none. A step's table has the keys `procedure`, the procedure's ID; `entry`, only for an entry of a general procedure, its number; `yield_percent`, the yield of the substance the step makes; and `substrates`, one table per substance the step starts from, in order, with the keys `compound`, the substance's key; `steps`, the list of the steps it keeps, built as R's are, when it is expanded, and an empty list otherwise; and `more`, `true` when it is cut off and `false` otherwise. No table has another key.

#### Scenario: Routes of the demo data
- **WHEN** the demo data set is written and a test draws the route tree of every substance in the lab
- **THEN** exactly `acetylsalicylic-acid`, `1-biphenyl-4-yl-ethanol` and `cinnamic-acid` have one
- **AND** the tree of `acetylsalicylic-acid` is the one step `OSDB-0002` with the yield 75, starting from `salicylic-acid`, expanded with the one step `OSDB-0001` at 80 that starts from `methyl-salicylate`, a plain leaf, and from `acetic-anhydride`, a plain leaf
- **AND** the tree of `1-biphenyl-4-yl-ethanol` holds `OSDB-0005` at 90 and entry 1 of `OSDB-0009` at 90, in that order, each starting from `4-acetylbiphenyl`, expanded with `OSDB-0004` at 85

#### Scenario: A protection and its removal in the lab
- **WHEN** the lab keeps three specific procedures, `OSDB-0001` making `b` from `a`, `OSDB-0002` making `a` from `b` and `OSDB-0003` making `c` from `b`, and a test draws the route trees of `a`, `b` and `c`
- **THEN** only `c` has one: `OSDB-0003` starting from `b`, expanded with the one step `OSDB-0001`, which starts from `a`, a plain leaf

#### Scenario: Withdrawn procedures leave the tree
- **WHEN** the demo data set is written, `OSDB-0007` is withdrawn, and a test draws the route tree of `cinnamic-acid`
- **THEN** it has none

#### Scenario: The budget in the lab
- **WHEN** the lab keeps a general procedure `OSDB-0001` of seven entries, entry `n` making `chain-<n>` from `chain-<n-1>`, and a test draws the route tree of `chain-7`
- **THEN** it nests six steps, for the entries 7 down to 2, and `chain-1` under the innermost is cut off with no steps

#### Scenario: The depth limit in the lab
- **WHEN** the lab keeps four specific procedures, `OSDB-000<n>` making `c<n>` from `c<n-1>` for `n` from 1 to 4, and a test draws the route trees with the depth limit 2, and again with the depth limit 1
- **THEN** with the depth limit 2, `c2`, `c3` and `c4` have one; that of `c4` is `OSDB-0004` starting from `c3`, expanded with `OSDB-0003`, which starts from `c2`, cut off with no steps; and that of `c2` is `OSDB-0002` starting from `c1`, expanded with `OSDB-0001`, which starts from `c0`, a plain leaf
- **AND** with the depth limit 1, `c2`, `c3` and `c4` have one, each its one step, which starts from a substance cut off with no steps

