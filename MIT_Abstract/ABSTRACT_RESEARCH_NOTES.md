# Abstract Research Notes — Dangerous Space Repositioning

Internal companion to `SLOAN_DANGEROUS_SPACE_REPOSITIONING_ABSTRACT.md`.
Not for submission — this is our own working reference for defending
the abstract, extending it into a full paper, and answering reviewer
questions.

## Research question

Formal: *Can dangerous opponent-controlled space be identified from
player tracking such that it reflects the CURRENT attacking phase (not
just static geometric exposure), and can a bounded counterfactual
search over player positions recommend which defender or midfielder
should reposition to close it, while explicitly checking whether that
move opens a new structural gap elsewhere?*

Coaching-language version: *Which player should move, and where,
to close dangerous space without opening another gap?*

## The actual contribution (be precise about this in any Q&A)

Voronoi tessellation itself is NOT the contribution — it is a 40-year-old
computational-geometry tool already standard in pitch-control/space
literature. The two things this project actually adds, in order of
importance:

1. **A hard, rule-based "is this cell part of the CURRENT attack"
   eligibility gate**, applied BEFORE ranking (not a soft penalty baked
   into the score). Most public dangerous-space/pitch-control work
   flags the geometrically most-exposed region regardless of whether
   the team in possession could plausibly reach it this phase of play.
   This project's gate structurally guarantees 0% of primary selections
   are "strongly behind" the live attack — verified, not assumed (see
   Results).
2. **A bounded, single-player counterfactual search that scores a
   candidate move against an explicit new-gap-risk term**, not just
   "does this player get closer to the danger." The "without creating a
   new gap" half of the coaching question is answered by a real,
   re-derived team-shape metric (compactness/isolation/coverage
   variance) evaluated on the full hypothetical roster after the move,
   not asserted.

