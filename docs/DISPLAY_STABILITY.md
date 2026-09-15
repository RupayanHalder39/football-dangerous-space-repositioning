# Display Stability — Causal DISPLAY-ONLY Stability Pass

Round 3 of the graph/dashboard polish work (after §8b's 16s window and
§8c's 20s window, both in `HANDOFF.md`). This round did not touch the
graph windowing at all -- the 20-second rolling window is **locked**
(see `HANDOFF.md` §8c/§8d) -- and did not touch any analytics formula.
It addresses a different complaint: reviewing the 20-second demo video
showed the dashboard OVERLAYS (not the football footage) fluctuating
too aggressively frame-to-frame -- a "disco dance" effect in the
dangerous-space highlight, the recommended player/target, and the
status badge, plus residual reactivity in Graph 2.

## What did NOT change

- **The football broadcast video plays at normal real-time speed.**
  `render_frame()` still reads exactly one real video frame per call
  (`cap.set` + `cap.read`); `main()`'s new `--out_path` mode writes the
  output at the source's own `match.fps` (30.0), one real frame in for
  one frame out -- no frame duplication, no slow-motion, no altered
  FPS. See `test_full_dashboard_renderer_smoke` and the QA video's own
  measured duration (below).
- **The 20-second rolling window, 4-second ticks, absolute match time,
  NOW-cursor-at-right-edge, full per-frame-resolution computation, and
  the three per-graph EMA alphas for Graphs 1 and 3** (`SEVERITY_EMA_ALPHA
  = 0.6`, `SPATIAL_BALANCE_EMA_ALPHA = 0.5`) are all unchanged from
  §8c/§8b.
- **Every analytics formula** -- `dangerous_space.py`,
  `opponent_access.py`, `spatial_balance.py`,
  `counterfactual_repositioning.py`, `player_responsibility.py`,
  `coach_signals.py` -- was not opened this round. `rank_candidates`
  and `search_repositioning` are still called with the real,
  current-frame roster and region on every single frame, for every
  candidate this round's new code asks about. Nothing here changes
  what those functions compute -- only WHICH of their already-real
  results gets shown, and for how long.
- **Voronoi geometry** is still `voronoi_for_players(team_a, team_b)`
  computed fresh from the real current-frame positions every frame --
  never temporally smoothed or averaged.
- **No future frame is ever used.** Every stabilizer's `update()` is a
  pure function of the current frame's real inputs plus its own past
  state -- see `tests/test_display_stability.py::test_no_future_leakage_*`,
  which prove that two different possible futures after an identical
  real prefix produce byte-identical outputs for that prefix.

## New module: `dashboard/display_stability.py`

Three small causal state machines, all DISPLAY-layer only (see the
module's own top-of-file docstring for the full contract):

### 1. `DangerRegionStabilizer` — which team's region is highlighted

The two teams' severities are frequently close (median gap on this
clip, when both are valid, is ~0.10, but 20% of the time under 0.03),
so a per-frame argmax (the original behavior) flips the highlighted
team constantly. This class:

- keeps showing the same team's region unless the other team becomes
  worse by more than `SWITCH_MARGIN_REGION = 0.03` (severity units)
  **and** at least `MIN_HOLD_SEC_REGION = 0.5s` has passed since the
  last switch;
- switches **immediately, with no hold**, the instant the displayed
  team's own evidence genuinely vanishes (an honest disappearance, not
  a "smoothed" one);
- separately EMA-smooths (`REGION_DRAW_EMA_ALPHA = 0.35`) only the
  DRAWN circle's centroid/radius. `opponent_control_of_region` and
  `search_repositioning` are always given the REAL, unsmoothed
  `(x, y)` and area of whichever team is displayed -- only the circle
  actually painted on screen is smoothed, purely cosmetic, never fed
  back into any computation.

### 2. `RecommendationStabilizer` — which player/target is recommended

- keeps showing the same recommended player for at least
  `MIN_HOLD_SEC_RECOMMENDATION = 0.5s`;
- after that hold, switches to a new raw top-ranked candidate only if
  its real, current-frame benefit exceeds the CURRENTLY DISPLAYED
  player's own real, freshly-recomputed current-frame benefit by more
  than `SWITCH_MARGIN_RECOMMENDATION = 0.002` (benefit units --
  realistic benefits sit in the 0.001-0.01 range per
  `docs/REPOSITIONING_LOGIC.md`) -- both sides of the comparison are
  real `search_repositioning` results for the current frame, never a
  frozen or fabricated number;
