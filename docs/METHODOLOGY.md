# Methodology — Dangerous Space Repositioning Analytics

## Problem definition

**Which player should reposition to close dangerous space without creating a
new gap?**

The pipeline answers five sub-questions every frame, for both teams
symmetrically:

1. Where is the dangerous space? (`analytics/dangerous_space.py`)
2. Why is it dangerous? (the same module's per-component breakdown)
3. Who should fix it? (`analytics/player_responsibility.py`)
4. Where should that player move? (`analytics/counterfactual_repositioning.py`)
5. Does that repositioning close the problem without creating another gap?
   (the same module's `new_gap_penalty`, backed by `analytics/spatial_balance.py`)

Voronoi (`analytics/voronoi_control.py`) is the geometric TOOL used to
answer these questions — it is never presented as the answer by
itself. Drawing a Voronoi diagram is step zero, not the deliverable.

## Data sources (real, canonical, never regenerated)

| Path | Contents | Used for |
|---|---|---|
| `outputs/tracking/testVideo1_120s/tracking.parquet` | Raw per-frame player/ball/referee detections, 3600 frames @ 30fps (video_id, frame, timestamp_sec, track_id, object_type, class_id, team_id, confidence, bbox_x1-y2, x_image, y_image, x_pitch, y_pitch) | The one and only tracking input |
| `outputs/analytics/testVideo1_120s_v3/ball_trajectory.parquet` | Already-hardened ball trajectory with a real OBSERVED/PREDICTED/LOST distinction (`is_observed`) | Ball position/evidence |
| `outputs/analytics/testVideo1_120s_v3/homography_transformers.pkl` | Per-frame `sports.common.view.ViewTransformer` (image↔pitch homography), pickled | Projecting pitch-cm analytics onto the real broadcast frame |
| `ExternalDownlaodVideo/testVideo1_120s.mp4` | The real broadcast video | The Tactical Match Feed panel's background |

No player tracking, ball tracking, or homography was re-run for this
project — everything above is read, never recomputed.

## Causal data pipeline (reused, not reinvented)

`analytics/data_loader.py` builds on `tactical_shared.tracking.
build_quality_view` + `current_roles` — the SAME loader already
shipped and validated by `pressing_structure` and `offside_break`.
Deliberately NOT `analytics.position_fill.build_full_display_frame`
(which short-gap-interpolates, i.e. uses a few frames of look-ahead) —
`build_quality_view` never fills a missing position and computes
velocity from a strictly backward-looking finite-difference / short
least-squares fit over real, already-observed frames only. See that
module's own docstring for the full detail; this project adds no new
tracking/cleaning logic, only assembles the existing causal view into
the small per-frame shape (`frame_players`, `rows_by_track_id`,
`ball_at`) the rest of this project's analytics consume.

## Team convention (this project only)

`team_id == 0` → **Team A** (blue in every dashboard panel)
`team_id == 1` → **Team B** (red in every dashboard panel)

This is a DIFFERENT color convention from `pressing_structure`/
`offside_break`'s own green/gold — deliberately matching the attached
reference mockup, since this is a visually independent project.

**Pitch-geometry note** (a real correctness detail, not obvious from
the numbers alone): per `tactical_shared.coordinates.DEFAULT_PITCH`
(one period, `far=True`), **Team A's own goal sits at x = length_cm
(12000), not x = 0** — `PitchConfig.own_goal(0)` resolves to the far
end. Team B's own goal sits at x = 0. Every goal-proximity/progression
calculation in this project uses `pitch.own_goal(team)` /
`pitch.depth(team, x)` directly rather than a hardcoded end, so this is
handled correctly throughout — but it is easy to get backwards when
writing a NEW test or script against this pitch config, so it is called
out explicitly here (see `docs/../tests/test_dangerous_space.py` for a
worked example that initially got this backwards and was corrected).

## Real measured constants (not textbook guesses)

Two of `dangerous_space.py`'s distance-decay reference constants were
calibrated from THIS clip's own real measured spacing, not assumed:

- Real nearest-**teammate** distance across both teams, sampled every
  20 frames for the whole clip: **median ≈ 805cm (~8m), 90th
  percentile ≈ 1539cm (~15m)**.
- `RECEIVER_RADIUS_CM` (2000cm) and `COVERAGE_RADIUS_CM` (2500cm) are
  set a little above that real measured range — "close enough to
  plausibly influence the space," not "standing on top of it" — see
  `dangerous_space.py`'s own comment for why an earlier, tighter
  1200-1500cm choice made the counterfactual search unable to detect
  almost any real improvement (the flagged danger region's nearest
  candidate defender is real-world typically 20-40m away, per the same
  measurement exercise, so a coverage radius sized for "marking
  distance" rather than "meaningfully contests this space" made
  `coverage_gap_score` insensitive to any bounded ≤3m move).
- `PLAYER_MAX_SPEED_CM_S`/`REACTION_TIME_SEC`/`CONTROL_SIGMA_SEC`
  (`opponent_access.py`) are IMPORTED, never redefined, from the
  repo's own already-calibrated `analytics/pitch_control.py`
  (`PLAYER_MAX_SPEED_CM_S=800` = this clip's own measured 95th-
  percentile real player speed).

## Possession/attacking-team coverage (measured, not assumed)

`data_loader._compute_attacking_context` (see `HANDOFF.md`'s
Attacking-Phase Relevance Correction) needed to know how often this
clip's real, causal possession evidence is actually available, since
that directly determines whether a majority-vote fallback is even
worth building:

- Real close-control observations (`tactical_shared.tracking.
  current_roles`'s own `carrier_team`, ball within 200cm of a player)
  cover only **4.0%** of frames (144/3600) on this clip.
- They are highly BURSTY, not uniform: median gap between two such
  observations is **0.03s** (they cluster tightly during a dribble/
  carry), but the mean gap is **0.80s** and gaps as long as **43.6s**
  occur during loose-ball/long-ball spells.
- The shared `current_roles`'s own 4-second trailing-majority fallback
  (`historical_context_role`) therefore only resolves **47%** of
  frames total (current + 4s combined) on this clip.
- This project's own tiered extension (4s → 12s → 30s majority,
  stopping at the first non-tied window) resolves **79%** of frames,
  leaving **21%** genuinely uncertain (`attacking_team=None`) — see
  `_compute_attacking_context`'s own docstring for the exact algorithm.
  All three window sizes reuse the SAME real, causal
  `carrier_team`/CONTROLLED observations the shared function already
  computes; nothing here re-derives possession from scratch.
- Separately, real BALL POSITION (not possession) is unavailable at
  ~46% of frames even when possession IS confidently known (ball
  tracking has its own independent real gaps, e.g. the ball leaving the
  visible frame or a low-confidence detection) — `direction_relevance`
  degrades to neutral (1.0) for exactly these frames, honestly, rather
  than guessing a position.

## Causality guarantee

Every quantity computed for frame `f` uses ONLY data from frames `<= f`:

- `build_quality_view`'s own velocity estimate is backward-looking only.
- `analytics/coach_signals.py::compute_frame_signal(match, f)` reads
  exactly `match.players_by_frame[f]`, `match.ball_at(f)`, and that
  frame's own roles — never a neighboring frame. `tests/
  test_dashboard_render.py::test_no_future_leakage` verifies this
  directly (corrupting every frame after `f` and confirming the
  signal at `f` is unchanged).
- `data_loader._compute_attacking_context` (the attacking-team
  estimate) is likewise a pure function of frames `<= f` at every index
  — its majority-vote windows only ever look backward, even though the
  whole array is precomputed once up front for engineering convenience
  (the exact same "precomputed once, causal per-index" pattern the
  shared `current_roles()` output already uses). `tests/
  test_attacking_phase_relevance.py::test_no_future_leakage_attacking_context`
  verifies this directly (two runs sharing an identical prefix but
  different futures produce identical entries for that prefix).
- The dashboard's rolling graph windows are real PAST history up to
  the current frame, never centered or future-aware.
- No retrospective/offline-only calculation is used anywhere in this
  project's live-signal path. (The one exception — reproducing a
  documented result by testing which parameter value matches it — is
  a one-off reverse-derivation exercise from the `pressing_structure`
  project, not something this project does; it is mentioned here only
  because the same care was taken.)

## What is measured vs. estimated vs. inferred vs. preliminary

| Quantity | Status |
|---|---|
| Player/ball pitch positions | **Measured** (real tracking, read-only) |
| Voronoi cells/areas | **Measured geometry** (nearest-player territory — a well-understood proxy, explicitly not possession/control probability) |
| Dangerous Space Severity | **Estimated proxy** — a disclosed, documented weighted combination of real geometric/contextual components, not fit to outcome data (none exists at this sample size) |
| Opponent Control of Dangerous Space | **Estimated proxy** — reuses the repo's own disclosed simplified time-to-intercept + logistic model |
| Spatial Balance / New-Gap Risk | **Estimated proxy** — real geometry only (compactness, isolation, coverage variance), no fabricated demonstration values |
| Candidate player ranking | **Estimated/heuristic** — a documented weighted score, not a trained model |
| Recommended reposition | **Estimated, PRELIMINARY** — "best candidate within the tested local search," never a proven/global optimum |
| Secondary/tertiary distinct regions (Top-3) | **Estimated proxy, same formula as the primary region** — de-duplication (§2c of `docs/METRIC_DEFINITIONS.md`) is a geometric pruning step over already-eligible, already-scored candidates, not a new severity model |
| Multi-region fixer conflict resolution | **Deterministic, not estimated** — reuses the existing `rank_candidates` ordering exactly; "next-best unassigned candidate" is a real, computed fallback, never invented |

See `docs/METRIC_DEFINITIONS.md` for exact formulas and
`docs/REPOSITIONING_LOGIC.md` for the full counterfactual-search
write-up.

## Top-3 Distinct Dangerous Regions (this round)

Extended the dashboard from ONE primary dangerous region per team to up
to THREE, ranked by urgency, WITHOUT touching the underlying severity
formula, the Current-Attack Eligibility gate, the counterfactual search,
or the radar/match-feed alignment fix. See `docs/METRIC_DEFINITIONS.md`
§2c for the exact de-duplication rule and `docs/DISPLAY_STABILITY.md`
for the new `MultiRegionStabilizer`. Graphs 1 and 2 continue to plot the
PRIMARY region only (see `docs/FINAL_DASHBOARD_NOTES.md`'s own
discussion of why a Top-3 aggregate was considered and rejected for
those two graphs).

Also this round: the coach-mode graph rolling window was widened from
20s to 24s (`COACH_WINDOW_SEC` in `render_dangerous_space_dashboard.py`)
— a DISPLAY-only change (more real history visible at once), with every
formula, smoothing alpha, and decimation policy held fixed. See
`docs/DISPLAY_STABILITY.md`'s graph-window QA section.
