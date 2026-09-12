# Current State

Current phase: **M2A complete**

Latest implementation commit: `9f00179`

## Verification

- 650 passed
- 11 skipped
- ruff clean
- recommendation ranking unchanged

## Completed

- M0.5 Benchmark Foundation
- M0.75 Ban Intelligence Repair
- M1 CounterKnowledge
- M1.5 Clean Evaluation + Coverage Audit
- M2A Synergy Knowledge Representation

## Current restrictions

- clean evaluation window after 2026-09-06 currently has 0 games
- counter_evidence weight = 0
- synergy_adj weight = 0
- synergy_evidence weight = 0
- composition weight = 0
- trait_counter weight = 0
- do not retune BAN_META_SHARE on inspected windows
- do not change raw synergy scoring until a clean evaluation window exists

## Known unresolved

- Doria vs dolia alias not verified
- Tamyn knowledge coverage missing
- hero knowledge coverage incomplete
- clean evaluation data not available yet

## Next planned work

Knowledge Coverage Expansion (see `.ai/NEXT_TASK.md`) — **not** M2B scoring
