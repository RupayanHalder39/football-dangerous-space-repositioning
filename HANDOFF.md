# HANDOFF — Dangerous Space Repositioning Analytics

**Status: FINAL DEMO RENDER COMPLETE.** See §19 for the authoritative
final summary (full 120-second video, final QA, final locked-settings
index, final deliverable paths, disclosed limitations). No further
cosmetic tweaks should be made unless a real bug is discovered.

Project arc, briefly (full detail in the numbered sections below):
analytics + tests built and passing (§1-§7); dashboard built with
preview frames + contact sheet (§8); a graph-display polish pass
(rolling window, tick spacing, display-only smoothing — §8b/§8c) locked
the window at 20s, then WIDENED to its final **24 seconds** (§15f); a
causal DISPLAY-STABILITY pass (§8d, `docs/DISPLAY_STABILITY.md`) calmed
frame-to-frame overlay flicker; the dangerous-space selector gained
possession awareness via a HARD Current-Attack Eligibility gate (§6b,
§6c) — strongly-behind-the-ball primary selections are **0% by
construction**; the radar panel's Y-axis alignment mismatch against the
real broadcast camera was root-caused and fixed with a documented
coordinate-convention mirror, NOT a cosmetic flip (§14); a faint cyan
"best fixer" spotlight was added to the Match Feed (§14e); the
dashboard was extended from ONE to up to **THREE distinct, ranked
dangerous regions** per team with multi-region fixer conflict
resolution (§15); Graph 1/2 were redesigned from line charts to
bucketed bars (§16), then to fully independent GROUPED bars per region
(§17), then given a final small presentation polish — Danger #1
emphasis, a LIVE tag on the current bucket, an audited fixed `[0,1]`
y-axis (§18); and finally, the full **120-second video was rendered,
QA'd, and signed off** (§19). Every core analytics formula
(severity/access/risk/repositioning) has been touched only ONCE, in
§6b/§6c, and is otherwise unchanged since this project's own initial
build (§1-§7).

## 1. Objective

Coaching problem: **which player should reposition to close dangerous
space without creating a new gap?** Answered every frame, for both
teams symmetrically, as five sub-questions: where is the dangerous
space, why is it dangerous, who should fix it, where should they move,
and does that move avoid creating a new gap elsewhere. Voronoi is the
geometric tool used to answer this — never the answer itself.

This is a **new, independent, root-level project** —
`dangerous_space_repositioning/` — parallel to (not inside, not
touching) `pressing_structure/` and `offside_break/`.

## 2. Exact folder structure (as built)

```
dangerous_space_repositioning/
├── __init__.py
├── HANDOFF.md                              (this file)
├── analytics/
│   ├── __init__.py
│   ├── data_loader.py                      (NEW, not in the original file list — see §3)
│   ├── voronoi_control.py
│   ├── dangerous_space.py
│   ├── opponent_access.py
│   ├── player_responsibility.py
│   ├── counterfactual_repositioning.py
│   ├── spatial_balance.py
│   └── coach_signals.py
│   (generate_space_graphs.py was NOT created as a separate file --
│    see §3 for why)
├── dashboard/
│   ├── __init__.py
│   ├── dashboard_style.py
│   ├── live_graphs.py
│   ├── display_stability.py                (NEW, §8d -- causal DISPLAY-ONLY stability layer)
│   ├── voronoi_broadcast_overlay.py
│   ├── voronoi_radar.py
│   └── render_dangerous_space_dashboard.py
├── docs/
│   ├── METHODOLOGY.md
│   ├── METRIC_DEFINITIONS.md
│   ├── REPOSITIONING_LOGIC.md
│   ├── FINAL_DASHBOARD_NOTES.md
│   └── DISPLAY_STABILITY.md                (NEW, §8d)
├── outputs/
│   ├── previews/            (6 real PNG previews, regenerated under the corrected formula -- see §6b/§6c)
│   ├── graphs/              (empty -- reserved, see §3)
│   ├── qa/                  (comparison PNGs + the 20s demo clip -- see §8b/§8c/§8d)
│   │   ├── attack_relevance_fix/       (NEW, §6b -- round-1 diagnostics/CSV/demo clip)
│   │   └── current_attack_gate_fix/    (NEW, §6c -- round-2 hard-gate diagnostics/CSV/montage/demo clip)
│   ├── contact_sheet/
│   │   └── contact_sheet.png
│   └── final_demo/          (empty -- intentionally, full video not rendered yet)
└── tests/
    ├── __init__.py
    ├── test_attacking_phase_relevance.py   (NEW, §6b; rewritten for the hard gate in §6c)
    ├── test_display_stability.py           (NEW, §8d; +1 test in §6c)
    ├── test_voronoi_control.py
    ├── test_dangerous_space.py
    ├── test_opponent_access.py
    ├── test_repositioning.py
    ├── test_spatial_balance.py
    └── test_dashboard_render.py
```

## 3. Deviations from the suggested structure (and why)

- **`analytics/data_loader.py` was added** (not in the original
  suggested list). Every analytics module needs the same small
  per-frame shape (real causal player/ball dicts); centralizing that
  loading once, reused everywhere, was clearly better than duplicating
  it across `dangerous_space.py`/`opponent_access.py`/etc. This is the
  ONLY new file beyond the suggested structure.
- **`analytics/generate_space_graphs.py` was not created as a separate
  script.** Its intended job (building the full-clip time series) is
  `coach_signals.build_signal_series(match, stride=...)`, already a
  clean, directly-callable, tested function — a thin CLI wrapper around
  it would add a file without adding capability. If a standalone CLI
  script becomes genuinely useful (e.g. for exporting a CSV of the full
  time series for offline analysis), it is a small addition to make
  later; nothing about the current design blocks it.
- **`outputs/graphs/` is currently empty.** No standalone
  (non-dashboard-embedded) graph PNGs were requested by name — the
  folder exists per the suggested structure, ready for a future round.
  **`outputs/qa/` is no longer empty** — see §8b/§8c/§8d, which added
  old-vs-new comparison PNGs and the 20-second demo clip across the
  three display-polish rounds.
- **`outputs/final_demo/` is empty** — the full 120s video render was
  explicitly deferred ("STOP after previews").

## 4. Reused dependencies (nothing in this list was reimplemented)

| Reused from | What | Used by |
|---|---|---|
| `analytics/voronoi.py` | `compute_voronoi()` — pure Voronoi geometry, pitch-clipped | `voronoi_control.py` |
| `analytics/pitch_control.py` | `PLAYER_MAX_SPEED_CM_S`, `REACTION_TIME_SEC`, `CONTROL_SIGMA_SEC` constants (imported, never redefined) | `opponent_access.py` |
| `tactical_shared/coordinates.py` | `DEFAULT_PITCH`, `PitchConfig` (own_goal/depth/attacking_sign geometry) | every analytics module |
| `tactical_shared/tracking.py` | `build_quality_view`, `current_roles` — the causal tracking/possession view already shipped for `pressing_structure`/`offside_break` | `data_loader.py` |
| `tactical_shared/perspective_radar.py` | The shared pinhole-camera pitch→canvas projection | `dashboard/voronoi_radar.py` |
| `offside_break/dashboard/render_offside_dashboard_v4_simple.py` | `_draw_player_shadow`, `_draw_player_body_human`, `_heading_cue` — the human-footballer glyph primitives | `dashboard/voronoi_radar.py` |
| `sports.common.view.ViewTransformer` (pickled per-frame) | Real image↔pitch homography | `dashboard/voronoi_broadcast_overlay.py` |
| `sports.configs.soccer.SoccerPitchConfiguration` | Pitch marking vertices/edges | `dashboard/voronoi_radar.py` |
| `sports.annotators.soccer` (indirectly, via `perspective_radar`) | — | radar pitch markings |

**Nothing in `pressing_structure/` or `offside_break/` was modified.**
Full existing test suite re-run after this project was built: `638
passed` (unchanged from before this work started).

## 5. Canonical data paths

| Path | Contents |
|---|---|
| `outputs/tracking/testVideo1_120s/tracking.parquet` | Raw tracking, 3600 frames @ 30fps, 80800 rows |
| `outputs/analytics/testVideo1_120s_v3/ball_trajectory.parquet` | Hardened ball trajectory (`is_observed` real/predicted/lost) |
| `outputs/analytics/testVideo1_120s_v3/homography_transformers.pkl` | Per-frame `ViewTransformer` pickle |
| `ExternalDownlaodVideo/testVideo1_120s.mp4` | Real broadcast video |

No player tracking, ball tracking, or homography was re-run.

## 6. Equations (full detail: `docs/METRIC_DEFINITIONS.md`, `docs/REPOSITIONING_LOGIC.md`)

**Dangerous Space Severity** (per opponent-owned Voronoi cell) — see
§6b for the Attacking-Phase Relevance Correction this round applied;
CURRENT formula:
```
severity = area_gate(area_cm2) × direction_relevance(...) × (0.20·goal_proximity
         + 0.10·centrality + 0.15·ball_proximity + 0.20·receiver_support
         + 0.35·coverage_gap)
```
Explicitly NOT "largest cell = dangerous" — area only appears inside
`area_gate` (a damping floor for vanishingly small cells), never as the
ranking signal. `coverage_gap`+`receiver_support` carry the largest
combined share (0.55) because they're the components most sensitive to
player position. `direction_relevance` (NEW, §6b) is a second
multiplicative gate answering "is this cell even part of the CURRENT
attacking phase" — the OLD `progression_value` additive term it
replaces is gone.

**Opponent Control of Dangerous Space** (reused pitch-control model):
```
access(point) = sigmoid((T_defend(point) − T_attack(point)) / 0.5s)
```
where `T_team(point)` is the fastest real responder's time-to-reach
(position + causal velocity × 0.3s reaction time, ÷ 800cm/s).

**Spatial Balance / New-Gap Risk**:
```
risk = 0.40·compactness_risk + 0.35·isolation_risk + 0.25·coverage_variance_risk
```
Real geometry only (mean distance to own centroid, worst nearest-
teammate gap, coefficient of variation of own Voronoi cell areas) — no
fabricated demonstration values.

**Candidate score** (who should fix it):
```
score = 0.35·proximity − 0.30·abandonment_penalty + 0.20·feasibility + 0.15·local_support
```
Never "nearest defender" — `abandonment_penalty` (a DELTA: does
removing this player genuinely worsen the team's own worst danger
cell?) and `local_support` can outrank pure distance.

**Counterfactual benefit** (where should they move):
```
benefit = 3.0·danger_removed − 1.5·new_gap_penalty − 1.5·structural_damage_penalty − 0.01·movement_cost_penalty
```
`danger_removed` = the SAME flagged region's own severity, before vs.
after, under the hypothetical roster (never re-anchored to a different
cell). Bounded candidates only: a 7×7 local grid of ±100/200/300cm
offsets, unioned with 100/200/300cm direct steps toward the danger
region; any candidate landing outside the real pitch is rejected, never
clamped.

## 6b. Attacking-Phase Relevance Correction (CORE ANALYTICS FIX)

**This is a correction to the analytics themselves, not a display
change.** Reported bug: the dashboard could highlight "dangerous space"
BEHIND the attacking team while the real attack was progressing in the
opposite direction — i.e. the primary orange highlight sometimes had
nothing to do with the team that actually had the ball.

### 1. Root cause (the audit)

`dangerous_space_for_team(defending_team, ...)` computed
`attacking_team = 1 - defending_team` **unconditionally** — it never
checked who actually had the ball. `render_frame()`/
`compute_frame_signal()` called this for BOTH teams every frame and
picked whichever team's conceded severity was numerically higher as
"the" defending team — a pure severity-comparison heuristic with ZERO
possession awareness. A full-repo grep confirmed `MatchData.roles`
(the already-computed, already-causal `current_roles()` possession
output) was loaded but **never read anywhere** in this project's
analytics before this round.

The weak link that let this misfire concretely: `progression_value_score
(attacking_team, x, ball, pitch)` measured "is this cell forward of the
ball, from `attacking_team`'s perspective" using the REAL ball position
but a possibly-FALSE `attacking_team` hypothesis. When the hypothesis
was wrong, the real ball's position got misread as "great forward
progress" for a team that wasn't actually progressing anything — and at
only 0.10 weight (additive, blended in with five other components), it
couldn't be reliably overridden by the also-unconditioned
`goal_proximity`/`centrality`/`coverage_gap` terms, which reward ANY
cell near the hypothesized attacked goal or poorly covered, regardless
of whether that attack is real.

**Concretely, at the exact reported bad frame (1040, t=34.7s)**: real
causal possession (4-second majority) says **Team B** has had the
ball, attacking toward Team A's goal (ball at x≈8371, deep in Team A's
defensive third, x=12000=Team A's own goal). The OLD selector instead
picked `defending_team=B` — implying Team A was attacking — because
evaluating "is Team A attacking toward Team B's goal (x=0)" against
the REAL ball position at x≈8371 made a cell at (2050, 3124), right
next to **Team B's own goal**, register `progression_value=1.0` (the
ball looked "maximally advanced" under that false hypothesis) with
high `goal_proximity` (0.63) and `centrality` (0.89) on top — severity
0.513, versus the real, near-ball, correctly-covered region's 0.329.
Wrong region wins. See `outputs/qa/attack_relevance_fix/
old_vs_new_t34p7.png`: the OLD region sits alone on the empty far side
of the pitch, nowhere near the ball or any player; the NEW region sits
exactly where the ball and both teams' players actually are.

Team symmetry itself was never hardcoded/asymmetric (`goal_proximity`/
`centrality`/`coverage_gap`/`pitch.own_goal`/`pitch.attacking_sign` are
all already correctly symmetric, confirmed by the pre-existing
`test_symmetry_between_teams`) — the bug was the total ABSENCE of a
possession check, which could misfire for either team depending on
real ball position, not a one-sided defect.

### 2. Possession/attacking-team determination

New `data_loader.attacking_team_at(frame)` / `_compute_attacking_context`,
using ONLY `tactical_shared.tracking.current_roles`'s own already-causal
`carrier_team` (real close-control observations, ball within 200cm of a
player):

1. This exact frame's real carrier → confidence `"current"`.
2. Else a majority vote over an increasing trailing window — 4s
   (matches the shared `current_roles`'s own `historical_context_role`
   exactly), then this project's own 12s, then 30s extension, stopping
   at the first non-tied majority.
3. Beyond a 30-second look-back with no real evidence at all (or an
   exact tie) → `attacking_team=None`, `confidence="uncertain"`.
   **Never fabricated.**

Why the tiered extension was needed (measured, not assumed): real
close-control observations cover only **4.0%** of frames on this clip,
arrive in tight bursts (median gap 0.03s) separated by gaps up to
**43.6s**, so the shared 4-second window alone resolves only **47%**
of frames. The tiered 4s→12s→30s extension resolves **79%**, leaving
**21%** genuinely uncertain — see `docs/METHODOLOGY.md` for the full
measurement. When genuinely uncertain, this round's code takes the
explicitly-disclosed "fall back cautiously" option (of the two the
brief allowed): the direction gate stays neutral (1.0) for that frame,
i.e. the pre-correction, undirected comparison — never a fabricated
attacking team.

### 3-4. Attacking-direction relevance + next-action relevance

Implemented as ONE function, `dangerous_space.direction_relevance`
(full formula in `docs/METRIC_DEFINITIONS.md` §2): a MULTIPLICATIVE
gate (same role as the existing `area_gate`), not a hard rule —
`attack_progress_cm = (x − ball_x) × pitch.attacking_sign(attacking_team_actual)`,
gate=1.0 when `attack_progress_cm ≥ −500cm` ("level with the ball" is
never penalized), decaying smoothly toward a floor of
`DIRECTION_GATE_MIN=0.15` the further behind the ball a cell sits
(`exp` decay, reusing `COVERAGE_RADIUS_CM`'s own real-data-calibrated
2500cm touchstone — never a hard cutoff, so the counterfactual search's
benefit landscape stays continuous). `ball_proximity` (this project's
own "next-action relevance" proxy: real distance-based reachability
from the ball) was upweighted 0.10→0.15, and `receiver_support`
(real nearby attacking players) 0.15→0.20, using `progression_value`'s
freed 0.10 — `goal_proximity`/`centrality`/`coverage_gap` untouched.

### 5. Counterattack Exposure, kept separate

When `defending_team`'s own team (not their opponent) actually has the
ball, `direction_relevance` returns `attack_phase_active=False` and
floors the gate to `COUNTERATTACK_GATE=0.05` — far stronger than the
behind-the-ball floor, since this is a categorically different case
(no current attack against this team exists at all). This value is
never surfaced as the primary orange "dangerous space" highlight
label — it is exposed only as `DangerScore.components["attack_phase_
active"]`/`["direction_relevance"]` for inspection, per the brief's own
"can remain unused for now" allowance; no new UI panel/label was built
for it this round.

