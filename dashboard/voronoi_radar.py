"""
Row 1, RIGHT panel: the 2.5D / perspective Voronoi radar -- ONE mode
only (no Player View / Heatmap toggle, per this project's own brief).

Reuses, rather than reinvents, two pieces of already-working,
already-documented machinery elsewhere in this repo:

  - `tactical_shared.perspective_radar` -- the shared pinhole-camera
    pitch(cm) -> canvas(px) projection already used by both
    `pressing_structure` and `offside_break`'s own perspective radars.
    Every object here (pitch markings, Voronoi polygons, the danger
    region, players, the ball, the recommendation arrow) is projected
    through the SAME homography -- never independently positioned.
  - `offside_break.dashboard.render_offside_dashboard_v4_simple`'s
    human-footballer glyph primitives (`_draw_player_shadow`,
    `_draw_player_body_human`, `_heading_cue`) -- the exact "human-like
    player glyph" look already built and visually QA'd for that
    project's own perspective radar, imported directly rather than
    copy-pasted a second time.

Analytics are computed upstream in real pitch cm; this module only
decides where things land on screen.

## Radar/match-feed spatial alignment fix (see HANDOFF.md)

Audited and confirmed: the REAL per-frame broadcast homography
(`outputs/analytics/testVideo1_120s_v3/homography_transformers.pkl`)
and this radar's fixed virtual camera (`tactical_shared.
perspective_radar.DEFAULT_RADAR_CAMERA`, `yaw_deg=0.0`) agree on the
pitch-LENGTH (x) axis (`x=0` renders on the left in both, checked
across multiple frames) but DISAGREE on the pitch-WIDTH (y) axis: a
point near `y=0` renders FARTHER (nearer the top) in the real broadcast
image, but NEARER (nearer the bottom) on this radar's own unmirrored
convention -- a genuine, measured, systematic mismatch, present in
every frame checked (i.e. a real calibration/convention difference
between this specific video's tracking pipeline and the radar's own
assumed camera siding, not a transient glitch). Rotating the virtual
camera's `yaw_deg` to 180 was tried and REJECTED: a yaw rotation
necessarily flips BOTH axes together (real 3D camera geometry -- moving
a camera to the opposite side of a symmetric scene while keeping the
same up-vector inverts BOTH the near/far sense AND the apparent
left/right, since "forward" and "right" are coupled through the same
rotation), which would re-break the ALREADY-correct x-axis to fix y.
The correct fix mirrors ONLY the y (width) coordinate of every DYNAMIC
object (players, ball, Voronoi cells, the danger region, the
recommendation) before it is projected through the SAME unchanged
camera/homography -- `_mirror_y`/`_mirror_*` below, applied once, at
the top of `compose_radar_panel`. Static pitch markings
(`draw_pitch_markings_perspective`) need NO mirroring: a real pitch's
own markings (penalty box, centre circle, penalty spot) are already
symmetric about the width midline, so mirroring them has zero visible
effect -- only the asymmetric, per-frame DYNAMIC content needed
correcting. This is a coordinate-convention correction analogous to
`tactical_shared.coordinates.PitchConfig.own_goal()`'s own disclosed
"Team A's own goal is at x=length, not x=0" quirk -- not a cosmetic
pixel-space flip of the rendered image.
"""
import math

import cv2
import numpy as np

from tactical_shared.coordinates import DEFAULT_PITCH
from tactical_shared.perspective_radar import (
    DEFAULT_RADAR_CAMERA, compute_radar_homography, project_point_int, project_points,
    marker_scale_factor, draw_pitch_markings_perspective,
)
from offside_break.dashboard.render_offside_dashboard_v4_simple import (
    _draw_player_shadow, _draw_player_body_human, _heading_cue,
    HEADING_MIN_SPEED_CM_S, HEADING_LOOKAHEAD_SEC,
)
from sports.configs.soccer import SoccerPitchConfiguration
from dangerous_space_repositioning.dashboard.dashboard_style import (
    FONT, TEXT_WHITE, TEAM_COLOR, DANGER_COLOR, RECOMMEND_COLOR, BALL_COLOR, panel_title, draw_pill_label,
)

