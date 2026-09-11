# MACRO ENGINE SPEC

## Goal

Turn current game state + draft context into explainable macro recommendations.

## Core Concepts

Source-derived concepts:
- Map Control & Vision
- Resource & Gold Efficiency
- Vision Triangle
- Objective Trading
- Power Spike Alignment
- Wave/Lane/Rotation
- Role interaction

## Time Triggers

The source identifies triggers around:
- 2:00 objective event
- 4:00 tower-shield expiration
- 8:00 objective upgrade/event
- 15:00 God Slayer event

Treat exact timings as source-derived values and keep them configurable by game version.

## State Model

Minimum state suggestions:

```text
GAME_LEAD
GAME_BEHIND
VISION_AVAILABLE
POWER_SPIKE_REACHED
OBJECTIVE_CONTESTABLE
LANE_PRIORITY
ENEMY_POSITION_KNOWN
```

## Events

Source examples:

```text
FIRST_BLOOD_GANK
RED_BUFF_INVADED
OBJECTIVE_SPAWN
TOWER_SHIELD_EXPIRE
```

## Rules

Source examples:

```text
IF Enemy_Offlane_Has_No_Escape_Spell
AND Roam_Has_CC
THEN Gank_Top_At_00_20

IF Creep_At_Tower
AND Jungle_Camp_Alive
THEN Clear_Tower_Creep_First

IF Objective_Is_Lost
THEN Evaluate_Trade_Objective
```

## Recommendation Structure

Every macro recommendation should contain:

```text
recommendation_id
phase/time_window
trigger
conditions
action
reason
roles_involved
expected_outcome
risk
confidence
sources
```

## Draft Integration

Macro should consume draft-derived attributes such as:
- early/late power
- engage/disengage
- peel
- objective strength
- wave clear
- mobility
- win condition

This means Draft Engine should expose a compact `composition_profile` to Macro Engine.
