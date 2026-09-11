# HERO DATA SPEC

> Implementation proposal based on the source structure in `knowledge/hero.md`. This file is not an additional game-data source.

## Canonical Hero Entity

Each hero record should support:

```text
id
name
aliases
role[]
secondary_roles[]
class[]
damage_type
range
strengths[]
weaknesses[]
tags[]
power_spike.early
power_spike.mid
power_spike.late
team_fight
objective_strength
wave_clear
mobility
cc
engage
peel
burst
scaling
required_conditions[]
win_condition[]
counters[]
countered_by[]
synergies[]
macro_requirements[]
confidence
sources[]
```

## Normalized Tag Groups

Use groups so a tag has predictable meaning:

- `role`: Jungle, Mid_Mage, Carry, Roam_Tank, Roam_Support, Offlane_Fighter, etc.
- `damage_pattern`: Burst_Damage, Continuous_DPS, Poke_Damage, True_Damage
- `utility`: Hard_CC, Soft_CC, CC_Immunity, Displacement_Hook, Recall_Teleport, Heal_Shield
- `timing`: Early_Game_PowerSpike, Mid_Game_PowerSpike, Late_Game_Scaling
- `wave_clear`: Fast_Clear, Slow_Clear
- `draft`: Flex_Pick, Hard_Counter, Meta_Priority
- `threat`: Recall_Warp_Threat, Heavy_CC_Threat, Tank_Frontline_Threat, Immobile_Backline_Threat, Poke_Siege_Threat
- `synergy`: Global_Warp_Synergy, Gold_Boost_Synergy, AoE_Pull_Burst_Synergy, Double_Ult_Synergy, Poke_Siege_Synergy, Front_to_Back_Synergy, Tag_Farm_Synergy

Only add a new tag when supported by the knowledge source or when explicitly marked as an implementation proposal.

## Missing Data

`UNKNOWN` is a valid value. Do not replace UNKNOWN with guesses.
