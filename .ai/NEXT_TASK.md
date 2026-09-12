# Next Task

Phase: **Knowledge Coverage Expansion**

## Goal

Improve knowledge representation and data quality only. No scoring, no weight changes,
no clean-window consumption.

## Priority

1. Verify the Doria <-> dolia alias using authoritative / source-backed evidence.
   If confirmed: add it to `HERO_ALIASES`, flip SYN-004 to `dolia`, drop `unresolved`.
2. Improve Tamyn knowledge coverage (high ban pressure, currently no knowledge).
3. Improve high-presence hero knowledge coverage.
4. Improve threat / capability / answer coverage using sourced knowledge only.

## Rules

- representation / data quality only
- no weight tuning
- no scoring activation (all extra weights stay 0)
- no clean-window consumption (do not measure/tune on post-2026-09-06 games)
- no invented RoV facts; UNKNOWN is valid; keep provenance

**Do NOT start M2B scoring** — the clean evaluation window has 0 games.

## Expected deliverables

- updated knowledge YAML (counter / synergy) with sourced additions
- a coverage report update
- tests for any new source-derived rules