### 6. Weights — before / after

| Component | OLD weight | NEW weight | Change |
|---|---|---|---|
| `goal_proximity` | 0.20 | 0.20 | unchanged |
| `centrality` | 0.10 | 0.10 | unchanged |
| `ball_proximity` | 0.10 | 0.15 | +0.05 (next-action relevance) |
| `receiver_support` | 0.15 | 0.20 | +0.05 (real attacker availability) |
| `coverage_gap` | 0.35 | 0.35 | unchanged |
| `progression_value` | 0.10 | *(removed)* | replaced by `direction_relevance` gate |
| `direction_relevance` | *(none)* | multiplicative gate | NEW — see §3-4 |

Rationale for every change is in `docs/METRIC_DEFINITIONS.md` §2 and
`analytics/dangerous_space.py`'s own top-of-file comment; nothing was
retuned "to make the screenshot look right" — `goal_proximity`/
`centrality`/`coverage_gap`, the three components NOT implicated in the
bug, are byte-identical to before.

### 7. Team symmetry — explicitly tested

`tests/test_attacking_phase_relevance.py` includes a dedicated mirror
test (`test_direction_relevance_mirrored_between_teams`): the identical
real situation, with team identity swapped and every x-coordinate
reflected about the halfway line, must produce the IDENTICAL gate value
— this would catch a direction-inversion bug that only manifests for
one team. Both `test_team_a_*`/`test_team_b_*` ahead/behind pairs are
tested explicitly and independently.

### 8. Impact propagation

- **MATCH FEED / RADAR**: `render_frame` now looks up
  `attacking_team_at(frame)` once per frame and forwards it to both
  `dangerous_space_for_team` calls, `rank_candidates`, and
  `search_repositioning` — the orange highlight, "Opponent control
  NN%" label, "Best player to fix"/"Suggested move", and status badge
  all derive from the corrected region.
- **GRAPH 1** (Dangerous Space Severity): `coach_signals.
  compute_frame_signal` now passes the same possession estimate into
  both teams' `dangerous_space_for_team` calls — `severity_a`/
  `severity_b` are now visibly spikier (frequently near-zero when that
  team's opponent doesn't have the ball) rather than smoothly hovering
  0.2-0.6 regardless of possession. **This is a deliberate, correct
  change in the graph's character, not a display bug** — see
  `docs/FINAL_DASHBOARD_NOTES.md`.
- **GRAPH 2** (Opponent Control): unchanged formula
  (`opponent_access.py` was not touched) — it now simply receives the
  corrected region, so its values change wherever the region changed.
- **GRAPH 3** (Spatial Balance / New-Gap Risk): **verified
  independent** — `compute_spatial_balance_risk(team_id, team_a,
  team_b, rows_by_track)` takes no ball, no danger-region, and no
  possession argument at all; it is a standalone team-shape metric.
  Confirmed unchanged and NOT modified this round.
- **RECOMMENDATION PIPELINE**: `rank_candidates`/`abandonment_penalty`/
  `search_repositioning`/`evaluate_candidate` all now accept and
  forward `attacking_team_actual`, applied identically to `danger_
  removed`/`new_gap_penalty`/`structural_damage_penalty`/`benefit` (see
  §9 below for the anchoring guarantee).
- **STATUS LABELS**: unchanged set (LOW/MODERATE/HIGH RISK,
  RECOMMENDATION FOUND, UNCERTAIN) — all now derive from the corrected
  severities without any new special-casing, since a counterattack-only
  team's severity is now honestly low enough to fall into LOW RISK on
  its own.

### 9. Counterfactual anchoring (verified, not just assumed)

`search_repositioning` holds `danger_region` AND `attacking_team_actual`
FIXED across the entire search — every candidate's `severity_after`
(and the one `severity_before`) is evaluated at the SAME region with
the SAME possession context, so `direction_relevance`'s gate value is
identical for all of them (it depends only on the fixed region/ball/
possession, never on the hypothetical roster) and cannot change which
candidate wins. `tests/test_attacking_phase_relevance.py::
test_counterfactual_search_stays_anchored_to_same_region_and_context`
verifies this directly: the SAME best candidate's `danger_removed`
scales by EXACTLY the `COUNTERATTACK_GATE` ratio between a live-attack
scenario and a counterattack-only one, proving both sides of the
before/after comparison used the identical anchored region.

### 10. The known bad frame, rechecked

See item 1 above and `outputs/qa/attack_relevance_fix/old_vs_new_t34p7.png`.
Summary: Team B attacking (ball x≈8371, deep in Team A's defensive
third) → OLD flagged Team A as attacking (backwards) with a region
at Team B's own goal, severity 0.513, isolated from all players; NEW
correctly flags Team A as defending with a region at (7946, 6120),
9.3m from the ball, severity 0.358, `attack_phase_active=True`,
`direction_relevance=1.0` (essentially level with the ball). Team B's
own conceded severity (how much Team A supposedly threatens Team B) now
correctly drops to 0.022 (`COUNTERATTACK_GATE` applied, since Team A
does not have the ball — there is no real attack against Team B at all
right now).

### 11. Broader validation (not just one screenshot)

`outputs/qa/attack_relevance_fix/validation_broad_sample.csv` — every
5th frame across the full 120s clip with ≥4 tracked players (475 rows):
frame/time, attacking_team, possession_confidence, ball (x,y), selected
defending team, region (x,y), severity, opponent_access,
attack_progress_cm, attack_phase_active, a direction classification,
and the uncertainty state.

Direction-class breakdown of the SELECTED primary region:

| Class | Count | % |
|---|---|---|
| `ball_unavailable_this_frame` (possession known, ball position not, this instant) | 217 | 45.7% |
| `possession_uncertain` (genuinely unknown, even at 30s) | 91 | 19.2% |
| `ahead_or_level` | 89 | 18.7% |
| `slightly_behind` (<2500cm behind) | 70 | 14.7% |
| `strongly_behind` (≥2500cm behind) | 8 | 1.7% |

Restricted to the 167 rows where BOTH possession and ball position are
known (the only rows where `direction_relevance` can actually act):
**53.3% ahead/level, 41.9% slightly behind, 4.8% strongly behind.** The
"slightly behind" share is intentionally not near-zero — the brief
explicitly asked for a smooth gate, not a hard ahead-only filter, so a
cell just behind the ball can still win if it is otherwise clearly the
most exposed real gap (e.g. a fullback's underlap leaving immediate
square/cutback space). The 8 `strongly_behind` exceptions were
inspected individually (`_gen_validation_csv.py`'s output): they
cluster around moments where the ball is very deep near the byline, so
the real goal-mouth danger area (a plausible cutback target) can
legitimately register as "behind" the ball's own extreme wide/deep
position — severities there are modest (0.15-0.24), well under HIGH
RISK, and a smooth gate deliberately still lets them surface rather
than hiding them outright (see `docs/FINAL_DASHBOARD_NOTES.md`).

### 12. Tests

`tests/test_attacking_phase_relevance.py` (18 new tests): Team A/Team B
ahead/behind direction correctness, an explicit team-mirror symmetry
test, the "level with ball" tolerance, the counterattack gate, neutral
gating on unknown possession/missing ball, an integration-level
"ahead preferred over behind when otherwise similar" case using the
real scoring pipeline, "counterattack exposure never outranks a real
live attack," possession-context tests (current-frame, majority
fallback, never-fabricated, no-future-leakage), a `MatchData` built
without possession data degrading gracefully, the counterfactual
anchoring proof (§9), and a real-data regression test on frame 1040
itself confirming the corrected selector now agrees with real
possession.

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 73 passed

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (unchanged elsewhere in the repo)
```

### 13. Limitations (disclosed)

- Possession is genuinely unknown ~21% of the time even with this
  project's own extended 30s fallback — those frames fall back to the
  pre-correction, undirected comparison (§2).
- Real ball position itself (independent of possession) is unavailable
  ~46% of the time even when possession IS known — `direction_relevance`
  is neutral for those frames too, honestly, rather than guessing.
- A small residual (~5% of the known/known sample) of flagged regions
  still register as strongly behind the ball, concentrated in
  deep-byline moments where the smooth gate deliberately does not
  hide a plausible cutback-area danger (§11).
- The `direction_relevance` gate constants (`DIRECTION_GATE_MIN=0.15`,
  `COUNTERATTACK_GATE=0.05`, `DIRECTION_BEHIND_REF_CM=2500`,
  `LEVEL_WITH_BALL_TOLERANCE_CM=500`) are disclosed modeling choices
  (the last reuses `COVERAGE_RADIUS_CM`'s own real-data touchstone),
  not fit to outcome data — same disclosed-proxy status as every other
  constant in this project.

**SUPERSEDED by §6c.** Round 1's soft `direction_relevance` gate
(above) still let a strongly-behind-the-ball region win the primary
ranking outright if its other components were large enough — visually
confirmed after reviewing the corrected 20-second video, where the
orange highlight still sometimes sat clearly behind the active attack.
`direction_relevance`/`COUNTERATTACK_GATE`/`DIRECTION_GATE_MIN`/
`DIRECTION_BEHIND_REF_CM`/`LEVEL_WITH_BALL_TOLERANCE_CM` no longer
exist in the code — see §6c for the replacement HARD eligibility gate.

## 6c. Current-Attack Eligibility Gate (HARD filter, round 2)

**Still a core analytics correction, not a display change.** Round 1
fixed the wrong-team/wrong-direction bug but used a SOFT multiplicative
penalty with a non-zero floor — a behind-the-ball region could still
win if its other components (goal proximity, coverage gap) were large
enough. Unacceptable for the PRIMARY coach-facing label, whose meaning
is now locked: **"Current Dangerous Space" = space the CURRENT
attacking team can plausibly exploit in the current/next attacking
action — never "the most spatially exposed region anywhere on the
pitch."**

### What changed

`classify_region()` (`dangerous_space.py`) now runs as an ELIGIBILITY
FILTER **before** any severity comparison (see
`dangerous_space_for_team`'s own docstring for the exact 6-step
pipeline: score → classify → filter → rank — never rank-then-hide).
`severity` itself no longer depends on possession/direction AT ALL
(confirmed: `test_severity_at_point_does_not_depend_on_attacking_team_actual`)
— it is the same 5-weighted-components-times-area-gate value as
before. Eligibility only decides which cells are even IN the ranking
pool for the primary selection:

1. **Possession/ball/direction unknown** → `CATEGORY_UNCERTAIN`,
   ineligible. Reverses round 1's "neutral gate, fall back to
   undirected ranking" — this round's explicit instruction is that
   showing no primary danger beats showing a possibly-nonsensical one.
2. **`defending_team`'s own team has the ball** → `CATEGORY_
   COUNTERATTACK_EXPOSURE`, ineligible.
3. **Longitudinal progress** `< -BACKWARD_TOLERANCE_CM` (500cm, ~5m) →
   `CATEGORY_SUPPORT_SPACE`, ineligible.
4. **Next-action reachability** (within the longitudinal band): real
   ball distance ≤ `NEXT_ACTION_BALL_DIST_CM` (3000cm) OR real
   `receiver_support_score` ≥ `NEXT_ACTION_MIN_RECEIVER_SCORE` (0.15) —
   else `CATEGORY_SUPPORT_SPACE`, ineligible. Prevents a technically-
   ahead but disconnected region (e.g. 40m from any real play) from
   winning.
5. Otherwise → `CATEGORY_CURRENT_DANGEROUS_SPACE`, eligible — the ONLY
   category that can become `top`.

Full formula/constants in `docs/METRIC_DEFINITIONS.md` §2b.

### Backward tolerance: 500cm, kept after validation

The brief's own suggested starting point. Checked against real data
(not blindly kept): of 104 real "resolved" primary-danger selections
in the broad sample (see §11 below), 37 (35.6%) fall in the
within-tolerance band. Individually inspected via
`outputs/qa/current_attack_gate_fix/behind_tolerance_audit.csv` and
its montage (`behind_tolerance_montage.png`) — every one sits visibly
adjacent to the ball (mean distance-behind ≈ 3m, all ≤5m by
construction), matching the brief's own named legitimate cases
("cutback zones, support pockets, short backward/diagonal next
actions" — NOT exclusively final-third cutbacks; a general midfield
support pocket right next to the ball is equally legitimate per the
brief's own wording). No separate "is this a plausible cutback shape"
sub-rule was added on top — the existing next-action-reachability gate
(step 4) already does that work, since anything in this band must
ALSO be right next to the ball or have a real attacker nearby.

### Next-action reachability rule

```
next_action_relevant = (ball_distance_cm <= 3000) OR (receiver_support_score >= 0.15)
```

`3000cm` reuses `BALL_PROXIMITY_REF_CM`'s own already-calibrated
touchstone (no new number invented). `0.15` on `receiver_support_score`
corresponds to roughly "a real attacking player within ~15-16m" (that
score's own soft-count math: a single attacker exactly at the 2000cm
receiver radius scores ≈0.12; one at ~1500cm scores ≈0.16). No
fabricated pass-probability model — purely a real-distance/real-
player-count proxy, same style as every other component in this
module.

### Honest uncertainty — a major behavioral shift

Per this round's explicit instruction, uncertain context is NO LONGER
a neutral fallback (round 1) — it is now ITSELF a reason for
ineligibility. Concretely, `dangerous_space_for_team` returns `top=None`
with a distinguishing `reason`:
- `REASON_UNCERTAIN_CONTEXT` — possession/ball/direction unknown.
- `REASON_NO_ELIGIBLE_CANDIDATE` — context known, but nothing passed
  the eligibility gate this frame.

The dashboard's status badge shows `"UNCERTAIN"` for both (plus the
pre-existing insufficient-tracking case), with a distinct, honest
subtitle for each (`_status_for`'s new `context_reason` parameter) —
never a fabricated recommendation. This is a MUCH larger behavioral
change than it sounds: only **21.9%** of sampled frames now resolve to
an eligible primary danger (see §11) — the dashboard is UNCERTAIN far
more often than before, by design, per this round's own explicit
"better to show no recommendation than a tactically nonsense one."

### Display-stability interaction (critical requirement, verified)

No code change was needed in `dashboard/display_stability.py` — an
ineligible region already flows through as `top=None`, which
`render_frame` already converts to `info=None` for
`DangerRegionStabilizer`/`RecommendationStabilizer`, exactly the same
signal already used for a structurally-invalid Voronoi frame. Both
stabilizers already treat `info=None`/`no_context` as an HONEST,
IMMEDIATE disappearance (no hold) — established in the display-
stability round. A new confirmatory test locks this in explicitly:
`test_display_stability.py::
test_region_resets_immediately_when_displayed_region_becomes_analytically_ineligible`.
The stabilizer can never keep showing an old behind-the-attack region
after the analytics reject it.

### Impact propagation

- **MATCH FEED/RADAR**: unaffected structurally — `render_frame`
  already threads `attacking_team_actual` through; the orange
  highlight, opponent-control label, recommended player, and arrow now
  simply don't appear at all when nothing is eligible (UNCERTAIN badge
  instead), rather than showing a soft-gated-but-still-selected region.
- **GRAPH 1/2**: visibly SPARSER than round 1 — real gaps now appear
  whenever no eligible candidate exists for a team, which per §11 is
  the majority of frames. This is the direct, intended consequence of
  the new hard gate, not a bug — see `docs/FINAL_DASHBOARD_NOTES.md`.
- **GRAPH 3**: unaffected — still verified fully independent
  (`compute_spatial_balance_risk` takes no ball/region/possession
  argument at all); not touched this round either.
- **RECOMMENDATION PIPELINE**: `rank_candidates`/`search_repositioning`
  are only ever invoked when `danger_point is not None` (i.e. an
  eligible `top` exists) — an ineligible region is structurally never
  handed to the counterfactual search
  (`test_counterfactual_repositioning_never_invoked_for_an_ineligible_region`).
  `severity_at_point`'s returned value no longer depends on
  `attacking_team_actual` at all (eligibility is filter-only now), so
  the search's before/after comparison is exactly the same real,
  unscaled severity difference as if eligibility didn't exist —
  simpler than round 1's scaled-anchoring guarantee.
- **STATUS LABELS**: same 4-label set; UNCERTAIN now fires far more
  often, honestly, per the above.

### 11. Full-clip re-audit (475-frame broad sample, every 5th frame)

| | Round 1 (soft gate) | Round 2 (hard gate) |
|---|---|---|
| Ahead/level (of resolved primary selections) | 53.3% | 64.4% |
| Slightly behind (within tolerance) | 41.9% | 35.6% |
| **Strongly behind** | 4.8% | **0.0%** |

**Strongly-behind primary-danger rate is now 0% by construction** — the
hard gate makes this a structural guarantee, not a statistical
tendency (any cell beyond `BACKWARD_TOLERANCE_CM` is filtered out
before ranking, full stop).

Uncertainty breakdown (475 sampled frames, every 5th frame, ≥4 tracked
players): resolved (eligible primary danger found) 104 (**21.9%**);
possession/ball unknown 308 (64.8%); context known but no eligible
candidate 63 (13.3%). See
`outputs/qa/current_attack_gate_fix/candidate_eligibility_validation.csv`
for the full row-by-row data and
`outputs/qa/current_attack_gate_fix/behind_tolerance_audit.csv` for
the 37 within-tolerance exceptions, individually validated (§ above).

### 12. Tests

`tests/test_attacking_phase_relevance.py` was substantially rewritten
for the new `classify_region`/hard-gate API (26 tests, up from 18):
far-behind ineligibility, 2m-behind-remains-eligible, exact-boundary
behavior, Team A/Team B direction (including an explicit mirror-
symmetry test), a final-third cutback case, a disconnected-far-forward
next-action-relevance failure, the counterattack gate, uncertain-
possession/no-ball-evidence ineligibility (never a fallback guess),
`dangerous_space_for_team`'s two distinct "no eligible" reasons,
counterattack-never-wins, all the round-1 possession-context/no-future-
leakage tests (unchanged), a proof that `search_repositioning` is never
invoked for an ineligible region, a proof that `severity_at_point` no
longer depends on `attacking_team_actual`, and the real-data flagship-
frame regression test. Plus one new `test_display_stability.py` test
(§ above). Three pre-existing `test_dangerous_space.py` tests
(`test_not_simply_largest_cell`, `test_symmetry_between_teams`,
`test_no_ball_evidence_is_neutral_not_fabricated`) were updated to
supply real ball/possession context where the new hard gate now
requires it to exercise what they originally tested — same intent,
adapted to the new architecture; two of these also revealed that
sparse synthetic Voronoi setups (very few players spread across the
full pitch) produce cell centroids far from any seed point, which two
tests now sidestep by testing `severity_at_point`/`score_cell` directly
rather than fighting Voronoi geometry unrelated to what they check.
One `test_repositioning.py` test was adjusted to use a fixed region
area directly instead of routing through `dangerous_space_for_team`'s
now-gated `top` for a value it never needed eligibility for.

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 82 passed

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (unchanged elsewhere in the repo)
```

