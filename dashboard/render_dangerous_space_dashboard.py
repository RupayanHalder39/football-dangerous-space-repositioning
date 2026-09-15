"""
Dangerous Space Repositioning dashboard -- PREVIEW ONLY (per this
round's own instructions: generate representative preview frames + one
contact sheet, do NOT render the full 120s video yet).

Composition: header -> top row (Tactical Match Feed with Voronoi
overlaid on the real broadcast frame | 3D Voronoi Radar) -> 3 graph
panels (Dangerous Space Severity / Opponent Control of Dangerous Space
/ Spatial Balance-New-Gap Risk), both teams on every graph.

CAUSALITY: every quantity shown for a given preview frame `f` is
computed using ONLY data up to and including frame `f` (the underlying
`build_quality_view` velocity estimate is itself strictly backward-
looking -- see `tactical_shared/tracking.py`). The rolling graph
windows shown are real PAST history up to `f`, never a centered or
future-aware window.
"""
import argparse
import os
import pickle
import sys
import time

import cv2
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from dangerous_space_repositioning.analytics.data_loader import (
    load_match_data, frame_players, rows_by_track_id, TEAM_A, TEAM_B, MatchData,
)
from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players
from dangerous_space_repositioning.analytics.dangerous_space import (
    dangerous_space_for_team, REASON_UNCERTAIN_CONTEXT, REASON_NO_ELIGIBLE_CANDIDATE,
)
from dangerous_space_repositioning.analytics.opponent_access import opponent_control_of_region
from dangerous_space_repositioning.analytics.player_responsibility import rank_candidates
from dangerous_space_repositioning.analytics.counterfactual_repositioning import search_repositioning
from dangerous_space_repositioning.analytics.coach_signals import compute_frame_signal
from dangerous_space_repositioning.analytics.multi_region import (
    select_top_regions, assign_regions_and_fixers, MAX_DANGER_REGIONS,
)
from dangerous_space_repositioning.dashboard.dashboard_style import (
    FONT, TEXT_WHITE, TEXT_DIM, TEAM_COLOR, draw_header, panel_frame, panel_title, ACCENT_RED,
)
from dangerous_space_repositioning.dashboard.voronoi_broadcast_overlay import (
    nearest_transformer, compose_match_feed_panel,
)
from dangerous_space_repositioning.dashboard.voronoi_radar import compose_radar_panel
from dangerous_space_repositioning.dashboard.live_graphs import (
    draw_severity_bar_graph, draw_opponent_access_bar_graph, draw_spatial_balance_graph,
    causal_ema_scalar, decimate_for_display, bucket_region_history,
)
from dangerous_space_repositioning.dashboard.display_stability import DashboardDisplayStabilizers

VIDEO_PATH = os.path.join(REPO_ROOT, "ExternalDownlaodVideo/testVideo1_120s.mp4")
TRANSFORMERS_PATH = os.path.join(REPO_ROOT, "outputs/analytics/testVideo1_120s_v3/homography_transformers.pkl")

CANVAS_W = 2304
HEADER_H, TOP_ROW_H, GAP, GRAPH_ROW_H = 52, 606, 8, 538
LEFT_W = round(CANVAS_W * 0.52)
RIGHT_W = CANVAS_W - LEFT_W
assert HEADER_H + TOP_ROW_H + GAP + GRAPH_ROW_H == 1204

COACH_WINDOW_SEC = 24.0   # rolling visible window -- widened from 20s this round (formulas/smoothing unchanged, see HANDOFF.md)
COACH_TICK_SEC = 4.0
DISPLAY_MAX_POINTS = 240  # point-thinning safety net only -- see live_graphs.decimate_for_display

# DISPLAY-ONLY smoothing (see live_graphs.causal_ema_scalar's own
# docstring): these alphas affect ONLY where a line is drawn, never the
# underlying dangerous_space/opponent_access/spatial_balance values,
# which remain exactly as computed. Closer to 1.0 = lighter smoothing.
SEVERITY_EMA_ALPHA = 0.6          # "raw or very lightly smoothed" -- kept responsive
OPPONENT_CONTROL_EMA_ALPHA = 0.15  # was 0.2 -- see docs/DISPLAY_STABILITY.md's alpha comparison (0.2/0.15/0.12)
SPATIAL_BALANCE_EMA_ALPHA = 0.5   # light smoothing, documented in HANDOFF.md

