# RoV Analysis System — Claude Code Instructions

## Project Purpose

Build a RoV analysis system in separate modules:
- Draft Engine
- Counter Engine
- Synergy Engine
- Macro Engine
- Hero Knowledge/Data Layer
- later: Video Analysis / Tracking / Coaching Layer

## Knowledge Sources

The project knowledge comes from the five source files in `knowledge/` and the original NotebookLM exports in `originals/`.

Read the relevant knowledge/spec files before implementing a feature.

## Source Discipline

1. Do not invent RoV facts.
2. Preserve the source labels: FACT, OBSERVATION, INFERENCE, OPINION, UNKNOWN.
3. Do not silently resolve conflicting source claims.
4. Separate source-derived game knowledge from implementation proposals.
5. When a fact is missing, use UNKNOWN or require data collection.
6. Keep source names/references attached to important rules.

## Architecture Rules

- Keep Hero data separate from Draft/Counter/Synergy/Macro logic.
- Prefer data-driven rules over hard-coded hero-name logic when practical.
- Keep the first implementation deterministic and explainable.
- Do not introduce machine learning when a rule/data approach is sufficient.
- Keep scoring weights configurable.
- Every recommendation should be explainable: what triggered it, what rule/factor contributed, and what risk remains.

## Implementation Order

1. Knowledge/Data model
2. Hero data loader
3. Tag and relationship layer
4. Counter Engine
5. Synergy Engine
6. Draft Engine
7. Macro Recommendation Engine
8. Evaluation/testing
9. Video analysis integration

## Important Source-Derived Constraints

- Draft should account for First Pick/Second Pick, flex picks, bans, revealed roles, counter picks and final composition balance.
- Counter must support direct hero, role, composition and problem-based counters.
- Synergy must support hero-pair, role and composition relationships.
- Macro must support rules, time triggers, game states, role interactions, objective decisions and recommendations.

## Coding Behavior

Before implementing a major module:
1. Read its specification.
2. Summarize the data flow.
3. Identify missing data/UNKNOWN fields.
4. Implement the smallest testable version.
5. Add tests for source-derived rules.

Do not change game rules merely to make the code cleaner. If a source rule appears questionable, keep it as source-derived and flag it for review.