CONFIG = SoccerPitchConfiguration()
CANVAS_W_DEFAULT = 1300
CANVAS_H_DEFAULT = 800

# Visual hierarchy for SECONDARY (#2) / TERTIARY (#3) regions on the
# radar -- strictly fainter/smaller than the primary region's own
# `draw_danger_region_perspective`/`draw_recommendation_perspective`,
# scaled to this panel's own (smaller) marker sizes -- same convention
# `voronoi_broadcast_overlay.py`'s own EXTRA_REGION_STYLE follows for
# the Match Feed, just re-scaled for this panel's own pixel geometry.
EXTRA_REGION_STYLE_RADAR = {
    2: {"fill_alpha": 0.16, "ring_thickness": 1},
    3: {"fill_alpha": 0.09, "ring_thickness": 1},
}
EXTRA_RECOMMEND_STYLE_RADAR = {
    2: {"player_ring_r": 11, "target_ring_r": 7, "thickness": 1},
    3: {"player_ring_r": 8, "target_ring_r": 6, "thickness": 1},
}


def _mirror_y(y: float, pitch=DEFAULT_PITCH) -> float:
    """The single, documented radar/match-feed alignment correction
    (see this module's own docstring) -- flips ONLY the pitch-width
    coordinate so this radar's near/far sense matches the real
    broadcast camera's, for every dynamic object drawn."""
    return pitch.width_cm - y


def _mirror_point(pt, pitch=DEFAULT_PITCH):
    if pt is None:
        return None
    return (pt[0], _mirror_y(pt[1], pitch))


def _mirror_players(players: list[dict], pitch=DEFAULT_PITCH) -> list[dict]:
    """Mirrors position AND the y-component of velocity together --
    `vy_cm_s` is a real rate of change of `y_pitch`, so it must flip
    sign along with the position it describes, or a moving player's
    heading glyph would point the wrong way on this radar."""
    out = []
    for p in players:
        mirrored = {**p, "y_pitch": _mirror_y(p["y_pitch"], pitch)}
        if p.get("vy_cm_s") is not None:
            mirrored["vy_cm_s"] = -p["vy_cm_s"]
        out.append(mirrored)
    return out


def _mirror_ball(ball, pitch=DEFAULT_PITCH):
    if ball is None:
        return None
    return {**ball, "y_pitch": _mirror_y(ball["y_pitch"], pitch)}


def _mirror_voronoi(voronoi_result: dict, pitch=DEFAULT_PITCH) -> dict:
    if not voronoi_result.get("valid"):
        return voronoi_result
    mirrored_cells = [{**cell, "polygon": [(x, _mirror_y(y, pitch)) for x, y in cell["polygon"]]}
                       for cell in voronoi_result["cells"]]
    return {**voronoi_result, "cells": mirrored_cells}


def _project_poly(H, poly_cm):
    pts = project_points(H, poly_cm)
    return np.round(pts).astype(np.int32)


def draw_voronoi_perspective(img, H, voronoi_result: dict, alpha: float = 0.16):
    if not voronoi_result.get("valid"):
        return img
    overlay = img.copy()
    for cell in voronoi_result["cells"]:
        poly = _project_poly(H, np.array(cell["polygon"]))
        color = TEAM_COLOR.get(cell["team_id"], (180, 180, 180))
        cv2.fillPoly(overlay, [poly], color, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, dst=img)
    for cell in voronoi_result["cells"]:
        poly = _project_poly(H, np.array(cell["polygon"]))
        color = TEAM_COLOR.get(cell["team_id"], (180, 180, 180))
        cv2.polylines(img, [poly], True, color, 1, cv2.LINE_AA)
    return img


