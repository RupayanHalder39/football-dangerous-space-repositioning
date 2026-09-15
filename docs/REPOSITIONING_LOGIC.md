# Repositioning Logic — The Bounded Counterfactual Search

## Wording rule (never violated)

Results are described as **"the best candidate within the tested local
search"** or **"a candidate improved structure,"** NEVER "the optimal
position." This is a bounded local grid over ONE player at a time, not
an exhaustive multi-player optimization — global optimality is never
claimed or implied. This mirrors the exact same wording discipline
`pressing_structure.analytics.counterfactual_pressing` already
established for its own single-defender search.

## Candidate generation

For the recommended (or any given) player, two families of candidate
TARGET positions are tested, both bounded to `MAX_CANDIDATE_RADIUS_CM
= 300`:

- **A. Local grid**: every `(dx, dy)` combination of
  `{-300,-200,-100,0,100,200,300}` cm on each axis — identical
  convention to `counterfactual_pressing.DEFAULT_OFFSETS_CM`.
- **B. Direct steps**: 100/200/300cm straight-line steps from the
  player's current position TOWARD the flagged danger region — the
  single most football-realistic "close the gap" direction, and one
  this project's own brief explicitly invited ("other bounded candidate
  directions if justified"). Never overshoots past the region itself.

Any candidate whose resulting `(x, y)` would fall outside the real
pitch rectangle is **REJECTED outright** — never clamped/teleported
back onto the pitch (a clamp would silently understate how far the
move actually is). A candidate whose movement exceeds the bounded
radius (a defensive check; the two generators above should never
produce one) is rejected the same way.

## The four terms, and why they're scaled the way they are

```
benefit = 3.0 × danger_removed
        - 1.5 × new_gap_penalty
        - 1.5 × structural_damage_penalty
        - 0.01 × movement_cost_penalty
```

### `danger_removed`

`severity_before − severity_after`, BOTH evaluated with the identical
scoring formula (`dangerous_space.severity_at_point`) **at the same
flagged region** — i.e. "did this specific pocket of space actually
get safer," not "did the pitch-wide worst cell change." A single-
defender ≤3m move can rarely move the GLOBAL worst cell if a bigger,
unrelated problem exists elsewhere on the pitch; anchoring the
before/after comparison to the flagged region itself is what makes the
comparison meaningful, and is a disclosed, deliberate scope limit of a
one-player search (not something papered over by silently re-anchoring
to whatever the new worst cell happens to be after the move).

**Attacking-Phase Relevance Correction** (see `HANDOFF.md` §6b/§6c):
`search_repositioning` only ever anchors to a `danger_region` that came
from an ALREADY-ELIGIBLE `top` (§2b of `docs/METRIC_DEFINITIONS.md`'s
Current-Attack Eligibility gate) — an ineligible (e.g. strongly-
behind-the-ball, or counterattack-only) region is structurally never
handed to the counterfactual search at all, so it can never be
"optimized" into looking like a recommendation
(`tests/test_attacking_phase_relevance.py::
test_counterfactual_repositioning_never_invoked_for_an_ineligible_region`
proves this directly).

As of round 2 (the hard eligibility gate), `severity_at_point`'s
returned value no longer depends on `attacking_team_actual` at all —
eligibility is a ranking-time FILTER (decides which region becomes
`danger_region` in the first place), not a severity multiplier baked
into the scoring formula. This is SIMPLER than round 1's soft gate
(which did scale `severity`, and therefore `danger_removed`, by a
possession-dependent constant): `severity_before`/`severity_after` are
now both plain, real, unscaled scores at the same fixed
`(danger_region, area)`, for the same real reasons every other
before/after comparison in this project already relies on (same
region, same real formula, only the roster differs).

**Why weighted 3.0×**: `danger_removed` is the PRIMARY objective, but
by construction it is always a SMALL number. Only the `coverage_gap`
(0.35 weight) and `receiver_support` (0.15 weight, unaffected by a
defensive move) components of Dangerous Space Severity respond to
player position at all, and even `coverage_gap`'s response to a ≤3m
move is a modest shift along a smooth exponential-decay curve.
Empirically (see below), realistic `danger_removed` values across this
clip's real data sit in the **0.001-0.01** range. Amplifying it 3×
keeps a genuine improvement visible in the final `benefit` sign without
distorting its relative meaning.

### `new_gap_penalty`

`max(0, spatial_balance_risk_after − spatial_balance_risk_before)` for
the defending team's OWN structure (`spatial_balance.py`) — only an
INCREASE in the team's own exposure is penalized; a move that happens
to also improve team shape is never penalized for that.

### `structural_damage_penalty`

The moved player's own `abandonment_penalty` (see
`player_responsibility.py`), evaluated ONCE against their REAL,
ORIGINAL position — not the candidate destination, since "how much did
leaving your current spot cost" does not depend on where you went.
Identical across every candidate for the same player; computed once
per search, not once per candidate, for both correctness and speed.

### `movement_cost_penalty`

`distance_moved_cm / 300` — a full-radius move costs exactly 1.0,
half-radius costs 0.5. **Why weighted only 0.01**: even the smallest
tested step (100cm) already carries a raw penalty of 0.333, which at
any weight above ~0.05 would swamp every realistic `danger_removed`
value. This term exists only to gently prefer a smaller move between
two otherwise-similar candidates — never to veto a genuine improvement
over moving at all.

