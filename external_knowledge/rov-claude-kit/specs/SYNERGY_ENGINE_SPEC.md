# SYNERGY ENGINE SPEC

## Goal

Measure how well two or more picks work together at hero, role and composition levels.

## Relationship Levels

### Hero-Hero

Core fields:

```text
hero_a
hero_b
synergy_type
reason
gameplay_interaction
condition
expected_result
weakness
confidence
sources
```

The current source contains examples including:
- Rouie + Capheny
- Teemee + Capheny
- Ming + Capheny
- Doria + Tachi
- Krizzix + Liliana
- Krizzix + Zuka/Panda
- Rouie + Marja
- Chaugnar + Hayate

### Role-Role

Support relationships such as:
- Jungle + Mid
- Roam + Mid
- Roam + Jungle
- Exp + Jungle
- Support + Carry

### Composition

Represent patterns such as:

```text
Frontline + Engage + Follow-up Damage + Carry
Poke + Wave Clear + Siege
```

## Synergy Types

Source-derived tags include:
- Global_Warp_Synergy
- Gold_Boost_Synergy
- AoE_Pull_Burst_Synergy
- Double_Ult_Synergy
- Poke_Siege_Synergy
- Front_to_Back_Synergy
- Tag_Farm_Synergy

## Score Model

The source proposes:
- Pair Synergy Score: +0 to +30%
- Role Complement Score: +15%
- Power Spike Alignment Score: +15%

These are configurable source-derived starting values. Do not hard-code them into business logic.

Conceptual score:

```text
SynergyScore =
    PairSynergy
  + RoleComplement
  + PowerSpikeAlignment
  + MacroCompatibility
  - CounterRisk
```

## Rule Examples

```text
IF Picked(Rouie)
THEN Recommend(Capheny OR Marja OR Tachi)

IF Picked(Teemee)
THEN Recommend(Capheny)

IF Picked(Doria)
THEN Recommend(Tachi OR Errol)

IF Picked(Krizzix)
THEN Recommend(Liliana OR Zuka OR Panda)

IF Picked(Chaugnar)
THEN Recommend(Hayate)
```

Keep these as data-driven relationships rather than scattered conditionals where practical.