def draw_danger_region_perspective(img, H, x, y, area_cm2, pitch=DEFAULT_PITCH, color=DANGER_COLOR, label=None):
    r_cm = float(np.sqrt(max(area_cm2, 0.0) / np.pi))
    ang = np.linspace(0, 2 * np.pi, 40)
    circle_cm = np.array([(x + r_cm * np.cos(a), y + r_cm * np.sin(a)) for a in ang])
    poly = _project_poly(H, circle_cm)
    overlay = img.copy()
    cv2.fillPoly(overlay, [poly], color, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.32, img, 0.68, 0, dst=img)
    cv2.polylines(img, [poly], True, color, 2, cv2.LINE_AA)
    if label:
        cx, cy = project_point_int(H, x, y)
        draw_pill_label(img, cx - 10, cy - 14, label, color)
    return img


def draw_secondary_danger_region_perspective(img, H, x, y, area_cm2, rank, pitch=DEFAULT_PITCH, color=DANGER_COLOR):
    """Radar-panel equivalent of
    `voronoi_broadcast_overlay.draw_secondary_danger_region` -- same
    real `(x, y, area_cm2)` (already mirrored by the caller, exactly
    like the primary region), drawn fainter/smaller than the primary
    highlight so Danger #1 stays visually dominant on this panel too."""
    style = EXTRA_REGION_STYLE_RADAR.get(rank, EXTRA_REGION_STYLE_RADAR[3])
    r_cm = float(np.sqrt(max(area_cm2, 0.0) / np.pi))
    ang = np.linspace(0, 2 * np.pi, 40)
    circle_cm = np.array([(x + r_cm * np.cos(a), y + r_cm * np.sin(a)) for a in ang])
    poly = _project_poly(H, circle_cm)
    overlay = img.copy()
    cv2.fillPoly(overlay, [poly], color, cv2.LINE_AA)
    cv2.addWeighted(overlay, style["fill_alpha"], img, 1 - style["fill_alpha"], 0, dst=img)
    cv2.polylines(img, [poly], True, color, style["ring_thickness"], cv2.LINE_AA)
    cx, cy = project_point_int(H, x, y)
    draw_pill_label(img, cx - 8, cy - 12, f"#{rank}", color)
    return img


def draw_secondary_recommendation_perspective(img, H, player_x, player_y, target_x, target_y, rank,
                                               conflict=False, color=RECOMMEND_COLOR):
    """Radar-panel equivalent of
    `voronoi_broadcast_overlay.draw_secondary_recommendation` -- no
    spotlight (the radar panel has never had one; only the Match Feed
    does, per this project's own prior-round decision), just a smaller,
    subtler ring/dashed-line/target pair than the primary
    `draw_recommendation_perspective`."""
    style = EXTRA_RECOMMEND_STYLE_RADAR.get(rank, EXTRA_RECOMMEND_STYLE_RADAR[3])
    px, py = project_point_int(H, player_x, player_y)
    tx, ty = project_point_int(H, target_x, target_y)
    cv2.circle(img, (px, py), style["player_ring_r"], color, style["thickness"], cv2.LINE_AA)
    _dashed_line(img, (px, py), (tx, ty), color, style["thickness"])
    cv2.circle(img, (tx, ty), style["target_ring_r"], color, style["thickness"], cv2.LINE_AA)
    return img


