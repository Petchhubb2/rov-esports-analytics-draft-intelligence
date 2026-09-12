# RoV Esports Analytics & Draft Intelligence — Agent Instructions

Instructions for any AI agent working in this repo (Claude Code, Codex, etc.).
`CLAUDE.md` and `AGENTS.md` are kept identical on purpose — read either one, and if you
edit one, mirror the change to the other. This file is an index; project knowledge lives
in `docs/` and `.ai/`, not here.

## Start here (read before changing code)

1. `docs/00-project-structure.md`
2. `docs/09-build-log.md` — measured results and disproved hypotheses; highest doc precedence
3. `.ai/CURRENT_STATE.md` — current phase, commit, and active restrictions
4. `.ai/HANDOFF.md` — what the last agent did
5. `.ai/NEXT_TASK.md` — what to do next
6. `.ai/DECISIONS.md` — permanent decisions
7. the latest phase docs (`docs/3x-*`)

## Source of truth (when things conflict, higher wins)

1. executed tests / measured behavior
2. current implementation
3. `docs/09-build-log.md`
4. latest phase report
5. older design docs
6. external knowledge (`external_knowledge/rov-claude-kit/knowledge/*`)
7. agent inference

## Engineering rules

- Do not invent RoV facts. UNKNOWN is a valid state.
- Preserve source labels: FACT / OBSERVATION / INFERENCE / OPINION / UNKNOWN.
- Every knowledge rule needs provenance — keep the source attached, per field
  (do not let one source cover a field it does not mention).
- Do not silently resolve conflicting source claims.
- KNOWLEDGE != OUTCOME. Historical match outcome must not overwrite mechanistic
  knowledge, and a claim is not empirically validated merely because it has a source.
  When they disagree: keep both, record a DataCheck, reduce confidence, do not resolve silently.
- Do not tune weights or thresholds on an evaluation window that has already been inspected.
- Keep scoring weights configurable and every recommendation explainable (what triggered
  it, which factor contributed, what risk remains).
- Prefer data-driven rules over hard-coded hero-name logic; do not add ML where a
  rule/data approach suffices; keep hero data separate from engine logic.
- Trace or reproduce before claiming a root cause; never mark one VERIFIED from static reading alone.
- Add regression tests for changed behavior. Run `ruff` and `pytest` before finishing.
- Do not silently modify unrelated shared utilities, or redesign working architecture without evidence.

## State / task / handoff

- Current state: `.ai/CURRENT_STATE.md`
- Next task: `.ai/NEXT_TASK.md`
- Handoff: `.ai/HANDOFF.md`
- Permanent decisions: `.ai/DECISIONS.md`