A secondary, disclosed contribution: extending the single "most
dangerous region" answer to up to THREE ranked, mutually-DISTINCT
regions per team (with spatial de-duplication so near-identical
Voronoi cells don't count as separate problems) and resolving the case
where the same real player is the natural fixer for two of them.

## Exact pipeline (method flow, as actually implemented)

```
tracking (player + ball, per frame)
  -> possession/attacking-team estimate (causal, tiered majority vote:
     current frame, then 4s / 12s / 30s trailing windows)
  -> Voronoi tessellation (per frame, all players)
  -> dangerous-space severity per opponent-owned cell
     (weighted, area-gated -- see "Metric definitions" below)
  -> Current-Attack Eligibility gate (HARD filter, applied before
     ranking -- see below)
  -> Top-3 distinct-region selection (severity-ranked, spatially
     de-duplicated)
  -> opponent accessibility per region (reused pitch-control /
     time-to-intercept sigmoid model)
  -> candidate defender/midfielder scoring per region (proximity,
     feasibility, abandonment cost, local support)
  -> multi-region fixer conflict resolution (a player can't fix two
     regions at once -- fall back to next-best real candidate)
  -> bounded (<=3m) counterfactual repositioning search per assigned
     fixer (benefit = danger removed - new-gap risk - structural
     damage - movement cost)
  -> coach-facing recommendation (region, fixer, target, benefit,
     new-gap risk)
```

Source modules (for our own reference, NOT to appear in the abstract):
`analytics/voronoi_control.py`, `analytics/dangerous_space.py`,
`analytics/multi_region.py`, `analytics/opponent_access.py`,
`analytics/player_responsibility.py`,
`analytics/counterfactual_repositioning.py`,
`analytics/spatial_balance.py`, `analytics/data_loader.py`
(`attacking_team_at`).

## Metric definitions (exact, current, source-verified)

**IMPORTANT**: `HANDOFF.md`'s own top-level "§6. Equations" section is
STALE — it documents the ROUND-1 severity formula
(`severity = area_gate x direction_relevance x weighted_sum`), which
was REPLACED in round 2 (the "Current-Attack Eligibility Gate," §6c).
The CURRENT formula (verified directly against
`analytics/dangerous_space.py::score_cell`, lines ~358-396, this
session) has NO `direction_relevance` term at all -- eligibility is now
a completely separate, hard, ranking-time filter, not a multiplier
baked into severity. **Always verify against source, not just the
first matching HANDOFF section**, since this document accumulated many
rounds and older sections were sometimes left in place after being
superseded.

**Dangerous Space Severity** (current, verified):
```
raw = 0.20*goal_proximity + 0.10*centrality + 0.15*ball_proximity
    + 0.20*receiver_support + 0.35*coverage_gap
severity = raw * area_gate(area_cm2)
```
All 5 components individually bounded to [0,1]; weights sum to 1.0;
`area_gate` in [0.15, 1.0]. Therefore `severity` is ALWAYS in [0,1] by
construction (relevant if we ever add a results figure with a y-axis).

**Current-Attack Eligibility** (`classify_region`, hard gate, applied
BEFORE ranking):
1. Possession/ball/direction unknown -> `UNCERTAIN`, ineligible (never
   falls back to an undirected guess).
2. Defending team's own team has the ball -> `COUNTERATTACK_EXPOSURE`,
   ineligible (there is no current attack against them).
3. `progress_cm = (x - ball_x) * attacking_sign(attacking_team)`;
   `progress_cm < -500cm` (5m behind the ball) -> `SUPPORT_SPACE`,
   ineligible.
4. Within the 5m tolerance band, ALSO must be reachable: ball distance
   <= 3000cm (30m) OR `receiver_support_score >= 0.15` -> else
   `SUPPORT_SPACE`, ineligible.
5. Otherwise -> `CURRENT_DANGEROUS_SPACE`, eligible.

**Top-3 de-duplication** (`select_top_regions`): walk severity-ranked
eligible candidates; suppress a candidate if
`centroid_distance < 1.5 * (r_candidate + r_kept)` where
`r = sqrt(area_cm2/pi)` (the same radius already used to draw the
region); keep up to 3.

**Opponent accessibility** (reused pitch-control model, NOT invented
here): `access(point) = sigmoid((T_defend - T_attack) / 0.5s)`, where
`T_team(point)` is the fastest real responder's time-to-reach
(`effective_position = position + velocity * 0.3s`, `/ 800cm/s` max
speed).

**Candidate fixer score**:
`score = 0.35*proximity + 0.20*feasibility - 0.30*abandonment_penalty + 0.15*local_support`.

**Counterfactual benefit**:
`benefit = 3.0*danger_removed - 1.5*new_gap_penalty - 1.5*structural_damage_penalty - 0.01*movement_cost_penalty`.
Bounded candidates only: 7x7 grid of +/-100/200/300cm offsets, unioned
with 100/200/300cm direct steps toward the region; any candidate
outside the real pitch rectangle is REJECTED, never clamped.

**Spatial Balance / New-Gap Risk**:
`risk = 0.40*compactness_risk + 0.35*isolation_risk + 0.25*coverage_variance_risk`.

## Verified quantitative results (every number traced in CLAIM_EVIDENCE_TRACEABILITY.md)

- 475-frame broad sample (every 5th frame, >=4 tracked players):
  ahead/level 53.3% -> 64.4%; slightly-behind-within-tolerance 41.9% ->
  35.6%; strongly-behind 4.8% -> **0.0%** (structural guarantee under
  the hard gate).
- Uncertainty breakdown (same 475-frame sample): resolved 104 (21.9%);
  possession/ball unknown 308 (64.8%); known context, no eligible
  candidate 63 (13.3%).
- 601-frame demo segment (frames 440-1040, the project's own
  20-second demo clip), 203 valid sampled frames (every 2nd frame,
  >=4 tracked players): 48 resolve a primary region. Of these: 1
  region 4 (8.3%), 2 regions 23 (47.9%), 3 regions 21 (43.75%).
  De-duplication suppressed >=1 raw candidate in 47/48 (97.9%).
- Same-player fixer conflicts: 4/48 resolved frames (8.3%) in the same
  demo segment; ALL resolved via fallback to the next-best real
  candidate (the "no independent fixer" honest-failure path was only
  ever exercised in synthetic unit tests, never in real match data).
- Worked positive-benefit example (frame 2233, t=74.43s, Team A/track
  55, defending team = Team A, attacking team = Team B): candidate
  moves 300cm (3.0m) from (10022.7, 2391.3) to (10193.7, 2144.8);
  `danger_removed=+0.00775`, `new_gap_penalty=0.0`, `benefit=+0.01326`.
  Flagged-region severity at that instant: 0.3444 (real, ungated),
  region radius ~1209.4cm (~12.1m), region center (10951.1, 1053.0).
  **This replaces the previously-cited frame-3300 example** (Team B/
  track 82, benefit +0.00544, sourced from `HANDOFF.md` §7): a fresh
  re-computation this round against the current, unmodified pipeline
  (`multi_region.select_top_regions`, `player_responsibility.
  assign_regions_and_fixers`, and the legacy single-region
  `dangerous_space_for_team` -> `rank_candidates` -> `search_repositioning`
  path that the dashboard itself calls) found frame 3300 is NOT
  reproducible: it now resolves a different region (track 143's, not
  track 82's), a different fixer (track 13, not 82), and a NEGATIVE
  benefit (-0.056). `HANDOFF.md` §7's own citation of a
  `direction_relevance=0.674` field in its "corrected" frame-3300
  table is the tell — that field does not exist in the current
  `dangerous_space.py::score_cell`, so §7's own "re-verified" example
  was itself computed under a stale/intermediate code state, the same
  class of error `HANDOFF.md` had already flagged for the earlier
  frame-1040 example it replaced. An exhaustive read-only scan of all
  3,600 frames x 2 teams against current source found only 3 genuinely
  reproducible positive-benefit cases in the whole match; frame 2233
  is the strongest (largest benefit, most legible region scale) and is
  used throughout the abstract and its figures.
- Test suite: 129 project tests (`dangerous_space_repositioning/
  tests/`), 638 repository regression tests, all passing as of the
  final round (`HANDOFF.md` §19d). No-future-leakage is directly
  tested (corrupting every frame after `f` never changes frame `f`'s
  own computed signal).

## What was explicitly NOT used (and why)

- **The original frame-1040 worked example** (Team B, track 42,
  benefit +0.00509) — `HANDOFF.md` §7 explicitly documents this was
  built on the UNCORRECTED (round-1, soft-gate) selector and flagged
  the wrong region at that exact frame; under the corrected pipeline,
  frame 1040 now honestly reports "no improving local candidate
  found."
- **`HANDOFF.md` §7's own "replacement" frame-3300 example** (Team B,
  track 82, benefit +0.00544) — used in an earlier round of this
  abstract, but found THIS round to be itself non-reproducible under
  current source (see the worked-example note above): `HANDOFF.md`'s
  own "corrected" table for this example cites a `direction_relevance`
  field that no longer exists in `dangerous_space.py::score_cell`,
  proving it was computed under a stale/intermediate code state, not
  the final pipeline. Replaced with the freshly re-verified frame-2233
  example above. This is exactly the trap flagged in this task's own
  instructions — always re-audit an example against the FINAL code
  before quoting it — and it recurred even after being caught once,
  because the earlier catch verified the FORMULA against source but
  not this specific worked EXAMPLE's own reproducibility.
- **Display-stability / UI-flicker-reduction metrics** — real,
  measured (see `docs/DISPLAY_STABILITY.md`), but explicitly excluded
  as an abstract Results claim per this task's own framing: engineering
  QA about a coach-facing rendering layer, not a research finding about
  the underlying tactical-analytics method.
- **Any full-dashboard or radar-alignment detail** — real, verified,
  well-documented (`HANDOFF.md` §14), but out of scope for a
  research-contribution abstract; a coordinate-system bug fix in a
  visualization layer is not a scientific result.

## Terminology to avoid (per this task's own explicit list)

Globally optimal repositioning; true/exact possession probability;
scoring probability; referee-grade spatial truth; proven match-outcome
improvement; universal coaching recommendation; validated causal
effect; "revolutionary"; "game-changing"; any claim that implies live
deployment (this is a single-match, offline analysis).

## Terminology safe to use

Geometric Voronoi control; dangerous-space proxy; attack-relevance
gate / Current-Attack Eligibility; opponent-accessibility estimate;
bounded counterfactual search; candidate reposition; new-gap-risk
proxy; "best candidate within the tested local search, not a proven
optimum" (the project's own locked wording discipline, see
`docs/REPOSITIONING_LOGIC.md`); coach-facing decision support.