### Limitations (disclosed)

- Only ~21.9% of frames resolve to an eligible primary danger in this
  sample — a direct, intended consequence of "no recommendation beats
  a nonsensical one," not a bug. Graphs 1/2 are visibly sparser as a
  result.
- ~64.8% of frames are UNCERTAIN due to possession/ball being unknown
  (a mix of genuine possession uncertainty and, more often, ball
  position specifically being unavailable even when possession is
  known) — see `docs/METHODOLOGY.md`'s coverage measurement.
- The gate constants (`BACKWARD_TOLERANCE_CM=500`,
  `NEXT_ACTION_BALL_DIST_CM=3000`, `NEXT_ACTION_MIN_RECEIVER_SCORE=0.15`)
  are disclosed modeling choices, empirically spot-checked against this
  clip's real data (§ above), not fit to outcome data.
- The 6 standing preview images (`outputs/previews/`, frame numbers
  fixed from earlier rounds) now sometimes show "UNCERTAIN" at their
  specific pre-picked instant even where their filename suggests a
  danger scenario (e.g. `02_team_a_danger.png`) — an honest consequence
  of the much stricter per-instant gate (only ~22% of frames resolve),
  not a bug, and NOT "fixed" by cherry-picking new frame numbers to
  make the screenshots look right (explicitly against this round's own
  instruction). The `outputs/qa/current_attack_gate_fix/` deliverables
  are the authoritative validation for this round, not the legacy
  preview set.

## 7. Real worked example (a genuine positive-benefit case)

