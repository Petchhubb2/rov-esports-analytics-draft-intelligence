# Permanent Decisions

## Knowledge vs Outcome

Mechanistic knowledge and historical outcome answer different questions.

When they disagree:

- retain both
- record DataCheck
- do not silently overwrite either

## Evaluation

Data after 2026-09-06 is reserved as clean evaluation.

## Root cause

Never label a root cause VERIFIED from static code reading alone.
Reproduce or trace it first.

## Association vs Mechanism (synergy)

Observed co-occurrence (how often two heroes are picked together, and their pair win
rate) is NOT mechanistic synergy. Co-occurrence is measured; mechanism is sourced
knowledge. Keep them in separate types. A pair's raw win rate can reverse sign after
subtracting expected_synergy(), so never treat co-occurrence as synergy directly.

## Unresolved entity identity

If two hero names, aliases, spellings, or identifiers may refer to the same entity
but the mapping is not source-verified:

- keep the identity unresolved
- do not silently normalize or merge them
- mark affected knowledge as UNKNOWN / inactive
- exclude affected evidence from scoring and benchmark claims
- preserve the original source spelling
- only activate the mapping after source-backed verification

Example cases may be documented separately, but this rule is not tied to any one hero.

## Series identity vs side (Global Ban-Pick)

Side (BLUE/RED) is ephemeral — it lasts one game. Team identity is stable across a
series. Series history, Global Ban-Pick locks, and series score must be keyed by team
identity, never by side. `GameRecord[]` is the single immutable source of truth; used
heroes and wins are derived from it, not stored separately.

A recorded game is immutable: its blue/red team identities, the association of picks to
those identities, and its winner_team_id must never change after recording. The
"swap sides" action may modify only the current/next game's side assignment — it must
never rewrite a historical GameRecord. Renaming a team's display name must not move
history, locks, or wins.
