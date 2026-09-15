"""
Tests for the 24-second graph rolling window (widened from 20s this
round -- formulas/smoothing/decimation UNCHANGED, see HANDOFF.md).
"""
import numpy as np

from dangerous_space_repositioning.dashboard.render_dangerous_space_dashboard import (
    COACH_WINDOW_SEC, COACH_TICK_SEC, SEVERITY_EMA_ALPHA, OPPONENT_CONTROL_EMA_ALPHA,
    SPATIAL_BALANCE_EMA_ALPHA,
)
from dangerous_space_repositioning.dashboard.live_graphs import draw_severity_graph, MAX_GAP_SEC, _to_px
from dangerous_space_repositioning.dashboard.dashboard_style import TEAM_COLOR


def test_graph_window_is_24_seconds():
    assert COACH_WINDOW_SEC == 24.0


def test_tick_spacing_unchanged_at_4_seconds():
    assert COACH_TICK_SEC == 4.0


def test_smoothing_alphas_unchanged_this_round():
    """This round explicitly widens the WINDOW only -- every display
    smoothing alpha must be untouched from the prior (20s) round."""
    assert SEVERITY_EMA_ALPHA == 0.6
    assert OPPONENT_CONTROL_EMA_ALPHA == 0.15
    assert SPATIAL_BALANCE_EMA_ALPHA == 0.5


def _has_color_in_column(img, x0, x1, color, tolerance=40):
    """Whether a specific drawn color (e.g. a team's own line color, or
    the white NOW-cursor) appears ANYWHERE in the given column range --
    robust to gridlines/background (which use different, unrelated
    colors) and to anti-aliasing (a generous per-channel tolerance)."""
    col = img[:, x0:x1].astype(int)
    target = np.array(color, dtype=int)
    diff = np.abs(col - target).sum(axis=2)
    return (diff < tolerance).any()


def test_now_cursor_is_pinned_at_the_right_edge_of_a_24s_window():
    """The NOW cursor is drawn at `_to_px(cur_time, ...)` -- with
    `cur_time == t_hi` (always true in production: the graphs are drawn
    with `cur_time=t_hi=frame/fps`), this must land exactly at the
    plot's own right edge (`x0 + pw`), regardless of window width."""
    t_hi = 100.0
    t_lo = t_hi - COACH_WINDOW_SEC
    pad_l, pad_r, pad_t, pad_b = 46, 14, 52, 34
    w, h = 700, 538
    x0, y0 = pad_l, pad_t
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    cx, _ = _to_px(t_hi, 0.0, t_lo, t_hi, 0.0, 1.0, x0, y0, pw, ph)
    assert cx == x0 + pw == w - pad_r


def test_real_gap_breaks_the_line_over_a_24s_window():
    """A real missing-data gap wider than MAX_GAP_SEC must leave a
    visibly blank stretch (no team-colored line drawn), never an
    interpolated line across it -- unchanged behavior, re-verified at
    the new 24s window width."""
    t_hi = 100.0
    t_lo = t_hi - COACH_WINDOW_SEC
    mid = (t_lo + t_hi) / 2.0
    gap_half_width = MAX_GAP_SEC * 3  # comfortably wider than the real-gap threshold
    hist_a = (
        [(t_lo + i * 0.2, 0.4) for i in range(int((mid - gap_half_width - t_lo) / 0.2))] +
        [(mid, None)] +
        [(mid + gap_half_width + i * 0.2, 0.4) for i in range(int((t_hi - mid - gap_half_width) / 0.2))]
    )
    hist_b = [(t, None) for t, _ in hist_a]
    img = draw_severity_graph(700, 538, hist_a, hist_b, t_hi, t_lo, t_hi, COACH_TICK_SEC)

    pad_l, pad_r = 46, 14
    x0, pw = pad_l, 700 - pad_l - pad_r
    gap_frac = (mid - t_lo) / (t_hi - t_lo)
    gap_x = x0 + int(pw * gap_frac)
    before_x = x0 + int(pw * ((mid - gap_half_width - 2.0 - t_lo) / (t_hi - t_lo)))
    # Team A's own line color must be present well before the gap...
    assert _has_color_in_column(img, before_x - 2, before_x + 2, TEAM_COLOR[0])
    # ...but absent in a narrow column centered on the real gap itself,
    # even though real data exists on both sides of it.
    assert not _has_color_in_column(img, gap_x - 2, gap_x + 2, TEAM_COLOR[0])