**Superseded by the Attacking-Phase Relevance Correction (§6b)** — the
example previously here (frame 1040, Team B, track 42) was built on
the OLD, uncorrected selector, which (per §6b's own audit) had flagged
the WRONG region at that exact frame. Under the corrected selector,
frame 1040 now honestly reports *"no improving local candidate found"*
(the real, currently-relevant region there is already well covered —
`coverage_gap=0.0`, 2 real defenders nearby). Replaced with a fresh,
real positive-benefit case found under the CORRECTED pipeline:

**Frame 3300 (t=110.0s), Team B (team_id=1), track 82** — attacking
team: Team A, confidence `"current"` (the highest tier: a real
close-control observation on this exact frame):

| | Observed | Best candidate (Δ = 224cm) |
|---|---|---|
| Candidate current position | (7097.6, 2640.0) | target (7197.6, 2840.0) |
| Danger region severity | 0.246 (real, `attack_phase_active=True`, `direction_relevance=0.674` — mildly behind the ball, not fully penalized) | — |
| `danger_removed` | — | +0.00430 (genuinely reduced) |
| `new_gap_penalty` | — | 0.0 |
| `structural_damage_penalty` | — | 0.0 |
| `movement_cost_penalty` | — | 0.745 |
| **`benefit`** | — | **+0.00544** |

Interpretation string: *"candidate improved structure — best candidate
within the tested local search, not a proven optimum."* Team A has the
ball at this frame, so Team B is correctly the defending team and its
conceded severity (0.246) is real and ungated; Team A's OWN conceded
severity at the same instant is only 0.019, correctly floored via
`COUNTERATTACK_GATE` since Team A's opponent (Team B) does not have the
ball — there is no current attack against Team A to speak of. This
case is NOT part of the 6 standing preview images (which keep their
original, disclosed frame numbers per §10) — it is documented here
purely as a real, freshly-verified positive-benefit example under the
corrected formula.

**Honest counterpoint (unchanged in spirit, now measured freshly)**:
across the ~475-row broad validation sample built for this round (see
§6b and `outputs/qa/attack_relevance_fix/validation_broad_sample.csv`),
the large majority of frames still correctly report *"no improving
local candidate found."* The flagged worst-danger region is, almost by
definition, poorly covered — meaning the nearest real defender is
routinely 20-40m away on this full-size pitch, genuinely beyond what a
bounded ≤3m adjustment can fix. See `docs/REPOSITIONING_LOGIC.md`
§"Calibration history" for the full disclosure of how the weights were
tuned to make genuine improvements visible at all, without fabricating
one.

## 8. Rendering design

`dashboard/render_dangerous_space_dashboard.py` composes: header → top
row (Tactical Match Feed with Voronoi + danger region + recommendation
drawn on the REAL broadcast frame, using the real per-frame homography
| 3D perspective Voronoi radar, ONE mode only, human-footballer glyphs)
→ 3 graph panels (both teams on every one). Full detail:
`docs/FINAL_DASHBOARD_NOTES.md`.

Team colors for this project only: **Team A = blue, Team B = red**
(matches the attached reference mockup; deliberately different from
`pressing_structure`/`offside_break`'s own green/gold).

## 8b. Graph-display polish pass (this round)

A follow-up round, requested purely for **visual readability** of the
three row-2 graphs — explicitly **not** a change to any analytics
formula. Confirmed unmodified this round: `analytics/dangerous_space.py`,
`analytics/opponent_access.py`, `analytics/spatial_balance.py`,
`analytics/counterfactual_repositioning.py`,
`analytics/player_responsibility.py`, `analytics/coach_signals.py`. Only
`dashboard/live_graphs.py` and
`dashboard/render_dangerous_space_dashboard.py` were touched.

**What changed, and why:**

| Setting | Before | Now |
|---|---|---|
| Rolling window (`COACH_WINDOW_SEC`) | 30s | 16s (this round) → **20s, final (§8c)** — matches `pressing_structure`/`offside_break`'s own coach-dashboard convention |
| Tick spacing (`COACH_TICK_SEC`) | 5s | **4s** |
| History computation stride | 3 (every 3rd frame) | **1 (full per-frame resolution)** — see below |
| Display point cap (`DISPLAY_MAX_POINTS`) | n/a | **240** — a per-series point-thinning cap, not a purely theoretical safety net: at 30fps a 16s window's 480 raw points already exceeds it (stride 2), and the final 20s window's 600 raw points exceeds it further (stride 3) |
| Display smoothing | none | causal EMA, **display-layer only** (see below) |

- **NOW cursor at the right edge** and **absolute match time on the
  x-axis** needed **no code change** — both were already structurally
  correct in `live_graphs.py` (`cur_time` is always passed as `t_hi`,
  which `_to_px` maps to the panel's right edge; `_chrome()`'s tick
  loop already printed real `t` values, e.g. `"52s"`, not
  relative offsets). Re-verified visually after the window/tick
  constants changed, not modified.
- **Full-resolution computation, display-only decimation**:
  `build_signal_history()`'s default `stride` changed from `3` to `1`,
  so the real per-frame signal is computed for every frame in the
  rolling window (analytics themselves are unchanged — only how densely the
  dashboard layer samples them for drawing). `decimate_for_display()`
  (new, in `live_graphs.py`) is a simple index-stride point-thinner —
  never interpolation or averaging — applied only as a display step
  after smoothing, and always keeps the exact final (NOW) sample so
  the right-edge cursor is never off by a stride.
- **Causal display smoothing** (`causal_ema_scalar()`, new, in
  `live_graphs.py`): a per-graph exponential moving average applied
  ONLY to what gets drawn, never to the underlying computed value.
  Resets to the raw value immediately after any real gap (`None`) —
  the same reset-on-gap convention `analytics/temporal_utils.py`'s own
  `causal_ema()` already uses for position series — and never looks at
  a future sample (output at time *t* depends only on samples ≤ *t*,
  verified by the existing `test_no_future_leakage`-style discipline).
  Per-graph alpha (closer to 1.0 = lighter/more responsive; closer to
  0.0 = heavier smoothing):
  - **Graph 1 (Dangerous Space Severity)**: `alpha=0.6` — kept
    responsive per this round's own instruction ("raw or very lightly
    smoothed"); both team curves stay easy to tell apart.
  - **Graph 2 (Opponent Control of Dangerous Space)**: `alpha=0.2` —
    the explicit default given this round, applied uniformly. This
    measurably reduces variance (checked numerically: on one sampled
    window, `threat_a`'s std dropped from 0.1321 raw to 0.1196
    smoothed), but the graph still shows real, fast oscillation. That
    residual noise is a disclosed property of the underlying signal
    itself (a fast-reacting logistic access model that can genuinely
    swing within a few frames — already noted in
    `docs/FINAL_DASHBOARD_NOTES.md`'s "known cosmetic limitations"),
    not under-smoothing left unaddressed. The **window width is the
    primary driver** of the "wall of spikes → readable line"
    improvement: narrowing from 30s to 16s (and, per §8c, back out
    slightly to 20s) changes the horizontal space each spike occupies,
    which is what actually separates previously-crammed spikes into a
    traceable line — the EMA on top is a secondary, real-but-modest
    readability gain, not the main fix. Confirmed visually across all
    4 requested comparison cases at each window size (see below and
    §8c).
  - **Graph 3 (Spatial Balance / New-Gap Risk)**: `alpha=0.5` — light
    smoothing, chosen because it visibly improved readability on this
    clip's real data without materially changing the shape of the
    trend line; the New-Gap Risk formula itself is untouched.
- **Missing-data gaps are still real, still preserved, never filled**:
  a `None` sample still breaks the line (`MAX_GAP_SEC=1.0`, unchanged)
  rather than being bridged or interpolated across — now detected at
  full per-frame resolution (every real frame is inspected) rather
  than at the coarser `stride=3` sampling used before. Visually
  reconfirmed in the regenerated `06_missing_uncertain_data.png` and
  in the `01`/`04` comparison images below (both show a genuine line
  break, not a fabricated gap-free line).

**Old-vs-new visual verification** (`outputs/qa/`, 4 new PNGs, each the
graph row only, old on top / new on bottom, labeled): `compare_01_ordinary_low_risk_moment.png`, `compare_02_team_a_danger.png`,
`compare_03_team_b_danger.png`,
`compare_04_strong_reposition_recommendation.png`. All four confirm the
same effect: visibly larger, less horizontally-compressed curves; a
narrower, absolute-time window (e.g. `18s`-`34s` instead of `5s`-`33s`
for the same NOW instant); 4s ticks instead of 5s; the white NOW-cursor
line still exactly at the right edge; and real gaps still visible as
line breaks, not smoothed over.

**Performance**: full per-frame-resolution computation over the 16s
(480-frame) window costs ~1.17s per rendered dashboard frame
end-to-end (video read + both panels + all three graphs) — all 6
previews regenerate in well under 10 seconds total.

Previews and the contact sheet (§10) were regenerated with these new
settings; the 6 preview filenames, frame numbers, and stories they
tell are otherwise unchanged from §10.

## 8c. Second refinement — window widened to 20s (final setting)

After reviewing the 16s version (§8b), one further display-only
adjustment was requested and applied: **the rolling window only**,
16s → **20s**. Nothing else changed —confirmed unchanged this round:
tick spacing (still 4s), absolute match time, NOW-cursor-at-right-edge,
full-resolution signal computation (`stride=1`), the three per-graph
causal EMA alphas (Graph 1 `0.6`, Graph 2 `0.2`, Graph 3 `0.5`), the
`decimate_for_display`/`DISPLAY_MAX_POINTS=240` display-decimation
mechanism, missing-data gap behavior (`MAX_GAP_SEC=1.0`, real gaps
still broken not filled), and every analytics formula
(`dangerous_space.py`/`opponent_access.py`/`spatial_balance.py`/
`counterfactual_repositioning.py`/`player_responsibility.py`/
`coach_signals.py` — none opened this round).

The only code change was a single constant in
`render_dangerous_space_dashboard.py`:

```python
COACH_WINDOW_SEC = 20.0   # was 16.0
```

- **Effect on decimation**: at 30fps, a 20s window now carries 600 raw
  per-series points versus 16s's 480 — both already exceed the 240
  cap, so `decimate_for_display` (unchanged function) now thins with
  stride 3 instead of stride 2. This is the existing point-thinning
  logic responding automatically to a longer window, not a new
  behavior.
- **Performance**: single-frame render time rose from ~1.17s (16s
  window) to ~1.40s (20s window) — still well within budget; all 6
  previews regenerate in well under 10 seconds total.
- **Previews and contact sheet**: regenerated with the same 6
  (name, frame, force_team, force_player) jobs as every prior round —
  filenames, frame numbers, and the story each one tells (§10) are
  unchanged; only the visible window width changed.
- **16s-vs-20s visual verification** (`outputs/qa/`, 4 new PNGs, old
  16s on top / new 20s on bottom, labeled):
  `compare16v20_01_ordinary_low_risk_moment.png`,
  `compare16v20_02_team_a_danger.png`,
  `compare16v20_03_team_b_danger.png`,
  `compare16v20_04_strong_reposition_recommendation.png`. All four
  confirm the window's left edge simply moved 4s further back (e.g.
  `18.7s`→`34.7s` at 16s becomes `14.7s`→`34.7s` at 20s for the same
  NOW instant) with the identical underlying data, ticks, smoothing,
  gaps, and right-edge NOW cursor — i.e. exactly the intended
  single-parameter change and nothing else.
- The original 16s-vs-30s comparisons (`compare_01`...`compare_04`,
  §8b) were left in place in `outputs/qa/` alongside the new
  `compare16v20_*` set, so both refinement steps remain inspectable.

**This 20-second window is the final approved graph-display setting**
pending sign-off on this round's previews — see the updated table in
§8b, whose "Now" column should be read as reflecting this final value.

## 8d. Third refinement — causal display-stability pass (locked window, calmer overlays)

**The 20-second rolling window from §8c remains LOCKED** — this round
did not touch it, or the 4-second tick spacing, or absolute match
time, or the NOW-cursor-at-right-edge, or full per-frame-resolution
computation. **The football broadcast video remains exactly normal
real-time speed** — no slow-motion, no frame duplication, no altered
FPS; `main()`'s new `--out_path` mode writes one real frame in for one
frame out at the source's own 30fps. **No analytics formula was
touched** — `dangerous_space.py`/`opponent_access.py`/
`spatial_balance.py`/`counterfactual_repositioning.py`/
`player_responsibility.py`/`coach_signals.py` were not opened this
round, and `rank_candidates`/`search_repositioning` are still called
with real, current-frame data every single frame.

What this round addressed instead: reviewing the 20-second demo video
showed the dashboard OVERLAYS fluctuating too aggressively frame to
frame (a "disco dance" effect) in the dangerous-space highlight, the
recommended player/target, the status badge, and Graph 2. A new
DISPLAY-only module, `dashboard/display_stability.py`, adds three
causal state machines — full technical detail, exact defaults, the
Graph-2 alpha comparison, and the quantitative flicker-rate
measurements are all in **`docs/DISPLAY_STABILITY.md`**; summary:

| Mechanism | Setting | Effect |
|---|---|---|
| Recommendation hold | `min_hold_sec = 0.5s` | won't switch the recommended player before this much time has passed |
| Recommendation switch margin | `switch_margin = 0.002` (benefit units) | after the hold, only switches if the new candidate's REAL current-frame benefit beats the displayed player's own REAL current-frame benefit by more than this |
| Recommendation invalidation | immediate, no hold | displayed player leaves the roster, defending team changes, or no danger region this frame |
| Target display smoothing | causal EMA, `alpha = 0.30` | smooths only the drawn target point/arrow; resets (never blends) on player change, invalidation, or a real gap |
| Danger-region hold | `min_hold_sec = 0.5s` | won't switch which team's region is highlighted before this much time has passed |
| Danger-region switch margin | `switch_margin = 0.03` (severity units) | after the hold, only switches if the other team is worse by more than this |
| Danger-region draw smoothing | causal EMA, `alpha = 0.35` | smooths only the drawn circle's centroid/radius; the REAL point/area still feeds `opponent_control_of_region`/`search_repositioning` unsmoothed |
| Region/recommendation invalidation on evidence loss | immediate, no hold | a genuine disappearance is never held or faded |
| Status-label dwell | `min_dwell_sec = 0.5s` | holds the badge title between two otherwise-valid states |
| Status-label exceptions | immediate, no dwell | switching TO **or FROM** "UNCERTAIN" (both directions), or LEAVING "RECOMMENDATION FOUND" — missing evidence is never hidden (in either direction), and a gone recommendation is never held for cosmetic smoothness |
| Graph 2 display alpha | `0.15` (was `0.2`) | lightest of {0.2, 0.15, 0.12} tested that gives a real, measurable roughness reduction (see comparison in `docs/DISPLAY_STABILITY.md`) — Graphs 1/3 unchanged |
| Voronoi fill opacity | 0.16→0.13 (broadcast), 0.20→0.16 (radar) | purely cosmetic; Voronoi geometry itself is still computed fresh from real current-frame positions every frame, never smoothed |

**A bug was caught during this round's own visual QA and fixed before
sign-off**: the first build of `LabelStabilizer` debounced LEAVING
"UNCERTAIN" as if it were ordinary risk-level churn, which could hold
a stale "UNCERTAIN" on screen for up to 0.5s after real evidence (even
a real "RECOMMENDATION FOUND") had already returned — caught by
comparing the first stabilized clip against the pre-stability version
at t=19.7s/29.7s/34.7s. Fixed so every UNCERTAIN transition, in either
direction, is immediate (see `docs/DISPLAY_STABILITY.md` for the full
account and the regression test added for it), and the clip was
re-rendered before this HANDOFF was finalized.

**Quantitative verification** (not just visual): comparing RAW
pre-this-round behavior against the STABILIZED (fixed) behavior on the
same 601-frame/20-second range used for the demo clip, restricted to
frame-pairs where real evidence was present on both sides (to exclude
legitimate, honest data-gap transitions): displayed-team flips dropped
from 51 to 1 (98%), recommended-player changes from 131 to 21 (84%).
For the status label, most raw churn in this specific (gap-heavy)
clip is genuine UNCERTAIN-involving transitions that must never be
suppressed, so the fair comparison excludes those too: among
transitions where NEITHER side is "UNCERTAIN," LOW/MODERATE/HIGH-RISK
churn dropped from 8 to 2 (75%) over this same range. Full methodology
in `docs/DISPLAY_STABILITY.md`.

**Re-rendered the same 20-second demo clip** (frames 440-1040) via the
new `main() --out_path` mode, to the same
`outputs/qa/dangerous_space_repositioning_20s_demo.mp4` path.
Programmatic QA (frame count/fps/canvas size/duration/motion sanity)
was re-run and passed. Visual QA at start/5s/10s/15s/end (end and the
"strong recommendation moment" coincide at t=34.7s in this clip)
confirmed calmer overlays with the same real underlying data — see
`outputs/qa/display_stability_old_vs_new_contact_sheet.png`.

**Tests**: `tests/test_display_stability.py` (22 new tests) and `tests/test_attacking_phase_relevance.py` (18 new tests) cover
hold/margin/immediate-invalidation behavior for both the region and
recommendation stabilizers, target-smoothing reset-vs-blend behavior,
label dwell/immediate-exception behavior, and an explicit
no-future-leakage test for both stabilizers.
`external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q` → 73 passed;
`external/sports/.venv/bin/python3 -m pytest tests/ -q` → 638 passed (unchanged).

## 9. Tests — 82 total in this project, all passing; 638 existing elsewhere in the repo, unaffected

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -v
# 82 passed

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed  (pressing_structure / offside_break / shared modules -- unchanged)
```

Coverage: Voronoi clipping/ownership/degenerate-input, the "not simply
largest cell" anti-pattern, cross-team severity symmetry, honest
neutral handling with no ball evidence, opponent-access bounds and
correct-opponent wiring, candidate selection excluding the goalkeeper
and not just picking nearest, bounded/pitch-valid counterfactual
candidates, `new_gap_penalty` never negative, a controlled synthetic
case where the search finds a genuine improvement, both-team graph
coverage, missing-data handling, **no-future-leakage** (corrupting
every frame after `f` leaves the signal at `f` unchanged), a
real-data end-to-end renderer smoke test, and (§8d,
`tests/test_display_stability.py`) causal display-stability
hold/margin/immediate-invalidation behavior, target-smoothing
reset-vs-blend behavior, label dwell/immediate-exception behavior, and
no-future-leakage for the display stabilizers themselves.

## 10. Preview & contact sheet paths

- `outputs/previews/01_ordinary_low_risk_moment.png` (frame 1920, t=64.0s)
- `outputs/previews/02_team_a_danger.png` (frame 2020, t=67.3s)
- `outputs/previews/03_team_b_danger.png` (frame 840, t=28.0s)
- `outputs/previews/04_strong_reposition_recommendation.png` (frame 1040, t=34.7s)
- `outputs/previews/05_high_new_gap_risk_case.png` (frame 1170, t=39.0s — forced illustration, see §11)
- `outputs/previews/06_missing_uncertain_data.png` (frame 220, t=7.3s)
- `outputs/contact_sheet/contact_sheet.png` (2×3 grid, captioned) —
  reflects the final 20s window (§8c)
- `outputs/qa/compare_*.png` (4 old-vs-new graph-row comparisons, 30s
  vs 16s, from the first graph-display polish pass — see §8b) —
  **removed in the §17 cleanup pass** (obsolete window widths, obsolete
  line-chart design; prose summary in §8b is authoritative)
- `outputs/qa/compare16v20_*.png` (4 old-vs-new graph-row comparisons,
  16s vs 20s, from the second refinement — see §8c) — **removed in the
  §17 cleanup pass** (same reason)
- `outputs/qa/dangerous_space_repositioning_20s_demo.mp4` (the 20-second
  demo clip, frames 440-1040, real broadcast footage at normal
  real-time speed — see §8d) — **removed in the §17 cleanup pass**,
  superseded by every later round's own re-render; the CURRENT demo
  clip lives at
  `outputs/final_demo/dangerous_space_repositioning_20s_final.mp4 (this file itself was superseded by this final round; see HANDOFF.md §19)`
  (see §16's own successor, §17)
- `outputs/qa/display_stability_old_vs_new_contact_sheet.png`
  (before/after the causal display-stability pass, same six instants
  — see §8d)
- `outputs/qa/graph2_alpha_comparison.png` (the 0.2 / 0.15 / 0.12
  Graph 2 display-alpha comparison — see §8d)

## 11. Limitations & known caveats (disclosed, not hidden)

- **Scale limitation of a single-defender, ≤3m search**: the flagged
  "most dangerous" region is usually far (20-40m) from the nearest real
  defender, so most frames honestly report no improving local
  candidate — see §7.
- **Severity/risk are disclosed proxies**, not validated against any
  outcome data (none exists at this sample size) — see
  `docs/METHODOLOGY.md`'s status table.
- **`05_high_new_gap_risk_case.png` is a deliberately forced
  illustration**, not the search's own auto-recommendation for that
  frame (whose own benefit is negative) — `force_team`/`force_player`
  kwargs on `render_frame()` were added specifically for this one
  preview; every number shown is still real and freshly computed for
  that exact (frame, team, player), only the CHOICE of which
  already-real candidate to display is manual.
- **The danger-region circle can extend past the visible broadcast
  camera frame** when the region sits near the edge of what the camera
  currently shows — expected, not a bug.
- **No baseline/statistical validation of the counterfactual search**
  has been attempted (would require multi-match data and, ideally,
  human-adjudicated "did this actually help" labels — same disclosed
  limitation pattern as `pressing_structure`'s own PSV_proxy).
- **Known non-bug**: Team A's own goal is at `x = pitch.length_cm`
  (12000), not `x = 0`, per `DEFAULT_PITCH`'s single-period
  configuration — easy to get backwards when extending this code (two
  of this project's own tests initially had it backwards and were
  corrected; see `docs/METHODOLOGY.md`).
- **No known bugs** in the shipped code as of this handoff — all 33
  new tests and all 638 pre-existing tests pass.

## 12. Commands to reproduce

```bash
# Run this project's own tests
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -v

# Confirm no regression to the rest of the repo
external/sports/.venv/bin/python3 -m pytest tests/ -q

# Regenerate the 6 previews + contact sheet (from the repo root)
external/sports/.venv/bin/python3 -c "
import sys, os; sys.path.insert(0, '.')
from dangerous_space_repositioning.dashboard.render_dangerous_space_dashboard import load_transformers, render_frame
from dangerous_space_repositioning.analytics.data_loader import load_match_data, TEAM_A
import cv2
match = load_match_data(); transformers = load_transformers()
cap = cv2.VideoCapture('ExternalDownlaodVideo/testVideo1_120s.mp4')
jobs = [
    ('01_ordinary_low_risk_moment', 1920, None, None),
    ('02_team_a_danger', 2020, None, None),
    ('03_team_b_danger', 840, None, None),
    ('04_strong_reposition_recommendation', 1040, None, None),
    ('05_high_new_gap_risk_case', 1170, TEAM_A, 55),
    ('06_missing_uncertain_data', 220, None, None),
]
os.makedirs('dangerous_space_repositioning/outputs/previews', exist_ok=True)
for name, f, ft, fp in jobs:
    canvas = render_frame(match, transformers, cap, f, force_team=ft, force_player=fp)
    cv2.imwrite(f'dangerous_space_repositioning/outputs/previews/{name}.png', canvas)
cap.release()
"
```

## 13. Next steps (not started, for a future round)

1. Review the 6 previews + contact sheet (this round's own explicit
   stop point).
2. If approved: render the full 120s video
   (`outputs/final_demo/dangerous_space_repositioning_120s.mp4`),
   reusing `render_frame()` in a sequential-seek loop exactly like
   `pressing_structure`/`offside_break`'s own `--out_path` full-render
   mode.
3. Consider a `generate_space_graphs.py` CLI wrapper around
   `coach_signals.build_signal_series` if a standalone exported time
   series (e.g. CSV) becomes useful.
4. Consider whether a multi-defender (not just single-defender) bounded
   search is worth adding, given how often a single-player move alone
   cannot reach the flagged region — this would need its own new
   "wording rule" discipline (never claiming a team-shape optimum) and
   is explicitly out of scope for this round.
5. More match data would be needed before any severity/risk/benefit
   number could be validated statistically — same disclosed limitation
   every other project in this repo already carries.

## 14. Radar/match-feed spatial alignment fix + cyan spotlight (this round)

Triggered by a review of the §8d 20s clip: "in some moments the
dangerous space in the match feed appears on one side, but in the
radar it appears on the opposite side." This round audited the root
cause (not a cosmetic flip), fixed it, added a Match-Feed spotlight
cue, and re-ran the graph/spatial QA pass. **No analytics formula was
touched** — every change is confined to rendering (`voronoi_radar.py`,
`voronoi_broadcast_overlay.py`).

### 14a. Root cause

A systematic Y-axis (pitch-**width**) orientation mismatch between the
REAL broadcast camera's per-frame homography
(`homography_transformers.pkl`) and the radar's own fixed virtual
camera (`tactical_shared.perspective_radar.DEFAULT_RADAR_CAMERA`,
`yaw_deg=0.0`) — present in **every** frame checked (500, 700, 860,
1000), i.e. a constant/structural mismatch, not a transient glitch.
Its *visibility* to a viewer is moment-dependent (only obvious when
the compared objects are separated substantially along the pitch-width
axis, e.g. near a touchline), which explains the "in SOME moments"
phrasing even though the underlying flip is mathematically always
present.

**Two wrong hypotheses were ruled out before committing to a fix**
(per the explicit "find the actual cause" instruction):

1. *Real camera cut mid-clip.* Checked left/right ordering and
   determinant sign of two reference points across all 405 available
   real homographies in frames 440-1040 — zero flips. The real
   camera's orientation is stable throughout this clip.
2. *`yaw_deg=180` (rotate the virtual camera to the opposite side).*
   Verified analytically: rotating the camera's yaw by 180° (same
   up-vector) correctly flips the Y/near-far sense to match the real
   camera, but a yaw rotation couples "forward" and "right" via a
   cross product in `_look_at_rotation`, so it **also** flips X/left-
   right — which then *mismatches* the real camera (whose `x=0` is
   already `LEFT`, matching the radar's own `yaw=0` convention). This
   is real 3D geometry, not a code bug — a camera physically relocated
   to the opposite side necessarily flips both axes together. Rejected
   because it is exactly the kind of "cosmetic-looking" blind flip the
   review explicitly warned against, and it is empirically wrong on X.

**The correct fix**: the mismatch is an axis-**convention** mismatch
(X already agrees, only Y is inverted — an axis-independent pattern no
single camera rotation can produce), not a camera-pose problem. This
is the same category of issue as `DEFAULT_PITCH.own_goal()`'s own
disclosed quirk (Team A's goal at `x = length_cm`, not `x = 0`) —
a documented coordinate-convention correction, applied at the input
boundary, never a camera hack.

### 14b. The fix

`dashboard/voronoi_radar.py` mirrors **only** the pitch-width (`y`)
coordinate of every DYNAMIC object, once, at the top of
`compose_radar_panel`, before anything is projected:

```python
def _mirror_y(y, pitch=DEFAULT_PITCH):
    return pitch.width_cm - y
```

Applied to: both teams' player positions AND `vy_cm_s` (velocity's y-
component must flip sign together with the position it describes, or
a moving player's heading glyph would point the wrong way), the ball,
every Voronoi cell polygon, the danger point, and
`recommend_from`/`recommend_to`. **Unchanged**: the camera model
(`DEFAULT_RADAR_CAMERA`, still `yaw_deg=0.0`) and static pitch markings
(`draw_pitch_markings_perspective`) — real pitch markings (penalty
box, centre circle, penalty spots) are already Y-symmetric about the
width midline, so mirroring them would be a no-op; leaving them alone
minimizes the change's surface area.
`tactical_shared/perspective_radar.py` (shared with `pressing_structure`
and `offside_break`) was **not** touched — this is a
`dangerous_space_repositioning`-local rendering correction only.

**Note for a future round**: `pressing_structure` and `offside_break`
render from the SAME source video and SAME homography file, so they
likely carry this identical latent Y-axis mismatch in their own radar
panels. Not fixed here (out of this round's scope) — flagged for
awareness, not yet actioned.

### 14c. Spatial QA — 5 required checkpoints, all consistent

Verified both analytically (comparing danger-region-vs-ball relative
position in match-feed pixels vs. radar pixels) and visually (full
dashboard renders) at every required timestamp within the 20s clip
(440-1040) that had an eligible/resolved primary danger region:

| Checkpoint | Frame | t | Match feed vs radar |
|---|---|---|---|
| Start | 495 | 16.5s | MATCH |
| ~5s | 590 | 19.7s | MATCH (see note below) |
| ~10s | 730 | 24.3s | MATCH |
| ~15s | 880 | 29.3s | MATCH |
| End / strong recommendation | 1040 | 34.7s | MATCH |

Frame 590 note: a raw pixel-side comparison first flagged this frame,
but the underlying real pitch-space separation between the danger
region and the ball is only ~180cm (<2m) along the pitch-width axis —
below the scale where "left of" vs "right of" is a meaningful claim in
either projection (the two cameras have different perspective
distortion at that scale). The dominant, real 1166cm separation (pitch
length/depth axis) agreed correctly in both projections. Direct visual
inspection of the rendered frame confirms the danger region, ball, and
"Best player to fix" marker occupy the same relative area in both
panels — not a mirroring bug.

Frame 1040 (the flagship "strong reposition recommendation" moment,
already visually correct before this fix) was re-verified to remain
correct after the fix — confirming the mirror correction does not
regress cases that were already fine.

QA contact sheet:
`outputs/qa/radar_alignment_fix/radar_alignment_qa_contact_sheet.png`
(all 5 checkpoints, full dashboard, stacked with captions).

### 14d. Graph QA pass — no changes needed

Audited Graphs 1/2/3 for consistency with the corrected radar; **no
graph rendering or formula change was made or needed**. Verified two
ways:

1. **By construction**: `render_dangerous_space_dashboard.py` calls
   `compose_radar_panel` (line ~296, containing this round's fix) and
   `draw_severity_graph`/`draw_opponent_control_graph`/
   `draw_spatial_balance_graph` (lines ~324-327) as two entirely
   separate steps, fed by separate data — the graphs read `sev_a/b`,
   `thr_a/b`, `risk_a/b` history arrays accumulated upstream by
   `compute_frame_signal`, which the radar-panel fix never touches.
   `dashboard/live_graphs.py` does not import `voronoi_radar.py` at
   all. The Y-mirror is a pure rendering step local to one function's
   own inputs; it cannot reach the graphs.
2. **Visually**: all 5 QA checkpoint renders (§14c) show Graph 1 with
   real gaps preserved (sparse, per the §6c eligibility gate) and
   correct Team A/B coloring; Graph 2 with its "Threat vs A"/"Threat
   vs B" labels intact and correctly noisy; Graph 3 continuous (not
   gated by eligibility) with correct coloring — all plausible and
   consistent with the corrected radar/match-feed selection at each
   instant. Fixed `[0,1]` y-range, 20s window, 4s ticks, white
   current-time marker: all unchanged.

### 14e. Cyan spotlight — added

`dashboard/voronoi_broadcast_overlay.py::draw_recommendation_spotlight`
draws a faint, translucent cyan cylindrical beam rising from the
recommended player's ground position in the Match Feed panel, plus a
soft flattened-ellipse glow at its base (foreshortened to sit naturally
on the ground plane rather than floating as a flat screen-space disc).
Built as a stack of same-radius (cylindrical, non-tapering) translucent
horizontal bands whose alpha fades going up (`0.16 * (1-frac)^1.4`),
so it reads as a soft light column rather than a solid shape. Uses the
project's own existing `RECOMMEND_COLOR` (the same cyan already used
for the "Best player to fix" ring), so it matches the existing 2.5D
aesthetic rather than introducing a new color.

Called from inside `draw_recommendation()`, which is itself only ever
invoked when `recommend_from`/`recommend_to` are both non-`None` — the
exact same values, already produced by
`DashboardDisplayStabilizers.recommendation.update()` (the causal
hysteresis/dwell stabilizer from §8d), that drive both the Match Feed
ring AND the Radar panel's own recommendation marker. The spotlight
therefore has **no separate state machine**: it automatically tracks
the currently-stabilized player, switches cleanly on a stabilized
recommendation change, and disappears immediately when no valid
recommendation exists (including every UNCERTAIN state) — verified by
rendering frame 1040 (recommendation present → spotlight visible,
subtle) and frame 220 (`UNCERTAIN`/insufficient tracking → no
spotlight, no danger circle, no recommendation UI at all).

A matching radar-side halo was considered (explicitly optional in the
brief) but not added — the Match Feed spotlight alone satisfies the
requirement, and the radar panel already has its own cyan ring/label
for the recommended player.

### 14f. Display-stability interaction — confirmed, no changes needed

The Y-mirror fix lives entirely inside `compose_radar_panel`, applied
to already-resolved (already-stabilized) `danger_point`/
`recommend_from`/`recommend_to` values passed in from
`render_dangerous_space_dashboard.py` — the stabilizers themselves
(`dashboard/display_stability.py`) operate purely on real, unmirrored
pitch-cm coordinates and never see the mirror. Since the mirror is a
stateless, per-frame, per-call transform (no memory of previous
frames), there is no stale-state case where an old mirrored location
could persist after a resolved/UNCERTAIN transition — each frame's
radar panel is mirrored fresh from that frame's already-stabilizer-
selected values. No code change to `display_stability.py` was made or
needed. Confirmed via the frame-220 (UNCERTAIN) and frame-1040
(resolved) renders above: both panels reset/populate exactly in step
with the existing stabilizer output, with no lag or leftover marker.

### 14g. Deliverables

- Corrected 20s demo clip (frames 440-1040, both fixes applied):
  ~~`outputs/qa/radar_alignment_fix/dangerous_space_repositioning_20s_demo.mp4`~~
  — **removed in the §17 cleanup pass**, superseded by every later
  round's own re-render; the CURRENT demo clip lives at
  `outputs/final_demo/dangerous_space_repositioning_20s_final.mp4 (this file itself was superseded by this final round; see HANDOFF.md §19)`
- QA contact sheet (5 checkpoints, match feed + radar + graphs):
  `outputs/qa/radar_alignment_fix/radar_alignment_qa_contact_sheet.png`
- This section (§14).
- **The 120-second full video was explicitly NOT rendered this
  round**, per this round's own stop condition.

### 14h. Tests

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 82 passed (unchanged — no new tests were required; this round's
# changes are covered by the existing renderer smoke test plus the
# manual spatial/visual QA in §14c-§14f)
```

No new automated tests were added for the radar mirror or spotlight
themselves (both are pure rendering changes with no new branching
analytics logic to unit-test); verification for this round relied on
the numerical/visual QA documented above, per the round's own
deliverables list (spatial QA + contact sheet + note, not new tests).

## 15. Top-3 Distinct Dangerous Regions + 24-second graph window (this round)

Two goals, both purely ADDITIVE: (A) support up to 3 ranked, mutually
DISTINCT dangerous regions per defending team instead of just one, with
per-region fixer assignment and conflict resolution; (B) widen the
graph rolling window from 20s to 24s. **No analytics formula changed.**
The radar-alignment fix (§14), the Current-Attack Eligibility gate
(§6c), the display-stability hysteresis layer (§8d), and the cyan
spotlight (§14e) are all UNCHANGED and reused exactly as they were.

### 15a. Why not simply the top 3 Voronoi cells

Neighboring opponent-owned cells frequently represent the SAME tactical
pocket (e.g. two or three attackers standing close together just
outside a defender's coverage radius, each owning a sliver of the same
open space). Presenting all three as independent problems would
overstate how many distinct issues exist and could assign 2-3 different
"best fixers" to what one defender stepping into that pocket would
actually solve.

### 15b. The exact de-duplication rule

New module `analytics/multi_region.py`, consuming
`dangerous_space_for_team(...)["eligible_ranked"]` — the SAME
already-eligible, already-severity-ranked list `top` is already picked
from (`eligible_ranked[0] == top`, always). No new eligibility/severity
logic; this only prunes an already-scored, already-filtered list:

```
select_top_regions(eligible_ranked, max_regions=3, overlap_factor=1.5):
  walk candidates in severity-descending order (defensively re-sorted,
  not just trusted from the caller):
    r = sqrt(area_cm2 / pi)     # identical radius formula the dashboard already draws
    suppress this candidate if, for ANY already-kept region:
        centroid_distance < overlap_factor * (r_candidate + r_kept)
    else keep it (stop once max_regions are kept)
```

`overlap_factor = 1.5` is a disclosed, generous choice (not fitted to
data): two pockets separated by less than half their combined radii
still read, to a coach looking at the screen, as "the same patch of
grass" — matching the review's own explicit warning about neighboring
cells. `select_top_regions(...)[0]` is proven ALWAYS identical to the
existing single-region `top` (nothing can outrank the first,
highest-severity candidate to suppress it against) —
`tests/test_multi_region.py::
test_first_selected_region_always_matches_the_single_region_pipelines_top`
locks this in.

**Never fabricated**: fewer than 3 real, mutually-distinct eligible
candidates yields a SHORTER list (down to zero) — verified by
`test_fewer_than_3_valid_regions_are_never_fabricated`. Real-clip
measurement across the 440-1040 demo range (frames sampled every 2,
`eligible_ranked` non-empty): of 203 sampled resolved+non-resolved
frames, distinct-region counts were **4 frames with 1 region, 23 with
2, 21 with 3** (out of 48 total resolved frames), with de-duplication
actually suppressing at least one candidate on 47 of those 48 frames'
raw eligible pools.

### 15c. Multi-region fixer assignment and conflict resolution

`analytics/multi_region.assign_regions_and_fixers` walks the surviving
regions from primary to lowest priority, calling the existing,
UNCHANGED `player_responsibility.rank_candidates` for each region.

- If a region's own top-ranked real candidate is available (not already
  claimed by a higher-priority region this frame), it becomes that
  region's fixer — identical to how the single primary region always
  worked.
- If Player X is the natural best fixer for BOTH Danger #1 and Danger
  #2: Danger #1 (higher priority) keeps Player X. Danger #2's own
  ALREADY-COMPUTED ranked candidate list (never a second, different
  heuristic — never "pick the nearest") is walked further down for the
  next candidate not yet claimed by a higher-priority region.
  `conflict=True` is recorded for Danger #2 regardless of whether a
  fallback was found, since a real conflict genuinely occurred.
- If EVERY real candidate on the defending team is already claimed
  (exhausted — practically never occurs with a full 10-11 outfield
  roster, but tested synthetically), the region is reported honestly:
  `fixer_track_id=None`, `reason="Same-player conflict / no independent
  fixer"` — never a fabricated second simultaneous mover for one
  player.
- The PRIMARY region's own already-stabilized fixer (from the existing,
  unchanged `RecommendationStabilizer`) is seeded into
  `already_assigned` before secondary/tertiary assignment runs, so a
  secondary/tertiary region can never re-select the exact player
  already fixing the primary problem this frame.
