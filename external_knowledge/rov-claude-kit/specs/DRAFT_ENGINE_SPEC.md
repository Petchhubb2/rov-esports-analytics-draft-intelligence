# DRAFT ENGINE SPEC

## Goal

Evaluate the draft state, generate candidates, account for counters and synergies, predict responses, and recommend the next pick/ban with an explanation.

## Draft State

Minimum state:

```text
side: FIRST_PICK | SECOND_PICK
phase: BAN_1 | PICK_1 | BAN_2 | PICK_2
picked_our_heroes[]
picked_enemy_heroes[]
banned_heroes[]
unrevealed_roles[]
current_slots
```

## Draft Workflow

```text
Start Draft
-> Determine Side/Phase
-> Analyze Bans
-> Analyze Current Composition
-> Analyze Enemy Composition
-> Identify Threats
-> Identify Missing Functions
-> Generate Candidate Heroes
-> Apply Direct Counters
-> Apply Composition Counters
-> Apply Synergy
-> Check Flex Value
-> Predict Enemy Response
-> Evaluate Final-State Risk
-> Rank Candidates
-> Recommend Pick/Ban
```

## Evaluation Dimensions

Source-derived dimensions:
- Role & Flexibility
- CC & Engagement
- Peel & Protection
- Damage Type & Pattern
- Wave Clear Speed
- Scaling & Power Spike
- Objective Control
- Teamfight Synergy

Additional implementation dimension from the source logic:
- Counter Fit
- Composition Balance
- Frontline/Backline Balance
- Power Spike Alignment

## Lookahead

Model at least:

```text
Our Candidate
  -> likely Enemy Response
  -> our Response
  -> projected Final Composition
```

Do not pretend to predict the opponent with certainty. Return likely candidates and confidence.

## Candidate Scoring

The source proposes:
- Draft Balance Score
- Counter Pick Score
- Synergy Score
- Power Spike Alignment Score
- Frontline/Backline Ratio Score

Keep all weights configurable.

Conceptual:

```text
DraftScore =
    CounterFit
  + SynergyFit
  + RoleFlexValue
  + PowerSpikeAlignment
  + ObjectiveFit
  + TeamfightFit
  + DraftBalance
  - CounterRisk
  - CompositionConflict
```

## Output Contract

```text
recommendation
score
why
solves_problem[]
synergies[]
counters_avoided[]
expected_enemy_response[]
remaining_risks[]
confidence
sources[]
```

## Important Behavior

A hero must not rank first only because it counters one enemy hero. The engine must evaluate the complete projected composition.
