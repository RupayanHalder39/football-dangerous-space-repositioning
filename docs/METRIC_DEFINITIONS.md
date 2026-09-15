# Metric Definitions — Dangerous Space Repositioning Analytics

All formulas below are the ACTUAL source of truth in code
(`dangerous_space_repositioning/analytics/*.py`); this document explains
them in words and keeps the exact constants in sync deliberately — if
the code changes, update this file in the same change.

## 1. Voronoi Control (`voronoi_control.py`)

Reuses `analytics/voronoi.py::compute_voronoi()` directly: an
ALL-PLAYER Voronoi diagram (both teams' outfield players + goalkeepers,
ball and referees excluded), clipped to the real pitch rectangle. Each
cell is "nearest-player territory" — explicitly NOT a possession
probability, interception probability, or physically-modeled
pitch-control field. `valid=False` (fewer than 4 total players, or
coincident positions) is reported honestly, never papered over.

## 2. Dangerous Space Severity (`dangerous_space.py`)

For a defending team X, every Voronoi cell owned by the OPPONENT
(1 − X) is scored; the highest-scoring cell is reported as "the"
dangerous region against X this frame (plus the full ranked list).

**Attacking-Phase Relevance Correction, round 1** (see `HANDOFF.md`):
removed a weak, possession-blind `progression_value` term that let a
structurally-exposed-but-currently-irrelevant region win the ranking,
replacing it with a `direction_relevance` MULTIPLICATIVE gate.

