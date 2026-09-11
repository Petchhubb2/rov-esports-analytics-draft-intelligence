# IMPLEMENTATION PLAN

## Phase 0 — Knowledge Validation

1. Keep original NotebookLM files unchanged.
2. Normalize terminology without changing meaning.
3. Identify duplicate relationships.
4. Mark contradictions and UNKNOWN data.
5. Create source IDs.

## Phase 1 — Data Layer

Deliverables:
- Hero model
- Tag model
- Counter relationship model
- Synergy relationship model
- Macro rule model
- Draft state model

## Phase 2 — Deterministic Engines

Build in this order:

1. Counter Engine
2. Synergy Engine
3. Draft Engine
4. Macro Engine

Reason: Draft depends on reliable Counter/Synergy relationships, while Macro benefits from a completed composition profile.

## Phase 3 — Explainability

Every recommendation must expose its contributing rules/factors and sources.

## Phase 4 — Tests

Create unit tests for source-derived examples:
- Rouie counter candidates
- Omen/Marja -> Mina
- Heavy CC -> Chaugnar
- Marja vs Murad flex response
- Rouie -> Capheny/Marja/Tachi synergy
- Doria -> Tachi/Errol synergy
- Krizzix -> Liliana/Zuka/Panda synergy
- macro rules around gank, lane creep priority, objective trade

## Phase 5 — Real-World Tuning

Only after deterministic behavior works, tune score weights using real match/draft data.

## Phase 6 — Video/Macro Integration

Later connect:
Video -> Hero Detection -> Player/Position Tracking -> Game State -> Macro Evaluation -> Coaching Output

Do not let vision uncertainty directly overwrite the draft knowledge layer.