## Calibration history (disclosed, not hidden)

The weights above are the result of one deliberate calibration pass
against this project's own real data, not a first guess left
unchecked:

1. An initial `COVERAGE_RADIUS_CM=1200` (a tight "marking distance")
   combined with a HARD radius count made `coverage_gap_score` a step
   function — a real bounded ≤3m move essentially never crossed the
   threshold, so `danger_removed` was almost always exactly **0.0**.
   Fixed by switching to the smooth soft-count (see
   `docs/METRIC_DEFINITIONS.md`).
2. Even after that fix, `COVERAGE_RADIUS_CM=1200` was measured to be
   far tighter than this clip's own REAL spacing (median real
   nearest-candidate-to-region distance ≈ 22-38m, vs. a median real
   nearest-TEAMMATE distance of only ≈8m) — recalibrated to 2500cm,
   closer to the real scale at which a defender's presence plausibly
   matters for a large, open pocket of space.
3. `structural_damage_penalty`'s FIRST version used an absolute
   severity reading after removing a player ("is the resulting worst
   cell severe AND close to them"), which stayed high (~0.15-0.45) for
   almost every real candidate regardless of whether they individually
   mattered — because baseline severity on this dataset sits well
   above 0 nearly everywhere. Switched to a DELTA (`severity_after -
   severity_before`, only counting increases), matching the same
   "only penalize a genuine worsening" convention already used by
   `new_gap_penalty`.
4. `movement_cost_penalty`'s weight was reduced in three steps (0.5 →
   0.3 → 0.03 → 0.01) after direct measurement showed even its SMALLEST
   possible value (100cm move) numerically dominated every realistic
   `danger_removed` value at any higher weight, making the search
   structurally incapable of ever recommending a move regardless of
   how much danger it actually removed.

After this calibration, a real, honest positive-benefit example DOES
exist in this clip — see `docs/../HANDOFF.md`'s worked example
(episode at frame 1040, ≈34.7s, Team B, track 42: a 300cm move with
`danger_removed=+0.00503`, `new_gap_penalty=0`,
`structural_damage_penalty=0`, `benefit=+0.00509`,
interpretation: *"candidate improved structure — best candidate within
the tested local search, not a proven optimum."*).

**This remains the common case, not the exception**: across ~340
sampled (frame, team) combinations scanned during calibration, the
large majority correctly report **"no improving local candidate found
— the observed position already scores best within the searched
grid."** This is an honest structural finding, not a search failure:
the flagged "most dangerous" region is, almost by definition, a region
that is currently poorly covered — which on a full-size pitch usually
means the nearest real defender is 20m+ away, genuinely beyond what a
single bounded ≤3m adjustment can fix. Closing such a gap for real
would require a bigger tactical instruction (a full team-shape shift,
or sprint distances beyond this project's own realism bound), which
this project deliberately does not claim to search.

## New-Gap Risk in detail

This is the part of the brief marked CRITICAL — "without creating a
new gap." After every simulated move, the defending team's ENTIRE
structure (not just the moved player) is re-inspected via
`spatial_balance.compute_spatial_balance_risk` on the full hypothetical
roster. An elevated `new_gap_penalty` reflects a REAL, re-derived
increase in:

- compactness (the team spreading out more than before),
- isolation (some OTHER player now being the loneliest, farther from
  any teammate than before),
- or coverage variance (the team's own Voronoi coverage becoming more
  lopsided).

The "05_high_new_gap_risk_case" preview deliberately visualizes a real,
fully-computed candidate move with an elevated `new_gap_penalty`
(0.13, at frame 1170, Team A, track 55) that the search itself does
NOT recommend (its own `benefit` is negative) — chosen specifically to
illustrate what this failure mode looks like, since the search's own
top-ranked, auto-selected recommendation naturally avoids it. See
`HANDOFF.md` for the exact reproduction command.

## Multi-region fixer assignment (Top-3 round)

`analytics/multi_region.assign_regions_and_fixers` reuses THIS module's
`search_repositioning` unchanged for every region's assigned fixer —
the secondary/tertiary region's recommended move is computed by the
exact same bounded local search, benefit formula, and wording
discipline ("best candidate within the tested local search") as the
primary region's own. The only new logic is UPSTREAM of this module:
deciding which real player gets to be the candidate passed in for each
region (see `docs/METRIC_DEFINITIONS.md` §2c's conflict-resolution
rule) — `search_repositioning` itself has no notion of "regions" or
"conflicts," it is simply invoked once per (region, assigned fixer)
pair, exactly as it always was for the single primary region.

A consequence worth stating explicitly: `structural_damage_penalty`
(the moved player's own `abandonment_penalty`) is evaluated
independently for each region's assigned fixer, anchored to THAT
player's real current position — it does NOT account for a scenario
where two DIFFERENT regions' fixers move simultaneously (e.g. a
secondary fixer's own abandonment cost is calculated as if only they
moved, not jointly with the primary fixer's simultaneous move). This is
a disclosed scope limit of running N independent single-player searches
rather than one joint multi-player optimization — consistent with this
module's own "never claims a global/joint optimum" wording discipline,
now extended to say so across multiple simultaneous single-player
recommendations too.
