# Audit Report — Attacking-Phase Relevance Correction

Full technical detail lives in `HANDOFF.md` §6b and
`docs/METRIC_DEFINITIONS.md` §2; this is the standalone audit summary
requested for this round's QA deliverables.

## Bug report

The dashboard could highlight "dangerous space" BEHIND the attacking
team while the real attack was progressing in the opposite direction —
the primary orange highlight sometimes had nothing to do with the team
that actually had the ball.

## 1. Why a behind-the-attack region could win

`dangerous_space_for_team(defending_team, ...)` computed
`attacking_team = 1 - defending_team` **unconditionally** — it never
checked who actually had the ball. The dashboard/graph code called
this for BOTH teams every frame and picked whichever team's conceded
severity was numerically higher as "the" defending team: a pure
severity-comparison heuristic with zero possession awareness.

## 2. Which score components caused it

`progression_value_score(attacking_team, x, ball, pitch)` measured "is
this cell forward of the ball from `attacking_team`'s perspective"
using the REAL ball position but a possibly-FALSE `attacking_team`
hypothesis. When wrong, the real ball's position was misread as
"maximal forward progress" for a team not actually progressing
anything. At only 0.10 weight (blended additively with five other
components), this false signal, combined with the always-on
`goal_proximity` (0.20) and `coverage_gap` (0.35) — which reward any
cell near the hypothesized attacked goal or poorly covered, regardless
of whether that attack is real — was enough to make a structurally
"good-looking" but tactically irrelevant cell win outright.

## 3. Possession/attack-direction wiring — missing entirely

A full-repo grep confirmed `MatchData.roles` (the shared,
already-computed, already-causal `current_roles()` possession output)
was loaded into `data_loader.py` but **never read anywhere** in this
project's actual analytics before this round. Possession was
completely unwired.

## 4. Team A/Team B symmetry

The scoring math itself (`goal_proximity`, `centrality`,
`coverage_gap`, `pitch.own_goal`, `pitch.attacking_sign`) was already
correctly symmetric — confirmed by the pre-existing
`test_symmetry_between_teams` and re-confirmed this round by a
dedicated mirror test
(`test_direction_relevance_mirrored_between_teams`). The bug was the
total ABSENCE of a possession check, which could misfire for either
team depending on the real ball position at that instant — not a
one-sided defect favoring either team.

## The flagship bad frame (1040, t=34.7s), rechecked

- **Attacking team (real, causal possession, 4-second majority)**:
  Team B — ball at x≈8371, deep in Team A's defensive third (Team A's
  own goal is at x=12000).
- **OLD selector**: picked `defending_team=B` (implying Team A was
  attacking) — backwards. The flagged region sat at (2050, 3124), right
  next to **Team B's own goal**, isolated from every player on the
  pitch, severity 0.513 (driven by `progression_value=1.0` under the
  false hypothesis, plus static `goal_proximity`/`centrality`).
- **NEW selector**: correctly picks `defending_team=A`. Flagged region
  at (7946, 6120), 9.3m from the real ball, severity 0.358,
  `attack_phase_active=True`, `direction_relevance≈1.0` (essentially
  level with the ball). Team B's own conceded severity correctly drops
  to 0.022 (`COUNTERATTACK_GATE` — Team A does not have the ball).

See `old_vs_new_t34p7.png`.

## The fix

1. `data_loader.attacking_team_at(frame)` — a tiered causal possession
   estimate (current frame → 4s → 12s → 30s trailing majority →
   honestly "uncertain"), built entirely from the shared
   `current_roles()`'s own real `carrier_team` observations. Never
   fabricates a team.
2. `dangerous_space.direction_relevance(...)` — a new multiplicative
   gate (same role as the existing `area_gate`): neutral when
   possession/ball is unknown; floored to `COUNTERATTACK_GATE=0.05`
   when `defending_team`'s own team has the ball (no current attack
   against them exists — Counterattack Exposure, kept separate);
   otherwise a smooth decay toward `DIRECTION_GATE_MIN=0.15` the
   further behind the real ball (in the real attacking direction) a
   cell sits, never a hard cutoff.
3. `progression_value` REMOVED from the weighted sum; its freed 0.10
   given to `ball_proximity` (0.10→0.15, next-action relevance) and
   `receiver_support` (0.15→0.20). `goal_proximity`/`centrality`/
   `coverage_gap` untouched.
4. `attacking_team_actual` threaded through the entire pipeline:
   `dangerous_space_for_team`, `severity_at_point`,
   `abandonment_penalty`, `rank_candidates`, `search_repositioning`,
   `evaluate_candidate`, `compute_frame_signal`, `render_frame` — held
   FIXED across a single counterfactual search so the before/after
   comparison stays anchored to the same region and possession context
   (verified by a dedicated test, not just assumed).

## Validation

- **Broad sample** (`validation_broad_sample.csv`, 475 frames across
  the full 120s clip): of the 167 rows where both possession and ball
  position are known, 53.3% ahead/level, 41.9% slightly behind (<25m,
  smooth gate, not fully suppressed by design), 4.8% strongly behind
  (inspected individually — deep-byline edge cases, modest severities
  0.15-0.24).
- **7 diagnostic images** (`old_vs_new_t34p7.png`,
  `team_a_attacking_case1/2.png`, `team_b_attacking_case1/2.png`,
  `possession_change_case.png`, `uncertain_possession_case.png`) — top-
  down pitch views with real player/ball positions, the real attacking-
  direction arrow, and both the OLD and NEW flagged regions plotted
  together for direct visual comparison.
- **18 new unit/integration tests**
  (`tests/test_attacking_phase_relevance.py`), all passing, covering
  direction correctness for both teams, team-mirror symmetry, the
  counterattack gate, honest uncertainty handling, no-future-leakage of
  the new possession context, and counterfactual anchoring.
- **Full suite**: 73/73 project tests, 638/638 full-repo regression
  tests, all passing.

## Limitations (disclosed)

- Possession is genuinely unknown ~21% of the time even with this
  project's own extended 30-second fallback; those frames fall back to
  the pre-correction, undirected comparison.
- Real ball position (independent of possession) is unavailable ~46%
  of the time even when possession IS known; the gate stays neutral for
  those frames too.
- The gate constants (`DIRECTION_GATE_MIN`, `COUNTERATTACK_GATE`,
  `DIRECTION_BEHIND_REF_CM`, `LEVEL_WITH_BALL_TOLERANCE_CM`) are
  disclosed modeling choices, not fit to outcome data.