**Round 2 — Current-Attack Eligibility (HARD gate, current)**: round
1's soft gate (a non-zero floor) still let a strongly-behind-the-ball
region win outright if its other components were large enough —
unacceptable for the PRIMARY "Current Dangerous Space" label. Severity
itself is now computed WITHOUT any direction-based scaling at all;
eligibility is instead a HARD FILTER applied at ranking time (see
`classify_region`/`dangerous_space_for_team`, and §2b "Current-Attack
Eligibility Gate" below):

```
severity = area_gate(cell_area_cm2) × (
      0.20 × goal_proximity
    + 0.10 × centrality
    + 0.15 × ball_proximity
    + 0.20 × receiver_support
    + 0.35 × coverage_gap
)
```

All five weighted components are in `[0, 1]` and sum to 1.0 —
UNCHANGED from round 1 (`goal_proximity`/`centrality`/`coverage_gap`
untouched since round 1's original correction; `progression_value`'s
freed 0.10 already reallocated to `ball_proximity`/`receiver_support`
in round 1, still in effect).

- **`goal_proximity`** = `exp(-distance_to_own_goal_mouth / 4500cm)` —
  1.0 right at the goal mouth, ~0.37 at 45m, decaying smoothly beyond.
- **`centrality`** = `1 - |y - width/2| / (width/2)` — 1.0 on the
  exact centre line, 0.0 on either touchline.
- **`ball_proximity`** = `exp(-distance_to_ball / 3000cm)`, or exactly
  **0.5** (neutral, flagged `had_ball_evidence=False`) when the ball
  isn't currently observed — never a fabricated ball position.
- **`receiver_support`** = smooth effective count of the ATTACKING
  team's own players near the region (soft cap 3), via
  `_soft_count(players, x, y, ref_cm=2000cm)` — see "soft counting"
  below.
- **`coverage_gap`** = `1 - smooth effective count of the DEFENDING
  team's own players near the region` (soft cap 3, `ref_cm=2500cm`).
- **`area_gate(area_cm2)`** = `0.15 + 0.85 × clip(area / 3,000,000cm², 0, 1)`
  — damps (never zeroes) a vanishingly small pocket. This is the ONLY
  role area plays: a final damping gate, never the primary ranking
  signal ("largest cell = dangerous" is explicitly rejected).

## 2b. Current-Attack Eligibility Gate (`classify_region`, round 2)

Applied BEFORE any severity comparison — see
`dangerous_space_for_team`'s own docstring for the exact pipeline
order (score → classify → filter → rank, never rank-then-hide). Every
opponent-owned cell gets a `category` and an `eligible` flag; ONLY
`eligible=True` (`CATEGORY_CURRENT_DANGEROUS_SPACE`) cells are ever
compared for the primary "Current Dangerous Space" selection.

1. **Possession/ball unknown** (`attacking_team_actual is None` or no
   ball evidence) → `CATEGORY_UNCERTAIN`, ineligible. Per this round's
   explicit requirement, this does NOT fall back to an undirected
   ranking (round 1's choice) — showing no primary danger is preferred
   over a possibly-nonsensical one.
2. **`defending_team`'s own team has the ball** (not their opponent) →
   `CATEGORY_COUNTERATTACK_EXPOSURE`, ineligible — there is no current
   attack against them.
3. **Longitudinal progress**: `progress_cm = (x − ball_x) ×
   attacking_sign(attacking_team)`. `progress_cm < −BACKWARD_TOLERANCE_CM`
   → `CATEGORY_SUPPORT_SPACE`, ineligible.
   - **`BACKWARD_TOLERANCE_CM = 500`** (~5m) — the brief's own starting
     suggestion, kept after empirical validation: the real allowed
     slightly-behind cases in this clip (see
     `outputs/qa/current_attack_gate_fix/behind_tolerance_audit.csv`
     and its montage), inspected individually, are genuine
     "support pocket" / cutback-adjacent cells immediately next to the
     ball, not unrelated far-behind exposure. The tolerance covers BOTH
     final-third cutback zones and general midfield support pockets —
     both explicitly named as legitimate small-tolerance cases.
4. **Next-action reachability** (within the longitudinally-eligible
   band): must ALSO be plausibly reachable soon —
   `ball_distance_cm ≤ NEXT_ACTION_BALL_DIST_CM` (**3000cm**, reuses
   `BALL_PROXIMITY_REF_CM`'s own touchstone) **OR**
   `receiver_support_score ≥ NEXT_ACTION_MIN_RECEIVER_SCORE`
   (**0.15**, roughly "a real attacker within ~15-16m"). Failing this
   → `CATEGORY_SUPPORT_SPACE`, ineligible — this is what stops a
   technically-ahead but totally disconnected region (e.g. 40m from
   any real play) from winning.
5. Otherwise → `CATEGORY_CURRENT_DANGEROUS_SPACE`, eligible.

`attacking_team_actual` comes from `data_loader.attacking_team_at` — a
tiered causal majority vote (current frame, then 4s/12s/30s trailing
windows) over real close-control observations; `None` ("uncertain")
only when even a 30-second look-back finds nothing, never fabricated.

**This is a HARD filter, not a soft multiplier** — `severity` itself no
longer depends on eligibility at all (an eligible cell's severity is
the plain weighted-sum-times-area-gate above); eligibility only decides
WHICH cells enter the ranking pool. Ineligible cells are still scored
and categorized (never discarded) for `SUPPORT_SPACE`/
`COUNTERATTACK_EXPOSURE` diagnostics, just never allowed to win the
primary selection.

### Soft counting (why not a hard radius count)

`_soft_count(players, x, y, ref_cm)` sums `exp(-distance/ref_cm)` per
player rather than counting how many fall inside a hard radius. A hard
count is a **step function** of position: a small counterfactual move
(this project's bounded ±1-3m search) very often crosses zero real
thresholds and reports NO change at all even when a player genuinely
moved closer. The smooth version responds continuously to any move,
however small. The real (discrete) count is still reported alongside,
for the dashboard's own "why" readout.

`severity_at_point(...)` re-scores an ARBITRARY point with the
identical formula — used by the counterfactual search to re-evaluate
the SAME flagged region under a hypothetical roster.

## 2c. Top-3 Distinct Dangerous Regions (`multi_region.py`)

Layered ENTIRELY on top of §2b's unchanged eligibility pipeline — no
new severity/eligibility formula. `dangerous_space_for_team(...)
["eligible_ranked"]` (already the same list `top` is picked from) is
walked in severity order and de-duplicated:

```
select_top_regions(eligible_ranked, max_regions=3, overlap_factor=1.5):
  for each candidate (highest severity first):
    r_candidate = sqrt(area_cm2 / pi)      # same radius formula the dashboard already draws
    suppress candidate if, for any ALREADY-KEPT region:
        centroid_distance(candidate, kept) < overlap_factor * (r_candidate + r_kept)
    else keep it (up to max_regions)
```

**Why not simply the top 3 Voronoi cells**: two or three of the
highest-severity eligible cells are frequently neighboring pieces of
the SAME opponent-controlled pocket (e.g. three nearby attackers each
owning a sliver of the same open space) — presenting all three as
independent problems would overstate how many distinct tactical issues
exist. `overlap_factor = 1.5` is a disclosed, generous choice (not a
fitted value): two pockets separated by less than half their combined
radii still read as "the same patch of grass" to a coach, matching the
brief's own explicit warning about neighboring cells.

`select_top_regions(...)[0]` is ALWAYS identical to `top` (nothing can
outrank the first, highest-severity candidate to suppress it) — the
existing single-region primary pipeline is preserved exactly. Never
fabricates a 3rd (or 2nd) region: fewer real distinct candidates yields
a shorter list, down to empty.

### Multi-region fixer assignment and conflict resolution

`assign_regions_and_fixers` walks the surviving regions from primary to
lowest priority, calling the existing, UNCHANGED `rank_candidates` for
each. If a region's own top-ranked real candidate was ALREADY assigned
to a higher-priority region this frame (`conflict=True`), the next-best
unassigned candidate from that SAME already-computed ranked list is
used instead (never a different heuristic, never "pick the nearest").
If every real candidate is already claimed, the region is reported with
`fixer_track_id=None`, `reason="Same-player conflict / no independent
fixer"` — disclosed honestly, never a fabricated second mover for one
player. See `docs/REPOSITIONING_LOGIC.md` for how the assigned fixer's
own counterfactual move (`search_repositioning`) is then computed —
identical to the primary region's own, just anchored to that region.

### Display stability for the extra slots

`dashboard.display_stability.MultiRegionStabilizer` generalizes
`DangerRegionStabilizer`'s own hold/margin hysteresis to N ranked slots,
keyed by the region's owning opponent `track_id` (a natural identity
anchor, since a real cell tracks one real opponent player frame to
frame). See `docs/DISPLAY_STABILITY.md` for the full mechanism. The
PRIMARY region/team decision itself is untouched — this stabilizer only
governs the secondary/tertiary slots layered on top of it.

## 3. Opponent Control / Access of Dangerous Space (`opponent_access.py`)

Reuses `analytics/pitch_control.py`'s own disclosed, already-calibrated
time-to-intercept + logistic model — never a second, independently
invented reachability model:

```
effective_position_i = position_i + velocity_i × REACTION_TIME_SEC (0.3s)
time_to_reach_i(point) = |point - effective_position_i| / PLAYER_MAX_SPEED_CM_S (800 cm/s)
T_team(point) = min_i time_to_reach_i(point)          # fastest real responder
access(point) = sigmoid((T_defend(point) - T_attack(point)) / CONTROL_SIGMA_SEC (0.5s))
```

`opponent_control_of_region(defending_team, region_point, ...)` =
"Threat Against `defending_team`" = the ATTACKING team's access
probability at `defending_team`'s own flagged region — exactly the
quantity Graph 2 plots for each team, and the dashboard's own
"Opponent control NN%" badge.

Velocity is always the REAL causal `vx_cm_s`/`vy_cm_s` from
`data_loader.player_dict` (0.0, `motion_valid=False`, when motion isn't
currently trustworthy — never a fabricated direction).

## 4. Player Responsibility — candidate scoring (`player_responsibility.py`)

For every outfield player (goalkeeper excluded) on the defending team:

```
score = 0.35 × proximity - 0.30 × abandonment_penalty
      + 0.20 × feasibility + 0.15 × local_support
```

- **`proximity`** = `exp(-distance_to_region / 3500cm)`.
- **`feasibility`** = `clip(1 - (distance/3500cm)^2, 0, 1)` — a
  saturating variant of proximity (two "clearly close enough"
  candidates shouldn't be scored near-linearly apart).
- **`abandonment_penalty`** = a DELTA: removes the candidate from the
  defending team entirely, re-scans Dangerous Space, and compares the
  resulting worst opponent-owned-cell severity to the worst cell WITH
  the candidate present. Only an INCREASE counts (`clip(severity_after
  - severity_before, 0, 1)`) — an absolute severity reading would flag
  almost every player as "load-bearing" on this dataset, since baseline
  severity tends to sit well above 0 nearly everywhere on a real pitch.
  Both re-scans receive the SAME `attacking_team_actual` (see §2's
  Attacking-Phase Relevance Correction), so the delta is judged by the
  identical attacking-phase-aware severity used everywhere else.
- **`local_support`** = smooth effective count of teammates within
  1500cm of the candidate's CURRENT position (soft cap 3) — more
  nearby support makes a player cheaper to move.

The top-ranked candidate is the "recommended player," but the full
ranked list (every component) is always available, never just a name.

## 5. Counterfactual Repositioning (`counterfactual_repositioning.py`)

See `docs/REPOSITIONING_LOGIC.md` for the full write-up. Summary:

```
benefit = 3.0 × danger_removed
        - 1.5 × new_gap_penalty
        - 1.5 × structural_damage_penalty
        - 0.01 × movement_cost_penalty
```

## 6. Spatial Balance / New-Gap Risk (`spatial_balance.py`)

One real, geometry-only proxy, computed identically for both teams and
reused (a) as the live time-series (Graph 3) on the REAL observed
roster, and (b) inside the counterfactual search on a hypothetical
roster:

```
risk = 0.40 × compactness_risk + 0.35 × isolation_risk + 0.25 × coverage_variance_risk
```

- **`compactness_risk`** = `clip(mean_distance_to_own_centroid / 2500cm, 0, 1)`.
- **`isolation_risk`** = `clip(worst_nearest_teammate_distance / 2000cm, 0, 1)`
  — the single loneliest player's gap, not just the average spread.
- **`coverage_variance_risk`** = `clip(coefficient_of_variation(own
  Voronoi cell areas) / 1.5, 0, 1)` — very uneven coverage (one player
  covering a huge share of the pitch) reads as a real structural risk.

Fewer than 2 outfield players → each sub-component is honestly `0.0`
(no evidence of a gap, not a fabricated high risk).