- invalidates **immediately, no hold**, the instant the displayed
  player leaves the current frame's candidate roster, the defending
  team changes, or there is no danger region at all this frame;
- separately applies a causal EMA (`TARGET_DISPLAY_EMA_ALPHA = 0.30`,
  within the requested 0.25-0.4 range) to the DISPLAYED target point
  only -- `counterfactual_repositioning.py`'s own candidate coordinates
  are untouched. The smoothing resets (never blends across) whenever
  the recommended player changes, the recommendation becomes invalid,
  or a real gap occurs (no valid candidate this frame).

### 3. `LabelStabilizer` — the top-row status badge text

- holds the current title for at least `MIN_DWELL_SEC_LABEL = 0.5s`
  before allowing a switch between two otherwise-valid labels (LOW /
  MODERATE / HIGH RISK churn, or newly entering RECOMMENDATION FOUND);
- **never** delays a switch TO "UNCERTAIN" -- genuinely missing or
  invalid evidence is always shown immediately;
- **never** delays LEAVING "RECOMMENDATION FOUND" -- once the
  recommendation itself is genuinely gone this frame, the badge drops
  it immediately rather than finishing its dwell time (this is the
  literal implementation of "do not hold an invalid recommendation
  merely for cosmetic smoothness");
- the subtitle/color for whichever title IS currently shown are always
  refreshed to this frame's real numbers even while the title itself
  is held (e.g. the "Team A: 0.52  Team B: 0.41" live readout keeps
  updating under a held "MODERATE RISK" title).

### `DashboardDisplayStabilizers`

Bundles the three above. `render_frame()` accepts an optional `stab`
parameter (default `None` → a fresh, empty instance is created for that
one call). A fresh instance's first observation always adopts
immediately, so every independent, non-sequential preview call (the 6
standalone previews) behaves EXACTLY as before this round -- there is
no history to persist between unrelated random-access frames anyway.
`main()`'s new `--out_path` mode creates ONE instance and threads it
through every sequential frame, so the hold/margin/EMA mechanisms can
actually do their job across real time. This is also the code path the
eventual full 120-second render will reuse.

## Minor accompanying cosmetic changes (Part 4)

Voronoi fill opacity was reduced slightly to reduce visual busyness:
`draw_voronoi_on_frame`'s default `alpha` 0.16 → 0.13 (broadcast panel),
`draw_voronoi_perspective`'s default `alpha` 0.20 → 0.16 (radar panel).
Line thickness, label content, and the Voronoi geometry itself are all
unchanged -- purely a fill-opacity tweak.

## Graph 2 display-alpha comparison (Part 5)

Generated `outputs/qa/graph2_alpha_comparison.png`: the same real
`threat_a`/`threat_b` history (frame 1040, the flagship moment, full
20s window) drawn three times with `alpha` = 0.20 (previous), 0.15,
and 0.12. A roughness metric (mean absolute frame-to-frame change of
the smoothed, full-resolution series) was also computed:

| alpha | threat_a mean\|Δ\| | threat_b mean\|Δ\| |
|---|---|---|
| 0.20 (previous) | 0.0292 | 0.0259 |
| 0.15 | 0.0261 | 0.0242 |
| 0.12 | 0.0241 | 0.0232 |

All three look visually very similar -- the sharp real spikes (a fast-
reacting logistic access model, disclosed since §8b) are large real
jumps that light EMA smoothing at any of these three alphas cannot
flatten without also flattening real tactical swings, and pushing all
the way to 0.12 buys only a modest additional ~8% roughness reduction
over 0.15 for a visually indistinguishable result. Chose **0.15** as
the lightest of the three that gives a real, measurable improvement
over the previous 0.2 (`OPPONENT_CONTROL_EMA_ALPHA = 0.15`, was 0.2).
Graphs 1 and 3 (`SEVERITY_EMA_ALPHA`, `SPATIAL_BALANCE_EMA_ALPHA`) were
not touched -- no visual issue was found in either.

## Quantitative flicker-rate verification

Measured directly (not just visually) on the same 601-frame / 20-
second range used for the demo clip (frames 440-1040), comparing the
RAW pre-this-round behavior against the STABILIZED behavior, using the
real analytics functions on real match data (script logic mirrors
`render_frame`'s own branching exactly):

This clip segment is itself fairly gap-heavy: neither team has a valid
danger region at all in 198 of the 601 frames (33%) -- a real,
disclosed property of this specific 20s window's tracking evidence,
not a display-stability bug. Genuine appear/disappear transitions
around those gaps are correctly immediate in both the raw and
stabilized behavior (see "Do NOT invent continuity" throughout this
document), so counting them as "flicker" would be misleading. Restricting
the count to consecutive-frame pairs where evidence was genuinely
present on both sides (294 such pairs) isolates the AVOIDABLE flicker
that display-stability is meant to remove:

| transition (evidence present both frames) | raw (before) | stabilized (after) | reduction |
|---|---|---|---|
| displayed team flips | 51 | 1 | 98% |
| recommended-player changes | 131 | 21 | 84% |

For the status label, the honest picture needs the same gap-exclusion
treatment as above. Across the full 601-frame range, RAW and
STABILIZED both change label almost equally often (225 vs 219, only a
3% drop) -- because most of that churn is genuine, frequent
UNCERTAIN-involving transitions in this gap-heavy clip, and those are
**correctly never suppressed** in either version (an earlier build of
`LabelStabilizer` had a bug that debounced LEAVING "UNCERTAIN" as if
it were ordinary risk-level churn, which produced an artificially low
"225→6 (97%)" number by silently holding stale "UNCERTAIN" text after
real evidence had already returned -- caught during this round's own
visual QA, see "A bug caught during this round's own QA" below, and
fixed before this document's numbers were finalized). Restricting the
count to transitions where NEITHER side is "UNCERTAIN" isolates the
genuinely avoidable LOW/MODERATE/HIGH-RISK churn the debounce is
meant to remove: raw=8, stabilized=2 (75% reduction) over this
601-frame range.

## A bug caught during this round's own QA

The first rendered version of the stabilized 20-second clip was
visually reviewed against the pre-stability version at the same six
instants before being accepted. That review caught a real defect:
at t=19.7s, t=29.7s, and even the flagship t=34.7s
"RECOMMENDATION FOUND" moment, the stabilized badge incorrectly read
"UNCERTAIN" while the pre-stability version correctly showed a real
status. Root cause: `LabelStabilizer.update()` treated entering
"UNCERTAIN" as immediate but LEAVING it as ordinary debounced churn,
so a brief real data gap a few frames earlier could leave a stale
"UNCERTAIN" on screen for up to `min_dwell_sec` after real evidence
had already returned -- silently hiding a real recommendation, the
exact failure mode item 6 of this round's brief explicitly warned
against ("do not hold an invalid recommendation merely for cosmetic
smoothness"; the same reasoning applies symmetrically to not holding
a stale UNCERTAIN). Fixed by making every transition touching
"UNCERTAIN", in either direction, immediate -- see
`LabelStabilizer`'s docstring and
`tests/test_display_stability.py::test_label_leaving_uncertain_is_also_always_immediate`
(a regression test added specifically for this). The clip was then
re-rendered and the quantitative numbers above reflect the FIXED
behavior, not the buggy one.

## QA — old vs new, same 20-second clip

Re-rendered the identical clip (frames 440-1040, `--start_frame 440
--end_frame 1040`) through `main()`'s new `--out_path` mode to
`outputs/qa/dangerous_space_repositioning_20s_demo.mp4` (overwriting
the pre-stability-pass version; its sampled frames were preserved
separately for this comparison) — **this specific render was removed
in a later disk-space cleanup pass** (HANDOFF.md §17); the CURRENT demo
clip lives at
`outputs/final_demo/dangerous_space_repositioning_20s_final.mp4 (this file itself was superseded by this final round; see HANDOFF.md §19)`.
Programmatic checks (frame count,
fps, canvas size, duration, non-blank/motion sanity) were re-run
exactly as in the previous round and all passed -- see the contact
sheet `outputs/qa/display_stability_old_vs_new_contact_sheet.png` for
the six inspected instants (start/5s/10s/15s/end -- end and the
"strong recommendation moment" coincide in this clip, both at
t=34.7s, frame 1040).

## Tests

`tests/test_display_stability.py` (22 tests, all passing) covers: hold
suppresses an early switch; a switch fires once the hold has elapsed
and the margin is clearly exceeded; a near-equal candidate does NOT
cause a switch; immediate invalidation when a player leaves the
roster or the defending team flips; reset to `(None, None)` with no
context; target-smoothing resets (not blends) on a player change; a
genuine EMA blend between two real values; target-smoothing reset on
a real gap; region hold/margin/immediate-loss behavior; the DRAWN
region point is confirmed to be a real EMA of two real points, never
a fabricated third value; label dwell, immediate UNCERTAIN, immediate
leaving-RECOMMENDATION-FOUND, and live subtitle refresh under a held
title; and, for both the recommendation and region stabilizers, an
explicit no-future-leakage test (two different futures after an
identical real prefix produce identical outputs for that prefix).

`external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q` → 55 passed
`external/sports/.venv/bin/python3 -m pytest tests/ -q` → 638 passed (unchanged elsewhere in the repo)

## `MultiRegionStabilizer` — extending hysteresis to N ranked slots (Top-3 round)

Added when Top-3 Distinct Dangerous Regions (see `docs/
METRIC_DEFINITIONS.md` §2c) needed the SAME "don't let a display
element flicker frame-to-frame" guarantee `DangerRegionStabilizer`
already gives the single primary region, generalized to the 2 EXTRA
(secondary/tertiary) slots. The primary region/team decision itself is
untouched — still exactly `DangerRegionStabilizer` + `RecommendationStabilizer`,
unmodified.

**Identity key**: each slot remembers WHICH opponent Voronoi cell it is
showing by that cell's own owning `track_id` (a real opponent player,
tracked frame to frame) — the same kind of stable identity
`RecommendationStabilizer` already keys player identity on, generalized
from "one player" to "one region owner."

**Per-frame algorithm** (`update(t, fresh_candidates)`):
1. A slot whose previous occupant's `track_id` is still present among
   this frame's fresh, already-deduplicated candidates keeps it,
   refreshed with the current real severity/x/y/area — even if its raw
   rank shifted slightly among the fresh candidates.
2. That held occupant can only be DISPLACED by a different,
   not-yet-claimed candidate whose severity exceeds it by more than
   `SWITCH_MARGIN_MULTI_REGION` (0.03, same scale/units as the primary
   region's own `SWITCH_MARGIN_REGION`) AND only once
   `MIN_HOLD_SEC_MULTI_REGION` (0.5s, same value as every other hold in
   this file) has passed since that slot's last change.
3. A slot whose previous occupant's `track_id` is NO LONGER present at
   all (ineligible now, merged away by de-duplication, or fewer real
   distinct regions exist) is cleared IMMEDIATELY — no hold, identical
   "genuine loss of evidence is never held" principle as every other
   stabilizer here.
4. A currently-empty slot fills from the best remaining unclaimed
   candidate immediately — no hold needed to START showing something
   new; the hold only protects against churn BETWEEN two already-real
   options.

Never uses a future frame — `tests/test_multi_region.py::
test_no_future_leakage_multi_region_stabilizer` locks this in with the
same "two different futures, identical prefix outputs" pattern used
throughout this file.

**Scope decision (disclosed)**: the secondary/tertiary region's OWN
assigned fixer is recomputed fresh each frame from the (already
slot-stabilized) region — it does not have its own dedicated
hold/margin hysteresis layer the way the primary recommendation does.
In practice this is usually sufficient: a stabilized region's nearest
real defenders rarely change frame-to-frame, so the fixer choice
inherits stability transitively. A future round could add a dedicated
secondary-fixer stabilizer if flicker is observed in practice; none was
observed in this round's own QA (see `HANDOFF.md` §15).

Tests: `tests/test_multi_region.py` (13 stabilizer-specific tests) —
keeps a stable occupant across minor severity refreshes; does not
switch within the hold window even when a clearly stronger candidate
appears; switches once the hold elapses and the margin is exceeded;
does not switch for a near-equal candidate; drops a vanished region
immediately; fills an empty slot immediately with no hold; clears all
slots on a full gap; never exceeds `n_slots`; no-future-leakage.
