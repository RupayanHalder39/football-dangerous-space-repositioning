"""
Row 1, LEFT panel: Voronoi drawn DIRECTLY on the real broadcast frame.

Analytics are always computed in real pitch coordinates (cm) --
`analytics.voronoi`, `dangerous_space.py`, `opponent_access.py`,
`player_responsibility.py`, `counterfactual_repositioning.py` never
see a screen pixel. This module's only job is projecting already-
computed pitch-plane results (cell polygons, the danger region, the
recommended player, the suggested move) onto the broadcast image via
the SAME per-frame homography the tracking pipeline itself already
computed and persisted (`outputs/analytics/testVideo1_120s_v3/
homography_transformers.pkl`) -- never a second, independently-fit
transform.
"""
import cv2
import numpy as np

from dangerous_space_repositioning.dashboard.dashboard_style import (
    FONT, TEXT_WHITE, TEAM_COLOR, DANGER_COLOR, RECOMMEND_COLOR, BALL_COLOR, GHOST_COLOR, panel_title,
    composite_badge, draw_pill_label,
)

# Visual hierarchy for the SECONDARY (#2) / TERTIARY (#3) dangerous
# regions -- always strictly fainter/smaller than the PRIMARY (#1)
# region's own `draw_danger_region`/`draw_recommendation`/
# `draw_recommendation_spotlight` styling, per this round's explicit
# "Danger #1 must always be obvious as the primary problem" requirement.
EXTRA_REGION_STYLE = {
    2: {"fill_alpha": 0.16, "ring_thickness": 1},
    3: {"fill_alpha": 0.09, "ring_thickness": 1},
}
EXTRA_RECOMMEND_STYLE = {
    2: {"player_ring_r": 15, "target_ring_r": 10, "thickness": 1, "spotlight_scale": 0.6},
    3: {"player_ring_r": 11, "target_ring_r": 8, "thickness": 1, "spotlight_scale": 0.4},
}


def nearest_transformer(transformers: dict, f: int, window: int = 10):
    """Same tolerant nearest-frame lookup `pressing_structure`/
    `offside_break` already use -- a homography can legitimately be
    unavailable for a handful of frames (motion blur, a cut, a
    replay); reusing the closest real one within `window` frames is
    better than leaving the whole overlay blank, and never claims
    higher precision than a same-instant homography would give."""
    if transformers.get(f) is not None:
        return transformers[f]
    for d in range(1, window + 1):
        if transformers.get(f - d) is not None:
            return transformers[f - d]
        if transformers.get(f + d) is not None:
            return transformers[f + d]
    return None


def pitch_to_image(transformer, pts_cm: np.ndarray) -> np.ndarray | None:
    """`pts_cm`: (N, 2) float array of real pitch (x_pitch, y_pitch) cm
    points. Returns (N, 2) image-pixel points, or None if this frame's
    homography is unavailable/singular -- callers must skip drawing
    rather than guess."""
    if transformer is None or len(pts_cm) == 0:
        return None
    try:
        inv_m = np.linalg.inv(transformer.m)
    except np.linalg.LinAlgError:
        return None
    pts = np.asarray(pts_cm, dtype=np.float32).reshape(-1, 1, 2)
    img_pts = cv2.perspectiveTransform(pts, inv_m).reshape(-1, 2)
    return img_pts


def draw_voronoi_on_frame(frame: np.ndarray, transformer, voronoi_result: dict, alpha: float = 0.13) -> np.ndarray:
    """Restrained team-colored Voronoi fills + clear cell boundaries --
    "visible but readable" per this project's own brief, not a solid
    wash. Cells whose polygon can't be projected this frame (no
    homography) are silently skipped, never approximated."""
    if not voronoi_result.get("valid") or transformer is None:
        return frame
    overlay = frame.copy()
    for cell in voronoi_result["cells"]:
        pts_img = pitch_to_image(transformer, np.array(cell["polygon"]))
        if pts_img is None:
            continue
        poly = np.round(pts_img).astype(np.int32)
        color = TEAM_COLOR.get(cell["team_id"], (180, 180, 180))
        cv2.fillPoly(overlay, [poly], color, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)
    for cell in voronoi_result["cells"]:
        pts_img = pitch_to_image(transformer, np.array(cell["polygon"]))
        if pts_img is None:
            continue
        poly = np.round(pts_img).astype(np.int32)
        color = TEAM_COLOR.get(cell["team_id"], (180, 180, 180))
        cv2.polylines(frame, [poly], True, color, 1, cv2.LINE_AA)
    return frame


