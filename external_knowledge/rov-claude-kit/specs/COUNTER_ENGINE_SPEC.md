# COUNTER ENGINE SPEC

## Goal

Given the current enemy draft and our current team state, identify useful counter responses while preserving team structure.

## Counter Layers

### 1. Direct Hero Counter

Input:
- target hero
- candidate hero
- counter type

Output:
- reason
- mechanism
- condition
- risk
- confidence
- sources

Counter types present in the source:
- Hard_Counter
- Displacement_Counter
- Burst_Counter
- Cleanse_Counter
- Poke_Counter
- Lane_Counter
- Flex_Counter

### 2. Role Counter

Examples from source:
- Enemy Assassin → Peel + Disengage/Hard CC + Flicker awareness
- Enemy Tank/CC Heavy Frontline → Tank Melter + Cleanse
- Enemy Poke/Siege → High Mobility Initiator/Dive

### 3. Composition Counter

Model:

```text
Enemy Composition
  -> Threat Tags
  -> Team Problem
  -> Required Response
  -> Candidate Hero Characteristics
  -> Candidate Heroes
  -> Risk Check
```

### 4. Problem-Based Counter

The system should answer:

```text
What problem does our team currently have?
What hero characteristics solve it?
Which candidates fit without breaking our composition?
```

## Rule Evaluation

Each rule should expose:

```text
rule_id
if_conditions
then_action
because_reason
risk
priority
confidence
sources
```

## Candidate Score

The source contains candidate score ideas such as:
- Direct Counter Score +30%
- Composition Synergy Penalty -20%
- Lane Matchup Score +15%

Treat these as **configurable starting values from the source**, not immutable truths. Put them in configuration so they can be tuned using match data.

Proposed conceptual score:

```text
CounterScore =
    DirectCounterFit
  + RoleThreatResponse
  + LaneMatchupFit
  + CompositionFit
  + SynergyFit
  - CompositionBreakPenalty
  - RiskPenalty
```

## Explainability

Every recommendation must return:

```text
Recommended Hero
Why
Counter Mechanism
What Problem It Solves
What It Synergizes With
Main Risk
Confidence
Source(s)
```