STATUS_COLOR = {
    "no_danger": (110, 110, 110),
    "moderate": (60, 190, 220),
    "high": (40, 140, 255),
    "recommendation": (235, 220, 70),
}


def _status_for(severity_a: float | None, severity_b: float | None, context_reason: str | None = None):
    """`context_reason`: when both severities are None, distinguishes
    WHY for an honest subtitle -- structurally insufficient tracking
    data (unrelated to this round), possession/ball/attacking-direction
    genuinely unknown (`REASON_UNCERTAIN_CONTEXT`), or the attacking
    context IS known but no real candidate passed the Current-Attack
    Eligibility gate this frame (`REASON_NO_ELIGIBLE_CANDIDATE`) -- see
    HANDOFF.md's "Current-Attack Eligibility Gate" section. All three
    still show the same "UNCERTAIN" title (so the existing
    display-stability label debounce's "any UNCERTAIN transition is
    immediate" rule keeps working unchanged), only the subtitle differs."""
    if severity_a is None and severity_b is None:
        if context_reason == REASON_UNCERTAIN_CONTEXT:
            return "UNCERTAIN", "Possession/attacking direction unknown this frame", STATUS_COLOR["no_danger"]
        if context_reason == REASON_NO_ELIGIBLE_CANDIDATE:
            return "UNCERTAIN", "No current attacking danger identified this frame", STATUS_COLOR["no_danger"]
        return "UNCERTAIN", "Insufficient tracking evidence this frame", STATUS_COLOR["no_danger"]
    sa = severity_a or 0.0
    sb = severity_b or 0.0
    worse_team, worse = (0, sa) if sa >= sb else (1, sb)
    if worse < 0.35:
        return "LOW RISK", f"Team A: {sa:.2f}   Team B: {sb:.2f}", STATUS_COLOR["no_danger"]
    if worse < 0.6:
        return "MODERATE RISK", f"Team A: {sa:.2f}   Team B: {sb:.2f}  (worse: Team {'A' if worse_team == 0 else 'B'})", STATUS_COLOR["moderate"]
    return "HIGH RISK", f"Team A: {sa:.2f}   Team B: {sb:.2f}  (worse: Team {'A' if worse_team == 0 else 'B'})", STATUS_COLOR["high"]


def load_transformers() -> dict:
    with open(TRANSFORMERS_PATH, "rb") as fh:
        return pickle.load(fh)


def build_signal_history(match: MatchData, up_to_frame: int, window_sec: float, stride: int = 1):
    """Real causal history [up_to_frame - window_sec*fps, up_to_frame],
    computed at FULL per-frame resolution by default (`stride=1`) --
    used only to DRAW the rolling graphs; never looks past
    `up_to_frame`. Any display-only decimation happens LATER, as a
    separate step on top of this full-resolution real series (see
    `live_graphs.decimate_for_display`), never by skipping frames here
    during computation."""
    start = max(0, up_to_frame - int(window_sec * match.fps))
    frames = list(range(start, up_to_frame + 1, stride))
    if frames[-1] != up_to_frame:
        frames.append(up_to_frame)
    hist = {"severity_a": [], "severity_b": [], "threat_a": [], "threat_b": [], "risk_a": [], "risk_b": [],
            "samples_a": [], "samples_b": []}
    for f in frames:
        sig = compute_frame_signal(match, f)
        t = sig.time_sec
        hist["severity_a"].append((t, sig.severity_a))
        hist["severity_b"].append((t, sig.severity_b))
        hist["threat_a"].append((t, sig.threat_against_a))
        hist["threat_b"].append((t, sig.threat_against_b))
        hist["risk_a"].append((t, sig.risk_a))
        hist["risk_b"].append((t, sig.risk_b))
        # Feeds the Graph 1/2 bucketed bar redesign (see
        # `live_graphs.bucket_region_history`) -- reuses the SAME
        # already-computed `sig` from this shared history pass, no
        # extra frames processed.
        hist["samples_a"].append({"time_sec": t, "status": sig.status_a,
                                   "top3_severity": sig.top3_severity_a, "top3_access": sig.top3_access_a})
        hist["samples_b"].append({"time_sec": t, "status": sig.status_b,
                                   "top3_severity": sig.top3_severity_b, "top3_access": sig.top3_access_b})
    return hist