def _dashed_line(img, p0, p1, color, thickness, dash_len=8, gap_len=6):
    x0, y0 = p0
    x1, y1 = p1
    dist = int(math.hypot(x1 - x0, y1 - y0))
    if dist == 0:
        return
    n_dashes = max(1, dist // (dash_len + gap_len))
    for i in range(n_dashes):
        t0 = i * (dash_len + gap_len) / dist
        t1 = min(1.0, (i * (dash_len + gap_len) + dash_len) / dist)
        sx, sy = int(x0 + (x1 - x0) * t0), int(y0 + (y1 - y0) * t0)
        ex, ey = int(x0 + (x1 - x0) * t1), int(y0 + (y1 - y0) * t1)
        cv2.line(img, (sx, sy), (ex, ey), color, thickness, cv2.LINE_AA)


def draw_players_perspective(img, H, team_a_players, team_b_players, pitch=DEFAULT_PITCH):
    """Human-footballer glyphs, shadow pass then body pass (matching
    the offside radar's own documented layering), sorted by screen-y so
    nearer glyphs correctly overlap farther ones."""
    all_players = [(0, p) for p in team_a_players] + [(1, p) for p in team_b_players]
    projected = []
    for team_id, p in all_players:
        px, py = project_point_int(H, p["x_pitch"], p["y_pitch"])
        scale = marker_scale_factor(H, p["x_pitch"], p["y_pitch"], pitch)
        projected.append((py, team_id, p, px, py, scale))
    projected.sort(key=lambda t: t[0])

    for _, team_id, p, px, py, scale in projected:
        _draw_player_shadow(img, px, py, scale=scale)

    for _, team_id, p, px, py, scale in projected:
        vx, vy = p.get("vx_cm_s") or 0.0, p.get("vy_cm_s") or 0.0
        speed = math.hypot(vx, vy)
        if speed < HEADING_MIN_SPEED_CM_S:
            mirror_sign, lean_x, lean_y = 1.0, 0.0, 0.0
        else:
            # Screen-space heading sample from the player's own CAUSAL
            # velocity, projected the SAME way every other point on this
            # radar is -- never a future tracked position (see
            # HEADING_LOOKAHEAD_SEC's own docstring in the offside
            # module: a small forward TIME-STEP applied to an already-
            # known PAST/current velocity, not a peek at a future frame).
            fx = p["x_pitch"] + vx * HEADING_LOOKAHEAD_SEC
            fy = p["y_pitch"] + vy * HEADING_LOOKAHEAD_SEC
            fpx, fpy = project_point_int(H, fx, fy)
            mirror_sign, lean_x, lean_y = _heading_cue(fpx - px, fpy - py)
        color = TEAM_COLOR.get(team_id, (180, 180, 180))
        _draw_player_body_human(img, px, py, color, scale=scale, mirror_sign=mirror_sign, lean=(lean_x, lean_y))
    return img


def draw_ball_perspective(img, H, ball):
    if ball is None:
        return img
    px, py = project_point_int(H, ball["x_pitch"], ball["y_pitch"])
    cv2.circle(img, (px, py), 5, BALL_COLOR, -1, cv2.LINE_AA)
    cv2.circle(img, (px, py), 5, (15, 15, 15), 1, cv2.LINE_AA)
    return img


def draw_recommendation_perspective(img, H, player_x, player_y, target_x, target_y):
    px, py = project_point_int(H, player_x, player_y)
    tx, ty = project_point_int(H, target_x, target_y)
    cv2.circle(img, (px, py), 16, RECOMMEND_COLOR, 2, cv2.LINE_AA)
    _dashed_line(img, (px, py), (tx, ty), RECOMMEND_COLOR, 2)
    cv2.arrowedLine(img, ((px + tx) // 2, (py + ty) // 2), (tx, ty), RECOMMEND_COLOR, 2, cv2.LINE_AA, tipLength=0.4)
    cv2.circle(img, (tx, ty), 10, RECOMMEND_COLOR, 2, cv2.LINE_AA)
    return img


def compose_radar_panel(w, h, team_a_players, team_b_players, ball, voronoi_result: dict,
                         danger_point, danger_area_cm2, defending_team, threat,
                         recommend_from, recommend_to, pitch=DEFAULT_PITCH,
                         camera=DEFAULT_RADAR_CAMERA, extra_regions: list | None = None) -> np.ndarray:
    """`extra_regions`: same shape as
    `voronoi_broadcast_overlay.compose_match_feed_panel`'s own
    `extra_regions` -- 0-2 dicts for the SECONDARY/TERTIARY distinct
    regions, in REAL (unmirrored) pitch coordinates; mirrored here
    exactly like every other dynamic object on this panel."""
    # RADAR ALIGNMENT FIX (see this module's own docstring): mirror the
    # pitch-WIDTH (y) coordinate of every DYNAMIC object, once, right
    # here -- before anything is projected -- so this radar's near/far
    # sense matches the real broadcast camera's for this video. The
    # camera/homography itself (and the static pitch markings) are
    # UNCHANGED; only the world-space input is corrected.
    team_a_players = _mirror_players(team_a_players, pitch)
    team_b_players = _mirror_players(team_b_players, pitch)
    ball = _mirror_ball(ball, pitch)
    voronoi_result = _mirror_voronoi(voronoi_result, pitch)
    danger_point = _mirror_point(danger_point, pitch)
    recommend_from = _mirror_point(recommend_from, pitch)
    recommend_to = _mirror_point(recommend_to, pitch)
    mirrored_extra = []
    for reg in (extra_regions or []):
        mx, my = _mirror_point((reg["x"], reg["y"]), pitch)
        mirrored_extra.append({
            **reg, "x": mx, "y": my,
            "fixer_xy": _mirror_point(reg.get("fixer_xy"), pitch),
            "target_xy": _mirror_point(reg.get("target_xy"), pitch),
        })

    canvas_w, canvas_h = CANVAS_W_DEFAULT, CANVAS_H_DEFAULT
    H = compute_radar_homography(pitch, camera, canvas_w, canvas_h)
    base = draw_pitch_markings_perspective(H, CONFIG, canvas_w, canvas_h)
    pitch_dark = cv2.addWeighted(base, 0.78, np.zeros_like(base), 0.22, 0)

    pitch_dark = draw_voronoi_perspective(pitch_dark, H, voronoi_result)

    # Extra regions are drawn BEFORE the primary one so the primary
    # always renders on top wherever they might visually overlap --
    # same ordering rule as the Match Feed panel.
    for reg in mirrored_extra:
        pitch_dark = draw_secondary_danger_region_perspective(pitch_dark, H, reg["x"], reg["y"],
                                                                reg["area_cm2"], reg["rank"], pitch)

    if danger_point is not None:
        pitch_dark = draw_danger_region_perspective(pitch_dark, H, danger_point[0], danger_point[1],
                                                     danger_area_cm2, pitch, label="Dangerous space")
    pitch_dark = draw_players_perspective(pitch_dark, H, team_a_players, team_b_players, pitch)
    pitch_dark = draw_ball_perspective(pitch_dark, H, ball)

    for reg in mirrored_extra:
        if reg.get("fixer_xy") is not None and reg.get("target_xy") is not None:
            pitch_dark = draw_secondary_recommendation_perspective(
                pitch_dark, H, reg["fixer_xy"][0], reg["fixer_xy"][1], reg["target_xy"][0], reg["target_xy"][1],
                reg["rank"], conflict=reg.get("conflict", False))

    if recommend_from is not None and recommend_to is not None:
        pitch_dark = draw_recommendation_perspective(pitch_dark, H, recommend_from[0], recommend_from[1],
                                                       recommend_to[0], recommend_to[1])
    if danger_point is not None and threat is not None:
        cx, cy = project_point_int(H, danger_point[0], danger_point[1])
        draw_pill_label(pitch_dark, cx - 10, cy + 26, f"Opponent control {threat:.0%}", DANGER_COLOR)

    out = np.full((h, w, 3), (28, 22, 18), dtype=np.uint8)
    resized = cv2.resize(pitch_dark, (w, h - 34))
    out[34:h, 0:w] = resized
    panel_title(out, "3D TACTICAL RADAR", sub="Same moment, perspective view -- Voronoi view only")
    return out
