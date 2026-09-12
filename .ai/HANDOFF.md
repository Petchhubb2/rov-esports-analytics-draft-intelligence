# Handoff

## Last agent

Claude Code (Opus 4.8)

## Last commit

`9f00179` — PHASE M2A: add source-backed synergy knowledge representation

## What was completed

M2A — Synergy Knowledge Representation (representation only; no scoring change)

## Tests

- 650 passed
- 11 skipped
- ruff clean
- recommendation ranking unchanged (all new factors at weight 0)

## Files changed

- `packages/core/rov/draft/synergyknowledge.py` (new: SynergyEvidence / SynergyBook / find_matches / explain)
- `knowledge/synergy/hero_pairs.yaml` (new: 8 pairs from synergy.md, each with a DataCheck)
- `tests/unit/test_synergy_knowledge.py` (new: 46 tests)
- `packages/core/rov/draft/recommend.py` (synergy_evidence component, weight 0)
- `packages/core/rov/eval/version.py`, `scripts/run_m15_status.py` (wiring + status output)
- `knowledge/counter/direct_hero.yaml`, `packages/core/rov/draft/counterknowledge.py` (STEP 7: Marja threat)
- `docs/33-synergy-knowledge-audit.md`, `docs/34-synergy-knowledge-spec.md`, `docs/35-synergy-knowledge-report.md`

## Important discoveries / decisions

- association (measured co-occurrence) is kept separate from mechanism (sourced knowledge);
  co-occurrence != synergy (34/214 pairs flip sign after subtracting expected_synergy)
- DataCheck compares against expected_synergy(), not prior 0.5
- Doria/dolia alias unresolved -> SYN-004 status=unknown, never matched or scored
- Marja threat tag ADDED (split_push) sourced to synergy.md Pair 7 (NOT CTR-004);
  lane_trade answer sourced to counter.md CTR-004 -> mechanism matching now reaches Marja

## Unresolved

- Doria vs dolia alias (do not add the alias without evidence)
- Tamyn: high ban pressure, no knowledge
- hero knowledge coverage incomplete (synergy covers 10/119 heroes; counter partial)
- weights cannot be evaluated until new clean games arrive (0 games after 2026-09-06)

## Next action

Read `.ai/NEXT_TASK.md` — Knowledge Coverage Expansion (not scoring)

## Do not do

- Do not tune weights/thresholds using previously inspected windows.
- Do not activate any scoring factor (all extra weights stay 0).