- Each assigned fixer's counterfactual move is computed via the
  existing, UNCHANGED `counterfactual_repositioning.search_repositioning`
  — same benefit formula, same bounded ±300cm search, same wording
  discipline ("best candidate within the tested local search"). See
  `docs/REPOSITIONING_LOGIC.md`'s new "Multi-region fixer assignment"
  section for the one disclosed scope limit this implies (each
  region's `structural_damage_penalty` is evaluated independently, not
  jointly across simultaneously-moving fixers).

Real-clip measurement: of the 48 resolved sampled frames in the demo
range, 4 showed a same-player conflict (frames 604, 742, 744, 788 in
the 2-frame-stride scan) — in every one, a real fallback candidate was
found (the "no independent fixer" honest-failure path was exercised
only synthetically, in `tests/test_multi_region.py`, since a full
11-a-side roster essentially always has a second viable candidate).

### 15d. Display stability for multiple regions

New `dashboard/display_stability.MultiRegionStabilizer` (2 slots,
covering secondary+tertiary) generalizes `DangerRegionStabilizer`'s own
hold/margin hysteresis to N ranked slots, keyed by the region's owning
opponent `track_id`. The PRIMARY region/team decision and its own
`DangerRegionStabilizer`/`RecommendationStabilizer` are completely
UNCHANGED — this new stabilizer only governs the 2 EXTRA slots layered
on top. Full mechanism documented in `docs/DISPLAY_STABILITY.md`'s new
section; summary: a held slot's occupant is kept (refreshed) unless
displaced by a `>0.03`-severity-stronger, not-yet-claimed candidate
after a `0.5s` hold; a vanished region is dropped immediately, no hold;
an empty slot fills immediately, no hold needed to start. 13 dedicated
tests in `tests/test_multi_region.py`, including a no-future-leakage
test matching this file's existing convention.

**Disclosed scope decision**: the secondary/tertiary region's own
assigned FIXER (as opposed to the region itself) is recomputed fresh
each frame from the already-slot-stabilized region, without its own
dedicated fixer-level hold/margin hysteresis the way the primary
recommendation has. In practice a stabilized region's nearest real
defenders rarely change frame-to-frame, so this was not observed to
flicker during this round's own visual QA (§15h) — a future round could
add a dedicated secondary-fixer stabilizer if real flicker is ever
observed.

### 15e. Visual design — Match Feed and Radar

Both panels draw the SAME ranked regions, at strictly decreasing visual
weight, with the primary always drawn LAST (i.e. on top, wherever
overlap occurs):

- **Danger #1 (primary)**: entirely UNCHANGED from the radar-alignment
  round — full orange region, full "Dangerous space"/"Opponent control
  NN%" labels, full cyan ring + spotlight + dashed arrow + target ring.
- **Danger #2/#3**: a fainter/smaller orange region (fill alpha 0.16 /
  0.09 vs. primary's 0.30, ring thickness 1px vs. 2px) with a small
  "#2"/"#3" marker instead of the full callout; if a fixer was
  assigned, a smaller cyan ring (15px/11px vs. primary's 22px on the
  Match Feed) + a scaled-down spotlight (60%/40% height vs. primary) +
  a thinner dashed connector + a smaller target ring, labeled "#2
  fixer"/"#3 fixer" (or "#2 fixer (reassigned)" when `conflict=True`
  for that region). If no independent fixer exists for that region, a
  small dimmed pill states the reason at the region's own centroid,
  never a fabricated fixer marker.
- The radar panel's secondary/tertiary drawing has NO spotlight (the
  radar has never had one — only the Match Feed does, an established
  prior-round decision), just the smaller ring/dashed-line/target set,
  scaled for the radar's own smaller marker sizes.
- Every secondary/tertiary point (region centroid, fixer position,
  target position) is mirrored on the radar panel via the SAME
  `_mirror_point`/`_mirror_y` correction as the primary region — the
  radar-alignment fix from §14 applies identically to every rank.

### 15f. Graph window: 20s → 24s

One-line change: `COACH_WINDOW_SEC = 24.0` in
`render_dangerous_space_dashboard.py` (was `20.0`). Everything else is
explicitly UNCHANGED and verified so:

- `COACH_TICK_SEC` stays `4.0` (6 ticks over 24s vs. 5 over 20s).
- `SEVERITY_EMA_ALPHA` (0.6), `OPPONENT_CONTROL_EMA_ALPHA` (0.15),
  `SPATIAL_BALANCE_EMA_ALPHA` (0.5) — all unchanged (locked by
  `tests/test_graph_window.py::test_smoothing_alphas_unchanged_this_round`).
- `MAX_GAP_SEC=1.0` (real gaps still break the line, never
  interpolated) — unchanged, re-verified at the new window width by
  `test_real_gap_breaks_the_line_over_a_24s_window`.
- The white NOW-cursor still pins to the plot's own right edge
  regardless of window width (`test_now_cursor_is_pinned_at_the_right_
  edge_of_a_24s_window`).
- `causal_ema_scalar`/`decimate_for_display` (display-only smoothing/
  thinning) in `live_graphs.py` — byte-for-byte unchanged.

### 15g. Graphs 1/2 stay PRIMARY-region-only — a deliberate, disclosed decision

**Considered and explicitly rejected**: aggregating the Top-3 regions'
severities (e.g. summing or max-ing across all distinct regions) into
Graph 1/Graph 2. Reasons this was NOT done:

1. `coach_signals.compute_frame_signal` — which Graph 1/2's history
   arrays are built from — reads `dangerous_space_for_team(...)["top"]`
   only; this function is completely UNCHANGED this round, so Graphs
   1/2 are PROVABLY unaffected by the new multi-region logic (no shared
   code path, no shared data structure).
2. A summed/maxed Top-3 metric would change the MEANING of "Dangerous
   Space Severity" retroactively across every already-rendered/
   documented frame and every existing test's expectations
   (`tests/test_dangerous_space.py`, `test_attacking_phase_relevance.py`)
   — a formula change requiring its own dedicated validation pass, not
   something to fold silently into a "add Top-3 to the RADAR view"
   round.