def render_frame(match: MatchData, transformers: dict, cap: cv2.VideoCapture, frame: int,
                  force_team: int | None = None, force_player=None,
                  stab: DashboardDisplayStabilizers | None = None) -> np.ndarray | None:
    """`force_team`/`force_player`: override the auto-selected
    "worse team" / "top-ranked candidate" choice -- used ONLY to
    generate the "high new-gap-risk case" preview, where we deliberately
    visualize a real, fully-computed candidate that the search itself
    would NOT naturally recommend (its own benefit score is negative),
    specifically to show what an elevated new-gap-risk reading looks
    like. Every number displayed is still a real, freshly computed
    value for that exact (frame, team, player) -- nothing here is
    fabricated, only the CHOICE of which already-real candidate to
    display is manual for this one preview. The force_team/force_player
    path always uses raw, unstabilized values (see
    `dashboard/display_stability.py`), since it is itself a one-off
    manual choice, not a naturally-arising real-time recommendation.

    `stab`: a `DashboardDisplayStabilizers` to carry causal display
    hysteresis/smoothing ACROSS SEQUENTIAL calls (see
    `docs/DISPLAY_STABILITY.md`). Pass the SAME instance across an
    increasing-frame sequential render (`main()`'s `--out_path` mode
    does this). Omitted (the default, used by every independent
    preview call) -- a fresh, empty one is used, which is equivalent to
    no stabilization at all on a lone frame with no prior history."""
    if stab is None:
        stab = DashboardDisplayStabilizers()
    t = frame / match.fps
    attacking_team_actual, possession_confidence = match.attacking_team_at(frame)

    ok = cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ret, raw_frame = cap.read()
    if not ret:
        return None

    team_a, team_b = frame_players(match, frame)
    ball = match.ball_at(frame)
    rows = rows_by_track_id(match, frame)
    transformer = nearest_transformer(transformers, frame)

    voronoi_result = voronoi_for_players(team_a, team_b)

    # `attacking_team_actual`: the best available CAUSAL possession
    # estimate this frame (see `data_loader.attacking_team_at`), or
    # `None` if genuinely unknown -- gates both teams' severities by
    # real attacking-phase relevance (see
    # `dangerous_space.direction_relevance`). This is the core of the
    # "Attacking-Phase Relevance Correction" -- see HANDOFF.md.
    danger_a = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, match.pitch, voronoi_result,
                                         attacking_team_actual=attacking_team_actual)
    danger_b = dangerous_space_for_team(TEAM_B, team_a, team_b, ball, match.pitch, voronoi_result,
                                         attacking_team_actual=attacking_team_actual)
    severity_a = danger_a["top"].severity if danger_a["valid"] and danger_a["top"] else None
    severity_b = danger_b["top"].severity if danger_b["valid"] and danger_b["top"] else None

    # The dashboard highlights whichever team's flagged region is
    # currently MORE severe -- "the single most pressing question right
    # now," not both teams' full detail at once (each graph below still
    # shows both teams' full time series). `force_team` overrides this
    # for the one deliberately-chosen new-gap-risk illustration above,
    # and bypasses region display-stabilization entirely (raw, real,
    # single-shot). Otherwise `stab.region` decides WHICH team's region
    # to keep showing (causal hold + switch-margin hysteresis) and
    # separately EMA-smooths only the DRAWN circle's centroid/radius;
    # `danger_point`/`danger_area` below are always the REAL, unsmoothed
    # values for whichever team is displayed, and are what feed
    # `opponent_control_of_region`/`search_repositioning` -- only
    # `draw_point`/`draw_area` (the circle actually drawn) are smoothed.
    if force_team is not None:
        defending_team = force_team
        top_danger = danger_a["top"] if force_team == TEAM_A else danger_b["top"]
        danger_point = (top_danger.x, top_danger.y) if top_danger else None
        danger_area = top_danger.area_cm2 if top_danger else 0.0
        draw_point, draw_area = danger_point, danger_area
    else:
        info_a = ((severity_a, danger_a["top"].x, danger_a["top"].y, danger_a["top"].area_cm2)
                  if (danger_a["valid"] and danger_a["top"]) else None)
        info_b = ((severity_b, danger_b["top"].x, danger_b["top"].y, danger_b["top"].area_cm2)
                  if (danger_b["valid"] and danger_b["top"]) else None)
        defending_team, danger_point, danger_area, draw_point, draw_area = stab.region.update(t, info_a, info_b)
        danger_area = danger_area or 0.0

    threat = None
    recommend_from = recommend_to = None
    recommend_player_id = None
    interpretation = None

    if force_team is not None:
        if danger_point is not None:
            threat = opponent_control_of_region(defending_team, danger_point, team_a, team_b)
            ranked = rank_candidates(defending_team, danger_point, team_a, team_b, rows, ball, match.pitch,
                                      attacking_team_actual=attacking_team_actual)
            if ranked:
                rec_id = force_player if force_player is not None else ranked[0].track_id
                recommend_player_id = rec_id
                res = search_repositioning(defending_team, rec_id, danger_point, team_a, team_b,
                                            ball, rows, danger_area, match.pitch,
                                            attacking_team_actual=attacking_team_actual)
                recommend_from = (res.current_x, res.current_y)
                if force_player is not None:
                    # For the deliberate new-gap-risk illustration, show the
                    # HIGHEST new-gap-penalty candidate this player actually
                    # tested (still a real, computed value), not necessarily
                    # their own best-benefit one.
                    candidate = max((c for c in res.all_candidates if c.rejected_reason is None),
                                     key=lambda c: c.new_gap_penalty, default=res.best)
                else:
                    candidate = res.best
                if candidate is not None:
                    recommend_to = (candidate.x, candidate.y)
                interpretation = res.interpretation
    else:
        raw_id, raw_res, valid_ids = None, None, set()
        if danger_point is not None:
            threat = opponent_control_of_region(defending_team, danger_point, team_a, team_b)
            ranked = rank_candidates(defending_team, danger_point, team_a, team_b, rows, ball, match.pitch,
                                      attacking_team_actual=attacking_team_actual)
            valid_ids = {c.track_id for c in ranked}
            if ranked:
                raw_id = ranked[0].track_id
                raw_res = search_repositioning(defending_team, raw_id, danger_point, team_a, team_b,
                                                ball, rows, danger_area, match.pitch,
                                                attacking_team_actual=attacking_team_actual)

        def _search(pid):
            return search_repositioning(defending_team, pid, danger_point, team_a, team_b,
                                         ball, rows, danger_area, match.pitch,
                                         attacking_team_actual=attacking_team_actual)

        recommend_player_id, disp_res = stab.recommendation.update(
            t, defending_team, danger_point, valid_ids, raw_id, raw_res, _search)
        if disp_res is not None:
            recommend_from = (disp_res.current_x, disp_res.current_y)
            interpretation = disp_res.interpretation
            recommend_to = stab.recommendation.display_to

    # TOP-3 DISTINCT DANGEROUS REGIONS (this round -- see HANDOFF.md).
    # `distinct_regions[0]`, when present, is ALWAYS identical to `top`/
    # `danger_point`'s own real value (see
    # `multi_region.select_top_regions`'s own docstring) -- this block
    # only ever ADDS the secondary/tertiary slots on top of the
    # existing, unchanged primary pipeline above; it never re-decides
    # the primary region or its fixer. Skipped entirely for the
    # force_team/force_player illustration path (a one-off manual
    # choice, same scoping the existing recommendation stabilizer
    # already uses for that path).
    extra_regions = []
    if force_team is None:
        if danger_point is not None:
            eligible_ranked_for_team = danger_a["eligible_ranked"] if defending_team == TEAM_A else danger_b["eligible_ranked"]
            distinct_regions = select_top_regions(eligible_ranked_for_team, max_regions=MAX_DANGER_REGIONS)
            stabilized_extra = stab.extra_regions.update(t, distinct_regions[1:])
            # The primary region's own already-stabilized fixer can
            # never also be assigned as the secondary/tertiary fixer --
            # see multi_region.assign_regions_and_fixers's own conflict
            # resolution.
            already_assigned = {recommend_player_id} if recommend_player_id is not None else set()
            extra_assignments = assign_regions_and_fixers(
                defending_team, stabilized_extra, team_a, team_b, rows, ball, match.pitch,
                attacking_team_actual=attacking_team_actual, already_assigned=already_assigned, start_rank=2)
            for a in extra_assignments:
                extra_regions.append({
                    "rank": a.rank, "x": a.danger.x, "y": a.danger.y, "area_cm2": a.danger.area_cm2,
                    "fixer_xy": (a.fixer_candidate.x, a.fixer_candidate.y) if a.fixer_candidate else None,
                    "target_xy": (a.reposition.best.x, a.reposition.best.y)
                                 if (a.reposition and a.reposition.best) else None,
                    "conflict": a.conflict, "reason": a.reason,
                })
        else:
            stab.extra_regions.update(t, [])  # honest immediate clear -- same gap-handling convention as every other stabilizer

    # Distinguish WHY both severities might be None -- possession/ball
    # genuinely unknown vs. context known but nothing passed the
    # Current-Attack Eligibility gate -- for an honest UNCERTAIN subtitle.
    context_reason = None
    if severity_a is None and severity_b is None:
        if danger_a.get("reason") == REASON_UNCERTAIN_CONTEXT or danger_b.get("reason") == REASON_UNCERTAIN_CONTEXT:
            context_reason = REASON_UNCERTAIN_CONTEXT
        elif danger_a.get("reason") == REASON_NO_ELIGIBLE_CANDIDATE or danger_b.get("reason") == REASON_NO_ELIGIBLE_CANDIDATE:
            context_reason = REASON_NO_ELIGIBLE_CANDIDATE
    raw_title, raw_subtitle, raw_color = _status_for(severity_a, severity_b, context_reason)
    if recommend_to is not None and interpretation and interpretation.startswith("candidate improved"):
        raw_title = "RECOMMENDATION FOUND"
        raw_color = STATUS_COLOR["recommendation"]
    status_title, status_subtitle, status_color = stab.label.update(t, raw_title, raw_subtitle, raw_color)

    left = compose_match_feed_panel(
        raw_frame, LEFT_W, TOP_ROW_H, transformer, voronoi_result, team_a, team_b, ball,
        draw_point, draw_area, defending_team, threat, recommend_from, recommend_to,
        status_title, status_subtitle, status_color, extra_regions=extra_regions,
    )
    right = compose_radar_panel(
        RIGHT_W, TOP_ROW_H, team_a, team_b, ball, voronoi_result,
        draw_point, draw_area, defending_team, threat, recommend_from, recommend_to, match.pitch,
        extra_regions=extra_regions,
    )
    top_row = np.hstack([left, right])

    header = draw_header(CANVAS_W, HEADER_H, "DANGEROUS SPACE REPOSITIONING ANALYTICS",
                          (f"t = {frame / match.fps:.1f}s", TEXT_DIM))

    # Full per-frame-resolution real history for the rolling window (see
    # build_signal_history's own docstring) -- smoothing and display
    # decimation are applied AFTER, as separate, clearly-scoped
    # display-only steps, never mixed into the computation itself.
    hist = build_signal_history(match, frame, COACH_WINDOW_SEC, stride=1)
    t_lo, t_hi = max(0.0, frame / match.fps - COACH_WINDOW_SEC), frame / match.fps

    def _prep(series, alpha):
        smoothed = causal_ema_scalar(series, alpha)
        return decimate_for_display(smoothed, DISPLAY_MAX_POINTS)

    # Graphs 1/2 (this round -- see HANDOFF.md): bucketed bar redesign.
    # `SEVERITY_EMA_ALPHA`/`OPPONENT_CONTROL_EMA_ALPHA` are no longer
    # applied here -- per-bucket MEAN aggregation (see
    # `bucket_region_history`) is this round's own display-smoothing
    # mechanism for these two graphs, replacing per-frame EMA. Graph 3
    # is completely UNCHANGED below (still line-based, still EMA'd).
    buckets_a = bucket_region_history(hist["samples_a"], t_lo, t_hi, COACH_TICK_SEC)
    buckets_b = bucket_region_history(hist["samples_b"], t_lo, t_hi, COACH_TICK_SEC)
    risk_a = _prep(hist["risk_a"], SPATIAL_BALANCE_EMA_ALPHA)
    risk_b = _prep(hist["risk_b"], SPATIAL_BALANCE_EMA_ALPHA)

    gw = (CANVAS_W - 2 * GAP) // 3
    g1 = draw_severity_bar_graph(gw, GRAPH_ROW_H, buckets_a, buckets_b, t_hi, t_lo, t_hi)
    g2 = draw_opponent_access_bar_graph(gw, GRAPH_ROW_H, buckets_a, buckets_b, t_hi, t_lo, t_hi)
    g3_w = CANVAS_W - 2 * gw - 2 * GAP
    g3 = draw_spatial_balance_graph(g3_w, GRAPH_ROW_H, risk_a, risk_b, t_hi, t_lo, t_hi, COACH_TICK_SEC)
    gap_col = np.full((GRAPH_ROW_H, GAP, 3), (28, 22, 18), dtype=np.uint8)
    graph_row = np.hstack([g1, gap_col, g2, gap_col, g3])
    if graph_row.shape[1] != CANVAS_W:
        graph_row = cv2.resize(graph_row, (CANVAS_W, GRAPH_ROW_H))

    row_gap = np.full((GAP, CANVAS_W, 3), (28, 22, 18), dtype=np.uint8)
    canvas = np.vstack([header, top_row, row_gap, graph_row])
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=int, action="append", default=[])
    ap.add_argument("--name", type=str, action="append", default=[])
    ap.add_argument("--force_team", type=int, action="append", default=[])
    ap.add_argument("--force_player", type=int, action="append", default=[])
    ap.add_argument("--out_dir", type=str, default=os.path.join(os.path.dirname(__file__), "..", "outputs", "previews"))
    ap.add_argument("--out_path", type=str, default=None,
                     help="if set, render frames [--start_frame, --end_frame] SEQUENTIALLY to this "
                          ".mp4 at normal real-time speed (no slow-motion, no frame duplication, "
                          "source FPS preserved exactly), using ONE continuous "
                          "DashboardDisplayStabilizers instance so the causal display-stability "
                          "hold/margin/EMA mechanisms can function across time -- see "
                          "docs/DISPLAY_STABILITY.md. Every frame's analytics are still real and "
                          "computed fresh from only that frame and earlier ones (no future frames).")
    ap.add_argument("--start_frame", type=int, default=0)
    ap.add_argument("--end_frame", type=int, default=None, help="inclusive; defaults to the last real frame")
    args = ap.parse_args()

    match = load_match_data()
    transformers = load_transformers()
    cap = cv2.VideoCapture(VIDEO_PATH)

    if args.out_path:
        f_start = args.start_frame
        f_end = args.end_frame if args.end_frame is not None else match.n_frames - 1
        os.makedirs(os.path.dirname(args.out_path) or ".", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.out_path, fourcc, match.fps, (CANVAS_W, HEADER_H + TOP_ROW_H + GAP + GRAPH_ROW_H))
        stab = DashboardDisplayStabilizers()
        t0 = time.time()
        n_written = 0
        total = f_end - f_start + 1
        for f in range(f_start, f_end + 1):
            canvas = render_frame(match, transformers, cap, f, stab=stab)
            if canvas is None:
                print(f"stopped at frame {f}: source video ended early")
                break
            writer.write(canvas)
            n_written += 1
            if n_written % 60 == 0:
                elapsed = time.time() - t0
                eta = elapsed / n_written * (total - n_written)
                print(f"...{n_written}/{total} frames written ({f / match.fps:.1f}s) in {elapsed:.1f}s "
                      f"(ETA {eta:.0f}s)", flush=True)
        writer.release()
        cap.release()
        print(f"Wrote {args.out_path}: {n_written} frames, canvas {CANVAS_W}x{HEADER_H + TOP_ROW_H + GAP + GRAPH_ROW_H}, "
              f"fps={match.fps} (normal real-time speed, unchanged), "
              f"duration={n_written / match.fps:.2f}s, total_render_time={time.time() - t0:.1f}s")
        return

    os.makedirs(args.out_dir, exist_ok=True)
    names = args.name or [f"frame_{f}" for f in args.frame]
    force_teams = args.force_team or [None] * len(args.frame)
    force_players = args.force_player or [None] * len(args.frame)
    for f, name, ft, fp in zip(args.frame, names, force_teams, force_players):
        canvas = render_frame(match, transformers, cap, f, force_team=ft, force_player=fp)
        if canvas is None:
            print(f"frame {f}: could not read video frame")
            continue
        out_path = os.path.join(args.out_dir, f"{name}.png")
        cv2.imwrite(out_path, canvas)
        print(f"wrote {out_path} ({canvas.shape[1]}x{canvas.shape[0]})")
    cap.release()


if __name__ == "__main__":
    main()
