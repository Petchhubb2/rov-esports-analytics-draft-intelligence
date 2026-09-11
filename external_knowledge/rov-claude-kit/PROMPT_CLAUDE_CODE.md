# Prompt for Claude Code

You are working on a RoV Analysis System.

Before coding, read:

1. `CLAUDE.md`
2. `KNOWLEDGE_BASE.md`
3. `specs/DRAFT_ENGINE_SPEC.md`
4. `specs/COUNTER_ENGINE_SPEC.md`
5. `specs/SYNERGY_ENGINE_SPEC.md`
6. `specs/MACRO_ENGINE_SPEC.md`
7. `specs/HERO_DATA_SPEC.md`
8. the relevant `knowledge/*.md` file for the feature you are implementing

## Source Discipline

The knowledge files are extracted from NotebookLM sources. Do not invent missing RoV facts. Preserve FACT / OBSERVATION / INFERENCE / OPINION / UNKNOWN. If a source rule conflicts with another source rule, flag the conflict instead of silently resolving it.

## Task

First inspect the repository and propose the smallest implementation for the requested module.

Then:

1. Identify which source knowledge the feature depends on.
2. Identify the data structures required.
3. Identify missing/UNKNOWN data.
4. Propose the algorithm before coding.
5. Implement the smallest testable version.
6. Add tests using the source-derived examples.
7. Return a concise explanation of what changed and what remains uncertain.

## First Milestone

Start with the Hero/Data layer and relationship models. Do not begin with AI/ML. The first version should be deterministic, explainable and configuration-driven.

## Do Not

- hard-code all hero logic into one giant function
- hide scoring weights in source code
- convert UNKNOWN into guessed values
- claim a counter is universal when the source only supports a specific condition
- remove source context from rules