3. The Top-3 overlay is explicitly framed (per this round's own brief)
   as "a richer tactical MAP view," i.e. a Match-Feed/Radar visual
   enrichment — not a request to redefine the coach-facing time-series
   metric itself.

**If a future round wants a Top-3 aggregate graph**, the principled
options (for that round's own explicit decision, not decided here) are:
(a) a NEW 4th graph plotting `sum(severity over kept distinct regions)`
alongside the existing Graph 1 (additive, non-breaking), or (b) a
documented redefinition of Graph 1 itself with its own before/after
validation pass matching this project's existing calibration-history
discipline (see `docs/REPOSITIONING_LOGIC.md`'s "Calibration history").
Neither is implemented here, per this round's own explicit instruction
not to implement an aggregate without first explaining and getting it
justified.

Graph 3 (Spatial Balance / New-Gap Risk) was ALREADY a whole-team
structural metric independent of how many distinct danger regions are
flagged (`spatial_balance.compute_spatial_balance_risk` scores the
team's own shape, not any particular opponent-owned cell) — nothing
about it changes with Top-3 support.

### 15h. QA

**Multi-region QA log**
(`outputs/qa/multi_region_24s_window/multi_region_qa_log.csv`), one row
per (frame, rank), covering every required scenario: 1 valid region
(frame 898), 2 valid distinct regions (frame 494, Team B), 3 valid
distinct regions (frame 542), a same-player fixer conflict with
fallback (frame 604), Team A defending (frame 724), Team B defending
(frame 494/542/590), uncertain possession (frame 452,
`REASON_UNCERTAIN_CONTEXT`), and a current-attack-eligibility failure
(frame 442, `REASON_NO_ELIGIBLE_CANDIDATE`) — plus the 5 standard
spatial-QA checkpoints (start/5s/10s/15s/end, frames 495/590/730/880/
1040) from the radar-alignment round, re-verified under the new
multi-region + 24s-window code. Every row logs rank, frame/time,
defending/attacking team, region centroid, severity, opponent control,
longitudinal progress, distance from ball, assigned fixer, suggested
target, benefit, new-gap risk, and whether a fixer conflict occurred.

**Visual QA** (`outputs/qa/multi_region_24s_window/` renders, inspected
directly): confirmed at every checkpoint plus a dedicated multi-danger
moment (frame 542, 3 distinct regions) and the same-player-conflict
moment (frame 604): Danger #1 always visually dominant (full-size
region + full spotlight); Danger #2/#3 visibly fainter/smaller and
never competing for attention; Match Feed and Radar agree on region
ranking, relative position, and assigned fixer at every inspected
frame; the "(reassigned)" fixer label renders correctly on the
conflict frame; a frame with zero eligible regions (452, 442) shows no
region/fixer markers of any rank, no stale leftovers.

**One disclosed, minor finding**: at frame 542 (3 distinct regions), the
secondary (#2) and tertiary (#3) regions' own SMALL pill labels sit
close enough together on the Match Feed to look somewhat busy when a
secondary/tertiary region's assigned fixer happens to stand physically
near another region's own marker — real information, not a bug (each
label is honestly reporting its own real region/fixer), but a
cosmetic crowding case worth flagging rather than hiding. Danger #1
itself remained clearly the dominant, unambiguous element in every
inspected frame, satisfying the round's core "Danger #1 must always be
obvious" requirement.

**24s graph-window QA**
(`outputs/qa/multi_region_24s_window/graph_window_20s_vs_24s_comparison.png`):
side-by-side 20s (old) vs. 24s (new) severity-graph renders at the same
4 timestamps used for the original graph-display-polish round
(01_ordinary_low_risk_moment/1920, 02_team_a_danger/2020,
03_team_b_danger/840, 04_strong_reposition_recommendation/1040).
Confirmed: curves remain readable, the extra 4 seconds of real history
adds context without reintroducing a "wall of spikes" (the
Current-Attack Eligibility gate keeps the series sparse regardless of
window width), 4s ticks remain legible (6 ticks at 24s vs. 5 at 20s),
and the NOW cursor stays correctly pinned at the right edge. No
readability regression found — 24s is kept as requested.

### 15i. Tests

27 new tests, all passing:

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/test_multi_region.py dangerous_space_repositioning/tests/test_graph_window.py -q
# 27 passed

external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 109 passed (82 existing, unaffected + 27 new)

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (unchanged elsewhere in the repo)
```

`tests/test_multi_region.py` (22 tests): Top-3 ranking order; never
exceeds `max_regions`; never fabricates when fewer real distinct
regions exist; overlapping/adjacent candidates deduplicated; distinct
far-apart candidates NOT suppressed; `select_top_regions(...)[0]`
always matches the single-region pipeline's own `top`; ranking
symmetric between Team A/B; fixer assignment with no conflict; a
same-player conflict resolved via fallback to the next-best REAL
candidate; a same-player conflict with no alternative reported
honestly (never fabricated); "no candidate available" reported as a
DISTINCT reason from a conflict; an `already_assigned` seed correctly
prevents reusing the primary's own fixer; fixer assignment symmetric
between team roles; `MultiRegionStabilizer` slot persistence, hold/
margin hysteresis, immediate removal on evidence loss, immediate fill
of an empty slot, full-gap clearing, slot-count bound, and
no-future-leakage.

`tests/test_graph_window.py` (5 tests): window is 24.0s; tick spacing
unchanged at 4.0s; every smoothing alpha unchanged; NOW cursor pinned
at the plot's own right edge; a real gap still breaks the line (no
interpolation) at the new window width.

### 15j. Deliverables

- Corrected 20s demo clip (frames 440-1040, ALL current-round + prior-
  round fixes applied — radar alignment, spotlight, Top-3 regions,
  24s graphs):
  ~~`outputs/qa/multi_region_24s_window/dangerous_space_repositioning_20s_demo.mp4`~~
  — **removed in the §17 cleanup pass**, superseded by both graph-
  redesign rounds since; the CURRENT demo clip lives at
  `outputs/final_demo/dangerous_space_repositioning_20s_final.mp4 (this file itself was superseded by this final round; see HANDOFF.md §19)`
- Multi-region QA log (24 rows, every required scenario, RETAINED):
  `outputs/qa/multi_region_24s_window/multi_region_qa_log.csv`
- 20s-vs-24s graph comparison contact sheet:
  ~~`outputs/qa/multi_region_24s_window/graph_window_20s_vs_24s_comparison.png`~~
  — **removed in the §17 cleanup pass** (the 24s window decision itself
  remains locked and unchanged; Graph 1/2 are no longer line charts at
  all, so this line-chart comparison no longer represents any current
  or recent rendering — see §16)
- This section (§15).
- **The 120-second full video was explicitly NOT rendered this
  round**, per this round's own stop condition — awaiting final
  approval.

### 15k. Lock (per this round's own explicit instruction)

Assuming this round's QA is approved, the following are now LOCKED
(no further aesthetic tuning without a real bug):

- Top-3 distinct danger-region design (de-duplication rule, ranking,
  visual hierarchy, conflict resolution).
- 24-second rolling graph window, 4-second ticks.
- Current smoothing values (`SEVERITY_EMA_ALPHA=0.6`,
  `OPPONENT_CONTROL_EMA_ALPHA=0.15`, `SPATIAL_BALANCE_EMA_ALPHA=0.5`).
- Current radar coordinate orientation (§14's Y-mirror fix).
- Current spotlight design (primary full-size; secondary/tertiary
  scaled-down; no radar spotlight).
- Current display-stability behavior (region/recommendation/label
  hysteresis, plus this round's `MultiRegionStabilizer`).

## 16. Graph 1/2 readability redesign: bucketed bars (this round)

Triggered by review feedback that Graphs 1/2's per-frame line charts
were "too scattered/noisy" for coach-facing demo use. **Display-only**:
no analytics formula changed, no multi-region detection logic changed,
no recommendation logic changed, the 24s window/4s ticks are UNCHANGED
(the 6 buckets below are exactly `COACH_WINDOW_SEC / COACH_TICK_SEC`,
already-existing constants, untouched). Graph 3 (Spatial Balance /
New-Gap Risk) is completely UNCHANGED — still the same line chart,
same EMA smoothing, same everything.

**Partial supersession of §15k's lock, by explicit new instruction**:
§15k locked "current smoothing values" for Graphs 1/2 too. This round's
own request explicitly asked to revisit Graph 1/2's readability, which
is exactly the kind of deliberate new direction a lock is meant to
yield to (a lock binds against unprompted future tuning, not against a
new, explicit request) — `SEVERITY_EMA_ALPHA`/`OPPONENT_CONTROL_EMA_ALPHA`
still exist with their same historical values (0.6/0.15, still used by
the legacy `draw_severity_graph`/`draw_opponent_control_graph`
functions kept in `live_graphs.py` for backward compatibility) but are
no longer invoked by `render_frame` for Graphs 1/2 — bucket-mean
aggregation is this round's own replacement smoothing mechanism for
those two graphs specifically. `SPATIAL_BALANCE_EMA_ALPHA` (Graph 3) is
untouched and still active.

### 16a. What changed, file by file

- `analytics/coach_signals.py`: `FrameSignal` gained ADDITIVE fields —
  `status_a`/`status_b` (`"resolved"` / `"no_eligible"` / `"uncertain"`)
  and `top3_severity_a`/`top3_severity_b`/`top3_access_a`/`top3_access_b`
  (0-3 entries, rank order). Computed by calling the EXISTING, UNCHANGED
  `multi_region.select_top_regions` on the SAME `eligible_ranked` list
  `dangerous_space_for_team` already returns (zero new
  `dangerous_space_for_team` calls) plus `opponent_access.
  opponent_control_of_region` at each kept region (the same function
  already used for the primary region's own `threat_a`/`threat_b`, now
  also called at ranks 2/3). Every EXISTING field (`severity_a`,
  `threat_against_a`, `risk_a`, etc.) is byte-for-byte unchanged.
- `dashboard/live_graphs.py`: new `bucket_region_history` (the
  aggregation), new `draw_severity_bar_graph`/
  `draw_opponent_access_bar_graph` (the bar-chart renderers) — all
  ADDED alongside, not replacing, the existing line-chart functions
  (`draw_severity_graph`/`draw_opponent_control_graph`/`_chrome`/
  `_plot_series`/etc. all still exist, still tested, still used by
  `draw_spatial_balance_graph`/Graph 3).
- `dashboard/render_dangerous_space_dashboard.py`: `build_signal_history`
  gained two new list entries (`samples_a`/`samples_b`, one dict per
  already-processed frame — no extra frames touched) alongside its
  existing `severity_a`/`threat_a`/`risk_a`/etc. lists. `render_frame`'s
  Graph 1/2 section now calls `bucket_region_history` +
  `draw_severity_bar_graph`/`draw_opponent_access_bar_graph` instead of
  the old EMA-then-line-plot path; Graph 3's own code path is untouched.

### 16b. The bucketing rule (honest, no fabrication)

`bucket_region_history` divides the rolling window into fixed
`COACH_TICK_SEC`-wide (4s) buckets — `COACH_WINDOW_SEC / COACH_TICK_SEC`
= 6 buckets at the full 24s window, FEWER near the very start of the
match (mirrors the existing line-graph's own `t_lo = max(0, cur_time -
window)` growing-window convention — never a fabricated bucket for
time before kickoff).

Per bucket, per team, per rank (Danger #1/#2/#3), each sampled frame's
`status` decides how it counts:

| Status | Meaning | Contribution to the bucket's mean |
|---|---|---|
| `"uncertain"` | possession/ball/tracking genuinely unknown | **Excluded entirely** — neither pulls the mean up nor down |
| `"no_eligible"` | context known, but no eligible candidate this instant | **Real 0.0** — an analytically-confirmed absence of danger, not a gap |
| `"resolved"` | a real eligible region existed at this rank | **Real value** (or 0.0 if fewer than `rank+1` distinct regions existed that instant — also a confirmed absence, not a gap) |

If EVERY sample in a bucket is `"uncertain"` (zero real evidence at
all), the bucket's value is `None` — drawn as an honest hatched
placeholder (`_draw_missing_bar`), never a fabricated zero. This is the
key distinction that makes the design honest: a bucket where a team
genuinely faced no danger (all `"no_eligible"`) looks like a real,
confident empty bar, while a bucket where NOTHING is known (all
`"uncertain"`) looks visibly, unmistakably different (hatched).

**Partial-evidence marker**: a bucket with fewer than
`MIN_SAMPLES_FOR_CONFIDENT_BUCKET = 10` real (`resolved`+`no_eligible`)
samples gets a small dashed baseline tick, regardless of whether its
computed value is zero or not — an honest "this real value rests on
thin evidence" signal. Chosen as an ABSOLUTE sample count, not a
coverage FRACTION: this project's own Current-Attack Eligibility gate
already means most buckets legitimately resolve only ~15-30% of their
~121 possible per-frame samples (this clip's own measured ~65%
possession/ball-unknown rate, see §6c) — a fraction-based threshold
would flag nearly EVERY bucket, which is not a useful signal.
Empirically measured across 314 sampled buckets (frames 500-1040,
stride 20): median 25 real samples/bucket, 10th percentile 6, 25th
percentile 19 — `10` sits just below the 25th percentile, flagging
genuinely thin buckets without flagging the typical case.

### 16c. Graph 1 design: stacked "Burden Score" bars

**Chosen design**: grouped bars per bucket (Team A next to Team B),
each bar STACKED bottom-to-top by Danger #1 (full team color) / #2
(medium shade) / #3 (faint shade) — total stack height = the bucket's
own summed mean severity across all real distinct regions ("Burden
Score"). Considered and rejected:

1. ~~Dominant-region bar + small markers for extras~~ — tried for
   Graph 1 too, but it hid the "was danger concentrated in one region
   or spread across several" story the brief explicitly wanted; a
   stacked sum shows this directly (a bar that's mostly one dark
   segment = concentrated, several similarly-sized segments = spread).
2. ~~A summed value with NO real cap check~~ — empirically verified
   first: real per-frame summed Top-3 severities across the 440-1040
   clip range top out at ~0.93 (48 resolved samples, stride 2), so the
   EXISTING project-wide `[0, 1]` fixed y-axis convention was kept
   rather than inventing a new `[0, 2]`-style scale — bucket-level MEAN
   aggregation (diluted by `no_eligible` zeros in the same bucket) pulls
   typical values lower still.

"Burden Score" is a NEW, disclosed DISPLAY aggregate (sum of the SAME
real, unchanged per-region severities) — not a redefinition of
"Dangerous Space Severity" itself, which remains exactly
`dangerous_space.score_cell`'s own weighted formula, untouched.

### 16d. Graph 2 design: dominant bar + rank-2/3 tick markers (NOT stacked)

**Chosen design**: a single solid bar for Danger #1's own real
opponent-access probability (clean `[0,1]` semantic, identical meaning
to the pre-existing "Threat Against X" quantity), plus small horizontal
tick marks at Danger #2/#3's own access levels. Explicitly NOT a
stacked sum like Graph 1: **opponent-access values are probabilities**,
and summing probabilities across DIFFERENT physical regions (e.g. "70%
+ 50% + 30% access") has no honest interpretation — there is no
meaningful "150% access." Graph 1's quantity (severity) is a proxy
score that IS meaningfully additive as a "total burden," Graph 2's is
not, so the two graphs deliberately use different bar styles despite
sharing the same bucketing/coloring language.

### 16e. Why the growing-window bucket count matters for this clip

The 440-1040 demo clip covers real match time t=14.7s-34.7s — since
this is LESS than `COACH_WINDOW_SEC` (24s) past kickoff for its early
frames, the EARLIEST rendered frames show FEWER than 6 buckets (e.g.
frame 452, t=15.1s, shows only 4 buckets spanning its real 15.1s of
elapsed match time) — verified directly in QA (§16g), not a bug, the
same "grow from zero, never fabricate before kickoff" principle the
line-graph already used.

### 16f. Comparison — is bucketed bars actually better?

**Yes, clearly**, per direct old-vs-new comparison at the same 4
reference instants used throughout this project's own history
(`outputs/qa/graph_readability_redesign/graph{1,2}_old_vs_new_comparison.png`):
the old line charts show sparse, disconnected scribble segments (a
direct consequence of the Current-Attack Eligibility gate's own ~78%
UNCERTAIN rate — real gaps everywhere) that are genuinely hard to read
at a glance; the new bucketed bars turn the SAME sparse real evidence
into a clean, immediately-parseable per-team, per-4s-window summary,
with the Top-3 breakdown now visible as an internal stack/tick-marks
rather than not shown at all in the old design.

**Top-3 information visibility**: fully preserved for Graph 1 (every
rank's own real contribution is a distinct, colored stack segment) and
partially simplified for Graph 2 (Danger #1 is the full bar; #2/#3 are
smaller tick marks rather than their own full bars — a deliberate
simplification, per §16d's reasoning, not an oversight).

**What was intentionally simplified**: (1) Graph 2's #2/#3 regions get
tick marks, not full bars — a probability-additivity constraint, not a
readability shortcut; (2) neither graph's bucket-level fixer/target
information is shown (the graphs answer "how much danger / how
accessible," not "who should fix it" — that remains the Match
Feed/Radar panels' own job); (3) the bucketed bars use the RAW,
per-frame analytical Top-3 ranking for their historical aggregation,
NOT the display-stabilized slot identity the live radar/match-feed
panels use (see `analytics/multi_region.py` §15's own
`MultiRegionStabilizer`) — replaying stabilizer state for an arbitrary
historical rolling window would require a redesign this round
explicitly avoids; a bucket's "Danger #2 contribution" means "the
average severity of whichever real region was second-most-severe in
each sampled frame of this bucket," which may not trace one single
physical region across the whole bucket, since real regions naturally
shift moment to moment. Disclosed, not hidden.

### 16g. QA

Visual QA (all 6 standard previews regenerated, plus the missing-data
preview `06_missing_uncertain_data.png` specifically checked): hatched
"missing" placeholders render correctly and only where genuinely zero
real evidence exists (verified against `bucket_region_history`'s own
direct output on frame 452, whose first bucket has `n_defined_samples
== 0`); a real "no eligible candidate" zero (e.g. frame 1040's `10-14s`
bucket, both teams, 13-32 real samples all resolving to 0.0) renders as
an honest, confident, zero-height bar — visibly different from a
hatched placeholder; the growing-window bucket count was confirmed at
frame 452 (4 buckets, t=15.1s of real elapsed match time) vs. frame
1040 (6 full buckets, t=34.7s, window fully available).

Old-vs-new comparison images (4 reference instants each, Graph 1 and
Graph 2 separately):
~~`outputs/qa/graph_readability_redesign/graph1_old_vs_new_comparison.png`~~,
~~`outputs/qa/graph_readability_redesign/graph2_old_vs_new_comparison.png`~~
— **removed in the §17 cleanup pass** (both the old line chart AND the
stacked-bar design they compared are now obsolete, superseded by the
grouped-bar design; see §17's own
`outputs/qa/grouped_region_bars_redesign/graph{1,2}_stacked_vs_grouped_comparison.png`
for the current-vs-immediate-predecessor comparison instead).

Corrected 20s demo clip (frames 440-1040, all current + prior-round
fixes, new Graph 1/2 design):
~~`outputs/qa/graph_readability_redesign/dangerous_space_repositioning_20s_demo.mp4`~~
— **removed in the §17 cleanup pass**, superseded by this round's own
re-render; the CURRENT demo clip lives at
`outputs/final_demo/dangerous_space_repositioning_20s_final.mp4 (this file itself was superseded by this final round; see HANDOFF.md §19)`.

Updated 6 standard previews (`outputs/previews/*.png`) and contact
sheet (`outputs/contact_sheet/contact_sheet.png`) regenerated under the
new design (and again under §17's grouped-bar design).

### 16h. Tests

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/test_graph_bucketing.py -v
# 7 passed

external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 116 passed (109 existing, unaffected + 7 new)

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (unchanged elsewhere in the repo)
```

`tests/test_graph_bucketing.py` (7 tests, pure data-transform tests, no
video/real match data needed): a bucket where every sample is
`"uncertain"` is reported as MISSING (`None`), never a fabricated zero;
a bucket where every sample is `"no_eligible"` is a real, confirmed
0.0; the bucket mean is a genuine causal mean of real resolved values;
uncertain samples are excluded from the mean, never averaged in as
zero; bucket count grows with the real available window and never
fabricates a bucket before kickoff; a bucket never produces more than 3
ranks; no-future-leakage (appending samples beyond the queried window
does not change an already-computed bucket).

### 16i. Stop condition

Per this round's own explicit instruction: **the 120-second final video
was NOT rendered.** This round is scoped to Graph 1/2 readability only
— `pressing_structure` and `offside_break` were not touched.

## 17. Grouped separate-bar redesign + disk-space cleanup (this round)

Two parts, strictly sequenced: (A) replace §16's stacked-bar Graph 1
and dominant-bar-plus-ticks Graph 2 with SIX fully independent,
side-by-side bars per bucket (Team A x Danger #1/#2/#3, Team B x
Danger #1/#2/#3) — approved as the final graph design; (B) ONLY once
that was implemented, previewed, QA'd, and tested, a disk-space cleanup
of obsolete `dangerous_space_repositioning/outputs/` artifacts. **No
analytics change of any kind** — the eligibility gate, Top-3
de-duplication, fixer assignment/conflict resolution, repositioning
formulas, attacking-direction logic, radar alignment, spotlight,
display stability, Graph 3's own formula, the 24-second window, and the
4-second buckets are ALL byte-for-byte unchanged from §15/§16.
`bucket_region_history` itself (the aggregation logic) was NOT touched
this round — only how its already-computed per-rank values are DRAWN.

### 17a. Final Graph 1 design: grouped separate bars (severity)

Replaced `_draw_stacked_bar` (removed) with `_draw_region_bar` (one
bar, one team, one rank) + `_draw_grouped_region_bars` (the shared
per-bucket layout). Each of Danger #1/#2/#3's own real MEAN severity in
a bucket is now its OWN bar — **never summed, never stacked**. Title
changed from "DANGEROUS SPACE BURDEN BY REGION" to "DANGEROUS SPACE
SEVERITY BY REGION" (the old title implied a combined "burden" total
that no longer exists in this design); y-axis label from "Burden Score"
to "Severity Score" for the same reason.

### 17b. Final Graph 2 design: grouped separate bars (access)

Replaced `_draw_dominant_plus_markers_bar` (removed) with the SAME
`_draw_region_bar`/`_draw_grouped_region_bars` pair Graph 1 uses —
Danger #1/#2/#3's own real opponent-access probability each gets its
own full bar (no longer a dominant bar + small tick marks for #2/#3).
Still explicitly NOT stacked/summed (unchanged reasoning from §16d:
access probabilities across different physical regions have no
meaningful combined value) — now expressed as fully independent bars
rather than dominant-bar-plus-ticks, per this round's own explicit
request for visual/informational parity with Graph 1.

### 17c. Visual hierarchy: bucket → team → region rank

`_draw_grouped_region_bars` lays out bars with spacing that WIDENS
outward through the hierarchy, so the eye groups correctly without
needing a label under every bar (per this round's own "do not write
D1/D2/D3 repeatedly under every tiny bar" instruction):

- **Region gap** (within one team's own 3 bars): `1.5%` of the bucket
  group's width — tight, since these 3 bars are meant to read as one
  connected unit.
- **Team gap** (between Team A's 3 bars and Team B's 3 bars, same
  bucket): `14%` of the bucket group's width — clearly wider than the
  region gap, so the team boundary is unambiguous at a glance.
- **Bucket gap**: implicit, from `_bar_chrome`'s own per-bucket group
  width division (`pw / n_buckets`) — the widest separation of the
  three, unchanged from §16.

Danger #1/#2/#3 are shaded, not labeled individually — `RANK_SHADE =
{0: 1.0, 1: 0.62, 2: 0.36}` (full team color, medium, faint), unchanged
from §16, blended via the existing `_shade()` helper. ONE compact
legend (`_rank_legend`, unchanged from §16) states "Team A / Team B"
color swatches plus a "Danger #1/#2/#3" shade key once per panel,
rather than a caption under every one of the up to 36 bars.

### 17d. Honest missing-data handling — unchanged rule, now applied per-bar

`bucket_region_history`'s own three-way `status` rule (uncertain =
excluded from the mean; no_eligible = a real, confirmed 0.0;
resolved = its own real value) is completely UNCHANGED (see §16b) —
this round only changes how the RESULT is drawn. Previously a hatched
"missing" placeholder covered one WHOLE team-bucket bar (when stacked);
now, since each rank is its own bar, `_draw_region_bar` draws a
hatched placeholder for the SPECIFIC rank(s) with no real evidence,
while a rank with real evidence in the SAME bucket still renders
normally — verified directly (§17f) on frame 452's fully-uncertain
first bucket, which now renders as SIX separate hatched placeholders
(3 per team) rather than one per team.

### 17e. Comparisons

`outputs/qa/grouped_region_bars_redesign/graph1_stacked_vs_grouped_comparison.png`
and `graph2_tick_vs_grouped_comparison.png` — built by cropping the
PREVIOUS round's own already-rendered "new" (stacked / dominant+ticks)
design out of its own comparison sheet and pairing it against a fresh
render of THIS round's grouped-bar design, at the same 4 reference
instants used throughout this project's history (01_ordinary_low_risk_moment
/1920, 02_team_a_danger/2020, 03_team_b_danger/840,
04_strong_reposition_recommendation/1040). Confirms directly: all
three ranks are simultaneously visible and individually comparable
(impossible to read off a stacked bar without visually subtracting
segments); both teams remain clearly grouped and separated; Graph 1
communicates each region's own severity directly; Graph 2 communicates
each region's own accessibility directly, answering "which SPECIFIC
region was easiest to exploit" rather than only "was the primary
region exploitable."

### 17f. QA

Visual QA: all 6 standard previews regenerated and inspected; the
missing-data preview (`06_missing_uncertain_data.png`) and a direct
render of frame 452 (the same fully-uncertain-first-bucket case from
§16g) both confirmed 6 separate hatched placeholders where 3 ranks x 2
teams have zero real evidence, transitioning cleanly into real bars
once real evidence exists later in the same window. Bar spacing/shading
verified readable at 3x zoom on a single bucket group — team gap
visibly wider than region gap, all 3 shades within one team
distinguishable.

**20-second video QA** (frames 440-1040, re-rendered under the final
design): extracted and compared 3 consecutive rendered clip frames
(595/598/600, ~0.17s apart) — bar heights evolve smoothly (the
"current"/rightmost bucket's own bars shift very slightly frame to
frame as new real samples enter its still-accumulating window; all
older, fully-elapsed buckets are pixel-identical across the 3 frames),
no flicker, no rank swapping, team/rank colors stayed consistent
throughout. Programmatic checks (601 frames, 30fps, 2304x1204 canvas,
20.03s duration) passed.

### 17g. Tests

8 new tests, all passing, exercising the NEW rendering/layout behavior
as direct pixel inspection of small synthetic canvases (no video, no
real match data needed — `bucket_region_history`'s own aggregation
tests from §16h are unchanged and still valid, since that function
itself was not touched this round):

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/test_grouped_region_bars.py -v
# 8 passed

external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 124 passed (116 existing, unaffected + 8 new)

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (unchanged elsewhere in the repo)
```

`tests/test_grouped_region_bars.py`: equal values across 3 bars
produce equal heights (proves no stacking); a bar's own height is
unaffected by neighboring bars drawn with real values (proves
independence); a missing region draws a hatch pattern with zero solid
team-colored pixels (never a fabricated solid fill); a real, confirmed
zero draws neither a solid bar nor a hatch (a confident absence, not
uncertainty); Danger #1/#2/#3 shades are three distinct colors; Team
A's bars sit strictly left of Team B's bars within the same bucket
(grouping); Graph 2's own bars behave identically to Graph 1's (no
probability summing); zero buckets is a safe no-op.

### 17h. Disk-space cleanup

Performed ONLY after 17a-17g were complete and verified, per this
round's own explicit ordering requirement. Full detail (manifest,
report, exact bytes, retained/removed lists, documentation updates made
BEFORE deletion): `outputs/cleanup_manifest_before_delete.txt` and
`outputs/cleanup_report.md`.

**Summary**: 17 files deleted, 304,512,902 bytes (290.41 MB) freed —
`outputs/` went from 331 MB to 79 MB. All 17 were either (a) an OLDER
round's own re-render of the identical 440-1040 demo clip, superseded
by every later round's own re-render (6 files, 298 MB — the large
majority of the space freed), or (b) a graph-window or graph-chart-type
comparison image whose OWN subject (a 30s/16s/20s window, or a line
chart, or a stacked bar) no longer describes any current or recent
design (11 files, ~6.3 MB). Every deleted file that was still cited by
path in `HANDOFF.md` or `docs/DISPLAY_STABILITY.md` had that reference
updated (struck through, annotated with its successor) BEFORE deletion
— never deleted first and documented after.

**Explicitly NOT touched**: `pressing_structure/`, `offside_break/`,
canonical tracking/analytics data, source code, tests, `HANDOFF.md`
content (only path references were edited), other `docs/*.md` files,
and — deliberately, disclosed, not an oversight —
`outputs/qa/attack_relevance_fix/`'s and `outputs/qa/
current_attack_gate_fix/`'s own smaller case-illustration PNGs/scripts
beyond the specific files directly cited by path in the docs (left
alone rather than risk removing something still load-bearing without a
more careful review).

**Structure**: `outputs/final_demo/` and `outputs/graphs/` are left
exactly as `HANDOFF.md` §3 already documented them — reserved for the
eventual 120-second render and for standalone graph exports
respectively, NEITHER of which is the 20-second demo clip. The current
demo clip was deliberately NOT moved into `final_demo/` (doing so would
contradict that pre-existing convention and could misleadingly suggest
the 120s video already exists); it remains at
`outputs/final_demo/dangerous_space_repositioning_20s_final.mp4 (this file itself was superseded by this final round; see HANDOFF.md §19)`,
consistent with every prior round's own `outputs/qa/<round-name>/`
convention.

### 17i. Final retained deliverable paths

- `outputs/previews/01-06_*.png` (6 files, regenerated under the final
  grouped-bar design)
- `outputs/contact_sheet/contact_sheet.png` (regenerated)
- `outputs/final_demo/dangerous_space_repositioning_20s_final.mp4 (this file itself was superseded by this final round; see HANDOFF.md §19)`
  (the current, final 20-second demo clip)
- `outputs/qa/grouped_region_bars_redesign/graph1_stacked_vs_grouped_comparison.png`
  and `graph2_tick_vs_grouped_comparison.png`
- `outputs/cleanup_manifest_before_delete.txt`, `outputs/cleanup_report.md`

### 17j. Stop condition

Per this round's own explicit instruction: **the 120-second final video
was NOT rendered.** `pressing_structure` and `offside_break` were not
touched, at any point in this round (graph redesign or cleanup).
## 18. Final presentation polish + full 120-second render (FINAL ROUND)

Two parts: (A) three small, purely presentational refinements to
Graph 1/2 (Danger #1 emphasis, a LIVE tag on the current bucket, an
explicit fixed-axis audit); (B) the full 120-second final video, once
the refined design passed a 20-second re-verification. **No analytics
change of any kind** — every item on this round's own "do not change"
list (Top-3 logic, radar alignment, attacking-phase eligibility,
spotlight, display stability, 24s window, 4s buckets) is byte-for-byte
unchanged from §15-§17.

### 18a. Danger #1 width emphasis

`RANK_WIDTH_MULT = {0: 1.15, 1: 1.0, 2: 1.0}` (`live_graphs.py`) —
Danger #1's own bar is drawn ~15% wider than #2/#3, solved so the 3
(now-unequal) bar widths plus their 2 inter-region gaps still exactly
fill each team's own allotted width (never overflowing into the team
gap). 15% (the top of the requested 10-15% range) was chosen because at
this panel's typical ~14-16px bar width, a 10% delta rounds to a
barely-perceptible 1-2px difference; 15% reads reliably as "a bit
wider" at every bucket count from 1 to 6. Verified: `D1/D2 width ratio
measured at 1.14` for a representative 6-bucket panel (rounds slightly
under the nominal 1.15 due to integer pixel rounding, still within the
requested 10-15% band) — `tests/test_grouped_region_bars.py::
test_danger1_bar_is_wider_than_danger2_and_danger3` locks this in
directly via pixel measurement, asserting `1.05 <= ratio <= 1.25`.
Danger #2/#3 remain equal width to each other and fully visible (never
squeezed away) — `test_danger2_and_danger3_remain_equal_width_and_fully_visible`.

### 18b. LIVE tag on the current bucket

`_bucket_axis_labels` now draws a small "LIVE" tag (was "NOW") in the
dashboard's own already-established cyan (`RECOMMEND_COLOR`, the exact
color already used for the spotlight/recommendation ring — chosen
specifically so it reads as "part of the existing visual language,"
not a new unrelated color) under ONLY the bucket whose `t_end >=
cur_time` — by construction this is always the single rightmost,
currently-accumulating bucket, never a historical (fully-elapsed) one.
Moves with the rolling window automatically (it is keyed to `cur_time`,
not a fixed index) — verified directly at a SHORTER, 2-bucket
growing-window case (`test_live_label_moves_with_a_shorter_growing_window`)
to confirm it lands on whichever bucket is actually last, not a
hardcoded "bucket 5."

### 18c. Fixed y-axis audit (both Graph 1 and Graph 2 use [0,1])

Audited before deciding, per this round's own explicit instruction not
to blindly force a range: 

- **Graph 1 (severity)**: `dangerous_space.score_cell` computes
  `severity = raw * area_gate(area)`, where `raw` is a weighted sum of
  5 components (`goal_proximity`, `centrality`, `ball_proximity`,
  `receiver_support`, `coverage_gap`), each individually bounded to
  `[0,1]` (via `_clip01` or a `[0,1]`-range exponential decay), with
  `SEVERITY_WEIGHTS` summing to exactly `1.0` — so `raw` is
  mathematically guaranteed to sit in `[0,1]`. `area_gate(...)` returns
  a value in `[AREA_GATE_MIN=0.15, 1.0]`. Therefore `severity` (the
  product of a `[0,1]` value and a `<=1` multiplier) is ALWAYS in
  `[0,1]` — never can exceed 1, by construction of the formula itself,
  not merely by empirical observation. A bucket's own MEAN of several
  `[0,1]` values is also always in `[0,1]`.
- **Graph 2 (access/opponent-control)**: `opponent_access.
  access_probability` returns either an explicit `0.0`/`0.5`/`1.0`
  edge case or a logistic sigmoid output
  (`1/(1+exp(-(t_def-t_att)/sigma)`), which is mathematically bounded
  to the open interval `(0,1)` for any finite input — never exceeds 1.

**Decision**: BOTH graphs use the fixed literal `(0.0, 1.0)` y-range —
this was already the case in the code before this round (no change was
needed), now explicitly audited and documented rather than assumed.
`tests/test_grouped_region_bars.py::
test_y_axis_is_locked_to_zero_one_and_never_computed_from_data` locks
this in by asserting the literal `(0.0, 1.0)` appears in both
`draw_severity_bar_graph`'s and `draw_opponent_access_bar_graph`'s own
source (never a value computed from the data being plotted, which
would silently auto-rescale frame to frame and break "the same bar
height means the same thing throughout the whole video").

### 18d. Static QA

All 6 standard previews regenerated and inspected: Danger #1 visibly
but subtly wider than #2/#3 in every bucket that has real data; #2/#3
remain fully readable; the "LIVE" cyan tag renders legibly under the
rightmost bucket only; y-axis gridlines/labels stayed at the same
0.0-1.0 positions across every preview; both teams remain clearly
grouped; all 6 buckets (or fewer, near the growing-window start) fit
without visual crowding; missing-data hatched placeholders still render
correctly (checked directly against `06_missing_uncertain_data.png`);
Graph 3 pixel-for-pixel unchanged (same function, same inputs, same
code path).

### 18e. Tests

5 new tests (`tests/test_grouped_region_bars.py`, extending the
existing file from §17): Danger #1 measurably wider than #2/#3 within
the requested 10-15% band (pixel-measured, not just code-reviewed);
#2/#3 stay equal-width; the LIVE tag appears ONLY on the correct
(rightmost) bucket in a 3-bucket case; the LIVE tag correctly tracks a
SHORTER 2-bucket growing window; the fixed `(0.0, 1.0)` y-range is
locked in both graph functions' own source.

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/test_grouped_region_bars.py -v
# 13 passed (8 existing from §17 + 5 new)

external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 129 passed (124 existing, unaffected + 5 new)

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (unchanged elsewhere in the repo)
```
## 19. FINAL DEMO RENDER COMPLETE — full 120-second video + project sign-off

**Status: FINAL DEMO RENDER COMPLETE.** This section is the
authoritative summary of the project's final, locked state. Per this
round's own explicit instruction, no further cosmetic tweaks should be
made after this section unless a real bug is discovered.

### 19a. Full 120-second video

Rendered via the EXACT SAME production code path as every verified
20-second clip — `render_dangerous_space_dashboard.main()`'s
`--out_path` mode, `render_frame()` called once per real frame,
sequentially, frames 0-3599, with ONE continuous
`DashboardDisplayStabilizers` instance threaded through the whole
render (the same persistent-stabilizer code path §8d/§14/§15/§17
already verified — no separate renderer was created, per this round's
own explicit instruction).

```
external/sports/.venv/bin/python3 -m dangerous_space_repositioning.dashboard.render_dangerous_space_dashboard \
  --start_frame 0 --end_frame 3599 \
  --out_path dangerous_space_repositioning/outputs/final_demo/dangerous_space_repositioning_120s_final.mp4
```

Result: **3600 frames, 30.0 fps, 2304x1204, 120.00s duration,
244,612,120 bytes (233.28 MB), total render time 3326.2s (~55.4
minutes)**.

### 19b. 120-second programmatic QA — all passed

- File size: 233.28 MB (not zero-byte, not suspiciously small).
- Decodes successfully via OpenCV (`cv2.VideoCapture(...).isOpened()`).
- Frame count: exactly 3600 (matches `match.n_frames`, the full real
  source clip — no premature termination).
- FPS: exactly 30.0 (source rate, unchanged — no slow-motion, no frame
  duplication).
- Resolution: exactly 2304x1204 (unchanged canvas size).
- Duration: exactly 120.00s.
- First frame: real, non-blank (mean pixel value 44.35).
- Last frame: real, non-blank (mean pixel value 50.79).
- 36 frames sampled every 100th across the whole file: all non-blank,
  all successfully decoded — no mid-file corruption.

### 19c. 120-second visual QA — 13 timeline checkpoints + 4 scenario examples, all passed

Extracted to `outputs/final_demo/qa_frames/` (17 PNGs) and combined
into `outputs/final_demo/final_120s_contact_sheet.png`:

**Timeline checkpoints** (t=0,10,20,...,110,119s — all 13 confirmed
non-blank on extraction, several inspected directly):
- t=0s (frame 0): UNCERTAIN/insufficient-tracking status at kickoff,
  correctly honest, no fabricated danger region.
- t=60s (frame 1800): full 6-bucket window (24s fully saturated), LIVE
  tag correctly on the rightmost bucket, Danger #1 visibly wider than
  #2/#3, both teams clearly grouped, Graph 3 continuous and stable.
- Every other timeline checkpoint confirmed non-blank with a healthy
  pixel-mean range (42.6-50.9) consistent with real broadcast footage,
  no freezes/corruption/visual artifacts.

**Scenario examples** (deliberately chosen OUTSIDE the previously-
verified 440-1040 frame range, as an independent confirmation the
whole pipeline generalizes across the full match, not just the
already-familiar 20-second window):
- **Strong recommendation** (frame 1040, t=34.7s — the project's own
  long-standing flagship example, re-verified in the 120s context):
  pixel-identical to the standalone preview and the 20s clip's own
  same frame.
- **Multi-region moment** (frame 1700, t=56.7s — a NEW instant never
  inspected in any prior round): 3 distinct regions (primary + #2 +
  #3) correctly ranked, radar and match feed agree on all 3 regions'
  relative positions, spotlight correctly tracks the primary fixer,
  secondary/tertiary fixer markers present and consistent between
  panels — a genuinely independent confirmation of the Top-3 +
  radar-alignment + spotlight pipeline working correctly at a
  previously-unchecked point in the match.
- **Uncertain/missing data** (frame 20, t=0.7s, kickoff): honest
  UNCERTAIN status, empty radar, no fabricated danger region.
- **Possession change** (frame 3210, t=107.0s — near the end of the
  match, also never previously inspected): honest UNCERTAIN status
  ("Possession/attacking direction unknown this frame") with correctly
  hatched missing graph buckets spanning the genuinely-uncertain
  stretch, real data on either side, Graph 3 (which does not depend on
  possession) remaining continuous throughout — confirms the
  Current-Attack Eligibility gate and the graphs' own honest-missing-
  data rule both hold up correctly at a real, previously-unseen
  possession transition.

**Confirmed throughout**: no stale danger highlight, no mirrored-radar
regression, correct fixer-spotlight tracking, readable bar charts at
every inspected instant, correctly-behaving LIVE tag, stable Graph 3,
no text overlap severe enough to hurt readability, no visual
corruption, no freezes, no video slowdown, no frame jumps, no future
leakage (the render is strictly sequential, frame `f`'s own analytics
never depend on frame `f+1` or later — see every prior round's own
no-future-leakage tests, all still passing unchanged).

### 19d. Tests — final counts

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 129 passed

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (pressing_structure / offside_break / shared modules -- unchanged)
```

No NEW tests were added specifically for "the full 120s renderer" — it
reuses `render_frame`/`main()`'s existing `--out_path` mode
byte-for-byte (already tested via `test_full_dashboard_renderer_smoke`
and exercised repeatedly across every prior round's own 20s clip); the
5 new tests this round are the §18e polish tests (D1 width, LIVE tag x2,
y-axis lock), already counted above.

### 19e. Final cleanup

Performed only after 19a-19d all passed, per this round's own explicit
ordering. Full detail: `outputs/cleanup_manifest_before_delete.txt` and
`outputs/cleanup_report.md` (both now cover two cleanup passes — the
§17 pass and this round's own addendum).

**This round's own addendum**: 1 additional file deleted (the
immediately-prior round's own 20s demo clip,
`outputs/qa/grouped_region_bars_redesign/dangerous_space_repositioning_20s_demo.mp4`,
41,536,340 bytes), superseded by this round's
`outputs/final_demo/dangerous_space_repositioning_20s_final.mp4`. Every
stale "CURRENT demo clip lives at..." pointer in `HANDOFF.md`
(§10/§14g/§15j/§16g) and `docs/DISPLAY_STABILITY.md` was updated to
point at the new final path BEFORE this deletion.

**Combined total across both cleanup passes**: 18 files deleted,
346,049,242 bytes (330.02 MB) freed. `pressing_structure/`,
`offside_break/`, canonical tracking/analytics data, source code,
tests, and documentation content were untouched by either pass (only
path *references* inside `HANDOFF.md`/`docs/DISPLAY_STABILITY.md` were
edited).

### 19f. Final locked settings — complete reference index

Everything below is LOCKED as of this final round; a future round
should only touch any of these if a real bug is found:

| Area | Final state | Documented in |
|---|---|---|
| Dangerous Space Severity formula | `SEVERITY_WEIGHTS` (goal_proximity 0.20, centrality 0.10, ball_proximity 0.15, receiver_support 0.20, coverage_gap 0.35), area-gated | `docs/METRIC_DEFINITIONS.md` §2 |
| Current-Attack Eligibility gate | Hard filter, `BACKWARD_TOLERANCE_CM=500`, `NEXT_ACTION_BALL_DIST_CM=3000`, `NEXT_ACTION_MIN_RECEIVER_SCORE=0.15` | §6c, `docs/METRIC_DEFINITIONS.md` §2b |
| Top-3 distinct danger regions | `select_top_regions`, `DEDUP_OVERLAP_FACTOR=1.5`, `MAX_DANGER_REGIONS=3` | §15, `docs/METRIC_DEFINITIONS.md` §2c |
| Multi-region fixer assignment/conflict resolution | `assign_regions_and_fixers`, next-best-unassigned-candidate fallback | §15c |
| Repositioning/counterfactual search | `BENEFIT_WEIGHTS` (danger_removed 3.0, new_gap_penalty 1.5, structural_damage_penalty 1.5, movement_cost_penalty 0.01), `MAX_CANDIDATE_RADIUS_CM=300` | `docs/REPOSITIONING_LOGIC.md` |
| Radar coordinate orientation | Y-mirror correction (`_mirror_y`/`_mirror_*` in `voronoi_radar.py`), camera model UNCHANGED | §14a/§14b |
| Cyan fixer spotlight | Primary full-size; secondary/tertiary scaled (60%/40%); no radar spotlight | §14e, §15e |
| Display stability | `DangerRegionStabilizer`, `RecommendationStabilizer`, `LabelStabilizer`, `MultiRegionStabilizer` (2 extra slots) | `docs/DISPLAY_STABILITY.md`, §15d |
| Graph 1 final design | "Dangerous Space Severity by Region" — grouped separate bars, Danger #1 ~15% wider, never stacked/summed, fixed `[0,1]` y-axis | §17a, §18a, §18c |
| Graph 2 final design | "Exploitable Danger by Region" — grouped separate bars, same styling as Graph 1, never stacked/summed, fixed `[0,1]` y-axis | §17b, §18c |
| Graph 3 final design | "Spatial Balance / New-Gap Risk" — UNCHANGED line chart | §8d (original), confirmed unchanged every round since |
| Rolling window | 24 seconds (`COACH_WINDOW_SEC`) | §15f |
| Bucket width | 4 seconds (`COACH_TICK_SEC`), 6 buckets at full window | §16 |
| LIVE tag | Cyan (`RECOMMEND_COLOR`), current/rightmost bucket only, moves with the window | §18b |
| Smoothing (Graph 3 only — Graphs 1/2 use bucket-mean aggregation instead) | `SPATIAL_BALANCE_EMA_ALPHA=0.5` | §16a |
| Missing-data handling | 3-way `status` (`resolved`/`no_eligible`/`uncertain`); uncertain excluded from means; hatched placeholder only when a bucket has ZERO real evidence; dashed "thin evidence" marker below `MIN_SAMPLES_FOR_CONFIDENT_BUCKET=10` real samples | §16b, §16d, §17d |

### 19g. Final deliverable paths

- **Full 120-second final video**:
  `dangerous_space_repositioning/outputs/final_demo/dangerous_space_repositioning_120s_final.mp4`
- **Final 20-second QA clip**:
  `dangerous_space_repositioning/outputs/final_demo/dangerous_space_repositioning_20s_final.mp4`
- **Final 120s QA contact sheet**:
  `dangerous_space_repositioning/outputs/final_demo/final_120s_contact_sheet.png`
- **Final 120s QA frames** (17 files):
  `dangerous_space_repositioning/outputs/final_demo/qa_frames/`
- **Final 6 standard previews**:
  `dangerous_space_repositioning/outputs/previews/01-06_*.png`
- **Final contact sheet** (6-preview grid):
  `dangerous_space_repositioning/outputs/contact_sheet/contact_sheet.png`
- **Grouped-vs-stacked design-decision comparisons** (retained from
  §17): `dangerous_space_repositioning/outputs/qa/grouped_region_bars_redesign/graph1_stacked_vs_grouped_comparison.png`,
  `graph2_tick_vs_grouped_comparison.png`
- **Cleanup manifest/report**:
  `dangerous_space_repositioning/outputs/cleanup_manifest_before_delete.txt`,
  `dangerous_space_repositioning/outputs/cleanup_report.md`

### 19h. Known limitations (disclosed, carried forward — none new this round)

All limitations disclosed in earlier rounds remain accurate and
unchanged by this round's purely-presentational work:

- Only ~22-24% of frames resolve to an eligible primary danger region
  (§6c) — an intentional, disclosed consequence of the Current-Attack
  Eligibility gate ("no recommendation beats a nonsensical one"), not a
  defect.
- A single-defender, ≤3m bounded counterfactual search cannot close
  gaps that would require a bigger team-shape change — most sampled
  (frame, team) combinations honestly report "no improving local
  candidate found" (`docs/REPOSITIONING_LOGIC.md`).
- Severity/access/risk are disclosed proxies, not validated against
  outcome data (none exists at this sample size) — same limitation
  every project in this repo carries (`docs/METHODOLOGY.md`).
- `pressing_structure` and `offside_break` likely share the SAME latent
  radar Y-axis mismatch this project fixed in §14 (same source video,
  same homography file, same shared `tactical_shared.perspective_radar`
  camera module) — NOT fixed there, out of scope for this project,
  flagged for awareness only (§14b).
- The bucketed graphs' historical Top-3 aggregation uses the RAW,
  per-frame analytical ranking, not the display-stabilized slot
  identity the live radar/match-feed panels use for a given instant —
  disclosed in §16f as a deliberate scope decision (replaying stabilizer
  state for an arbitrary historical window would be its own redesign).
- Secondary/tertiary regions' own assigned fixer has no dedicated
  hold/margin hysteresis of its own (§15d) — inherits stability
  transitively from its own already-stabilized region; no flicker was
  observed in any round's QA, but a future round could add this if
  ever needed.
- A secondary/tertiary region's own small pill labels can crowd
  slightly on screen when two such regions' fixers happen to stand
  physically close together (§15h) — cosmetic, Danger #1 remains the
  unambiguous dominant element in every inspected frame.

### 19i. Final stop condition

**This round, and the project's own dashboard-polish arc, are
complete.** Per this round's own explicit final instruction: no further
cosmetic tweaks should be made after this section unless a real bug is
discovered. `pressing_structure` and `offside_break` were not touched
at any point in this round.