## Anticipated reviewer questions and best concise answers

**Q: Isn't this just Voronoi/pitch control, which is already well
established?**
A: The tessellation itself is standard; the contribution is (1) a hard,
verified attack-relevance gate applied before ranking, which
structurally eliminates behind-the-play false positives (0% vs. 4.8%
measured), and (2) pairing the "where's the danger" question with a
bounded counterfactual search that explicitly re-scores the DEFENDING
team's own structural risk after a hypothetical move, so "fix this
without breaking that" is a computed answer, not an assumption.

**Q: How do you know the severity/accessibility proxies are actually
correlated with real danger?**
A: We don't claim they are validated against outcome or expert-coach
labels yet — this is explicitly disclosed as a limitation. The
contribution at this stage is a reproducible, rule-based, inspectable
FRAMEWORK (every threshold and weight is a disclosed constant, not
fit to data), not a validated predictive model.

**Q: Why only one match?**
A: Proof-of-concept scope; the framework itself has no per-match
tuning (all thresholds are geometric/kinematic constants, not fit
per-clip), so extending to more matches is an engineering scale-up, not
a methodological change — but we have not yet done it, and say so.

**Q: Why does the bounded search so often find "no improving
candidate"?**
A: Because the flagged region is, almost by definition, the LEAST
covered part of the pitch — the nearest real defender is routinely
20-40m away, genuinely beyond a <=3m local adjustment. We report this
honestly rather than expanding the search radius to manufacture a
positive result, since a large radius would no longer describe a
"reposition" in any realistic sense.

**Q: What happens when two flagged regions need the same player?**
A: The higher-priority (more severe) region keeps the natural best
fixer; the other falls back to the next real candidate in the SAME
already-computed ranking (never a different heuristic, never "nearest
available body"). Measured: 4/48 resolved frames in our demo segment
had this conflict, always resolved with a real fallback.

**Q: Could this run live, during a match?**
A: Not currently claimed or evaluated. Every quantity is computed
causally (no future frames), which is a NECESSARY condition for live
use, but we have not measured runtime/latency at broadcast frame rate,
and this abstract is scoped to offline tactical analysis, not live
deployment.

## Coach/industry value (as framed in the Conclusion)

1. Opposition analysis: "where does this opponent tend to concede
   attack-relevant space, and to which side/channel?"
2. Training-ground rehearsal: replaying a real sequence and showing the
   candidate fix + its own new-gap check as a concrete coaching point.
3. Post-match review: a frame-by-frame, reproducible audit trail of
   "was there a better structural response here" rather than a
   coach's memory of the passage of play.
4. Explicitly NOT framed as: real-time in-match decision support, an
   automatic substitution/instruction system, or a scouting/recruitment
   tool (out of scope for what this project actually measures).