def draw_danger_region(frame: np.ndarray, transformer, x: float, y: float, area_cm2: float,
                        color=DANGER_COLOR, label: str | None = None) -> np.ndarray:
    """A soft highlighted disc at the flagged region's centroid, radius
    derived from the REAL cell area (never a fixed decorative size) --
    `r = sqrt(area / pi)`, i.e. the radius of a circle with the same
    area as the real flagged cell."""
    if transformer is None:
        return frame
    r_cm = float(np.sqrt(max(area_cm2, 0.0) / np.pi))
    n = 40
    ang = np.linspace(0, 2 * np.pi, n)
    circle_cm = np.array([(x + r_cm * np.cos(a), y + r_cm * np.sin(a)) for a in ang])
    pts_img = pitch_to_image(transformer, circle_cm)
    if pts_img is None:
        return frame
    poly = np.round(pts_img).astype(np.int32)
    overlay = frame.copy()
    cv2.fillPoly(overlay, [poly], color, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.30, frame, 0.70, 0, dst=frame)
    cv2.polylines(frame, [poly], True, color, 2, cv2.LINE_AA)
    center_img = pitch_to_image(transformer, np.array([[x, y]]))
    if center_img is not None and label:
        cx, cy = np.round(center_img[0]).astype(int)
        draw_pill_label(frame, cx - 10, cy - 14, label, color)
    return frame


def draw_secondary_danger_region(frame: np.ndarray, transformer, x: float, y: float, area_cm2: float,
                                  rank: int, color=DANGER_COLOR) -> np.ndarray:
    """A fainter, lower-opacity danger-region highlight for a
    SECONDARY (rank=2) / TERTIARY (rank=3) distinct dangerous region --
    the identical real `(x, y, area_cm2)` computed by
    `analytics.multi_region.select_top_regions`, drawn strictly less
    prominently (lower fill alpha, thinner ring, a small "#2"/"#3"
    marker instead of the full "Dangerous space" + opponent-control
    callout) than the PRIMARY region's own `draw_danger_region`, so it
    never competes for the viewer's attention with Danger #1."""
    if transformer is None:
        return frame
    style = EXTRA_REGION_STYLE.get(rank, EXTRA_REGION_STYLE[3])
    r_cm = float(np.sqrt(max(area_cm2, 0.0) / np.pi))
    n = 40
    ang = np.linspace(0, 2 * np.pi, n)
    circle_cm = np.array([(x + r_cm * np.cos(a), y + r_cm * np.sin(a)) for a in ang])
    pts_img = pitch_to_image(transformer, circle_cm)
    if pts_img is None:
        return frame
    poly = np.round(pts_img).astype(np.int32)
    overlay = frame.copy()
    cv2.fillPoly(overlay, [poly], color, cv2.LINE_AA)
    cv2.addWeighted(overlay, style["fill_alpha"], frame, 1 - style["fill_alpha"], 0, dst=frame)
    cv2.polylines(frame, [poly], True, color, style["ring_thickness"], cv2.LINE_AA)
    center_img = pitch_to_image(transformer, np.array([[x, y]]))
    if center_img is not None:
        cx, cy = np.round(center_img[0]).astype(int)
        draw_pill_label(frame, cx - 8, cy - 12, f"#{rank}", color)
    return frame


def draw_secondary_recommendation(frame: np.ndarray, transformer, player_x: float, player_y: float,
                                   target_x: float, target_y: float, rank: int,
                                   conflict: bool = False, color=RECOMMEND_COLOR) -> np.ndarray:
    """A smaller, subtler fixer marker + movement cue for a
    SECONDARY/TERTIARY region's assigned fixer -- reuses
    `draw_recommendation_spotlight` at a reduced size/height (see
    `EXTRA_RECOMMEND_STYLE`) so every rank gets the same spotlight
    language, just strictly less prominent than Danger #1's own."""
    if transformer is None:
        return frame
    style = EXTRA_RECOMMEND_STYLE.get(rank, EXTRA_RECOMMEND_STYLE[3])
    pts_img = pitch_to_image(transformer, np.array([[player_x, player_y], [target_x, target_y]]))
    if pts_img is None:
        return frame
    (px, py), (tx, ty) = np.round(pts_img).astype(int)

    scale = style["spotlight_scale"]
    frame = draw_recommendation_spotlight(frame, px, py, height_px=int(78 * scale),
                                           radius_px=max(6, int(15 * scale)), color=color)
    cv2.circle(frame, (px, py), style["player_ring_r"], color, style["thickness"], cv2.LINE_AA)
    _dashed_line(frame, (px, py), (tx, ty), color, style["thickness"])
    cv2.circle(frame, (tx, ty), style["target_ring_r"], color, style["thickness"], cv2.LINE_AA)
    label = f"#{rank} fixer" + (" (reassigned)" if conflict else "")
    draw_pill_label(frame, px - 20, py - 26, label, color)
    return frame


def draw_recommendation_spotlight(frame: np.ndarray, px: int, py: int,
                                   height_px: int = 78, radius_px: int = 15,
                                   color=RECOMMEND_COLOR) -> np.ndarray:
    """A faint cyan spotlight -- a translucent cylindrical beam rising
    from the recommended player's ground position, with a soft glow at
    its base. Purely a Match-Feed visual cue ("this is the player to
    fix"); it carries no data of its own, so its only job is to stay
    subtle. Drawn as a stack of same-radius (cylindrical, not tapering)
    translucent bands whose alpha fades going up, so it reads as a
    soft light column rather than a solid shape. The base uses a
    flattened ellipse (foreshortened, matching how a real circle on
    the pitch looks from this broadcast camera's angle) rather than a
    circle, so it sits naturally on the ground plane instead of
    floating as a flat screen-space disc."""
    overlay = frame.copy()
    n_bands = 10
    for i in range(n_bands):
        frac_lo, frac_hi = i / n_bands, (i + 1) / n_bands
        y_lo = py - int(height_px * frac_lo)
        y_hi = py - int(height_px * frac_hi)
        band_alpha = 0.16 * (1.0 - frac_lo) ** 1.4
        pts = np.array([[px - radius_px, y_lo], [px + radius_px, y_lo],
                         [px + radius_px, y_hi], [px - radius_px, y_hi]], dtype=np.int32)
        band = overlay.copy()
        cv2.fillConvexPoly(band, pts, color, cv2.LINE_AA)
        cv2.addWeighted(band, band_alpha, overlay, 1 - band_alpha, 0, dst=overlay)
    glow = overlay.copy()
    cv2.ellipse(glow, (px, py), (radius_px + 10, max(5, radius_px // 2)), 0, 0, 360, color, -1, cv2.LINE_AA)
    cv2.addWeighted(glow, 0.14, overlay, 0.86, 0, dst=overlay)
    frame[:] = overlay
    return frame


def draw_recommendation(frame: np.ndarray, transformer, player_x: float, player_y: float,
                         target_x: float, target_y: float,
                         player_label: str = "Best player to fix", move_label: str = "Suggested move") -> np.ndarray:
    """Cyan ring on the recommended player, a dashed connector, and a
    ring at the suggested destination -- matches the attached reference
    mockup's own "3 Best player to fix" / "4 Suggested move" language.
    Also draws the faint cyan spotlight beam (see
    `draw_recommendation_spotlight`) under the player's ring -- both
    are gated on the exact same caller-side "a valid recommendation
    exists this frame" condition, so the spotlight inherits the same
    display-stability guarantees (tracks the stabilized player, switches
    cleanly, disappears immediately on UNCERTAIN) with no separate state
    machine of its own."""
    if transformer is None:
        return frame
    pts_img = pitch_to_image(transformer, np.array([[player_x, player_y], [target_x, target_y]]))
    if pts_img is None:
        return frame
    (px, py), (tx, ty) = np.round(pts_img).astype(int)

    frame = draw_recommendation_spotlight(frame, px, py)
    cv2.circle(frame, (px, py), 22, RECOMMEND_COLOR, 2, cv2.LINE_AA)
    _dashed_line(frame, (px, py), (tx, ty), RECOMMEND_COLOR, 2)
    cv2.arrowedLine(frame, ((px + tx) // 2, (py + ty) // 2), (tx, ty), RECOMMEND_COLOR, 2, cv2.LINE_AA, tipLength=0.35)
    cv2.circle(frame, (tx, ty), 14, RECOMMEND_COLOR, 2, cv2.LINE_AA)

    draw_pill_label(frame, px - 30, py - 30, player_label, RECOMMEND_COLOR)
    draw_pill_label(frame, tx - 20, ty + 46, move_label, RECOMMEND_COLOR)
    return frame


def draw_opponent_control_label(frame: np.ndarray, transformer, x: float, y: float, threat: float) -> np.ndarray:
    center_img = pitch_to_image(transformer, np.array([[x, y]]))
    if center_img is None:
        return frame
    cx, cy = np.round(center_img[0]).astype(int)
    draw_pill_label(frame, cx - 10, cy + 22, f"Opponent control {threat:.0%}", DANGER_COLOR)
    return frame


def _dashed_line(img, p0, p1, color, thickness, dash_len=10, gap_len=7):
    x0, y0 = p0
    x1, y1 = p1
    dist = int(np.hypot(x1 - x0, y1 - y0))
    if dist == 0:
        return
    n_dashes = max(1, dist // (dash_len + gap_len))
    for i in range(n_dashes):
        t0 = i * (dash_len + gap_len) / dist
        t1 = min(1.0, (i * (dash_len + gap_len) + dash_len) / dist)
        sx, sy = int(x0 + (x1 - x0) * t0), int(y0 + (y1 - y0) * t0)
        ex, ey = int(x0 + (x1 - x0) * t1), int(y0 + (y1 - y0) * t1)
        cv2.line(img, (sx, sy), (ex, ey), color, thickness, cv2.LINE_AA)


def draw_players_and_ball(frame: np.ndarray, transformer, team_a_players: list[dict], team_b_players: list[dict],
                           ball) -> np.ndarray:
    for team_id, players in ((0, team_a_players), (1, team_b_players)):
        pts_cm = np.array([[p["x_pitch"], p["y_pitch"]] for p in players]) if players else np.zeros((0, 2))
        pts_img = pitch_to_image(transformer, pts_cm)
        if pts_img is None:
            continue
        color = TEAM_COLOR[team_id]
        for (px, py) in np.round(pts_img).astype(int):
            cv2.circle(frame, (px, py), 4, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 4, (12, 12, 12), 1, cv2.LINE_AA)
    if ball is not None:
        pt = pitch_to_image(transformer, np.array([[ball["x_pitch"], ball["y_pitch"]]]))
        if pt is not None:
            px, py = np.round(pt[0]).astype(int)
            cv2.circle(frame, (px, py), 4, BALL_COLOR, -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 4, (15, 15, 15), 1, cv2.LINE_AA)
    return frame


def compose_match_feed_panel(frame: np.ndarray, w: int, h: int, transformer, voronoi_result: dict,
                              team_a_players: list, team_b_players: list, ball,
                              danger_point: tuple | None, danger_area_cm2: float, defending_team: int,
                              threat: float | None,
                              recommend_from: tuple | None, recommend_to: tuple | None,
                              status_title: str, status_subtitle: str, status_color,
                              extra_regions: list | None = None) -> np.ndarray:
    """`extra_regions`: 0-2 dicts for the SECONDARY/TERTIARY distinct
    dangerous regions (see `analytics.multi_region.select_top_regions` +
    `assign_regions_and_fixers`), each shaped
    `{"rank": 2|3, "x", "y", "area_cm2", "fixer_xy": (x,y)|None,
    "target_xy": (x,y)|None, "conflict": bool, "reason": str|None}`.
    Drawn strictly fainter/smaller than the PRIMARY region so Danger #1
    always reads as the obvious main problem -- see
    `draw_secondary_danger_region`/`draw_secondary_recommendation`."""
    vis = frame.copy()
    vis = draw_voronoi_on_frame(vis, transformer, voronoi_result)

    # Extra regions are drawn BEFORE the primary one so the primary
    # always renders on top wherever they might visually overlap.
    for reg in (extra_regions or []):
        vis = draw_secondary_danger_region(vis, transformer, reg["x"], reg["y"], reg["area_cm2"], reg["rank"])

    if danger_point is not None:
        vis = draw_danger_region(vis, transformer, danger_point[0], danger_point[1], danger_area_cm2,
                                  label="Dangerous space")
    vis = draw_players_and_ball(vis, transformer, team_a_players, team_b_players, ball)
    if danger_point is not None and threat is not None:
        vis = draw_opponent_control_label(vis, transformer, danger_point[0], danger_point[1], threat)

    for reg in (extra_regions or []):
        if reg.get("fixer_xy") is not None and reg.get("target_xy") is not None:
            vis = draw_secondary_recommendation(vis, transformer, reg["fixer_xy"][0], reg["fixer_xy"][1],
                                                 reg["target_xy"][0], reg["target_xy"][1], reg["rank"],
                                                 conflict=reg.get("conflict", False))
        elif reg.get("reason"):
            center_img = pitch_to_image(transformer, np.array([[reg["x"], reg["y"]]]))
            if center_img is not None:
                cx, cy = np.round(center_img[0]).astype(int)
                draw_pill_label(vis, cx - 10, cy + 44, f"#{reg['rank']}: {reg['reason']}", GHOST_COLOR)

    if recommend_from is not None and recommend_to is not None:
        vis = draw_recommendation(vis, transformer, recommend_from[0], recommend_from[1],
                                   recommend_to[0], recommend_to[1])

    vis = composite_badge(vis, 10, 10, status_title, status_color, status_subtitle, w=460)
    out = np.full((vis.shape[0] + 32, vis.shape[1], 3), (28, 22, 18), dtype=np.uint8)
    out[32:, :] = vis
    panel_title(out, "TACTICAL MATCH FEED", sub="Real broadcast frame + Voronoi + dangerous-space overlay")
    return cv2.resize(out, (w, h))
