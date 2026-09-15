"""
Tests for the grouped (non-stacked) Danger #1/#2/#3 bar rendering
(`dashboard/live_graphs._draw_region_bar` /
`_draw_grouped_region_bars`) -- the redesign that replaced Graph 1's
stacked-sum bars and Graph 2's dominant-bar-plus-tick-marks with SIX
fully independent bars per bucket (Team A x 3 ranks, Team B x 3 ranks).

`bucket_region_history`'s own aggregation rules are UNCHANGED this
round and already covered by `tests/test_graph_bucketing.py`; these
tests exercise only the NEW rendering/layout behavior, as direct pixel
inspection of small synthetic canvases (no video, no real match data).
"""
import numpy as np

from dangerous_space_repositioning.dashboard.dashboard_style import PANEL_BG, TEAM_COLOR, RECOMMEND_COLOR
from dangerous_space_repositioning.dashboard.live_graphs import (
    _draw_region_bar, _draw_grouped_region_bars, _shade, RANK_SHADE, RANK_WIDTH_MULT,
    _bucket_axis_labels, draw_severity_bar_graph, draw_opponent_access_bar_graph,
)


def _blank_canvas(w=300, h=220):
    return np.full((h, w, 3), PANEL_BG, dtype=np.uint8)


def _topmost_colored_row(img, x, bar_w, bg=PANEL_BG, tol=5):
    """First row (from the top) where the given column range differs
    from the background -- i.e. the top edge of whatever was drawn
    there, or `None` if the whole column range is still background."""
    col = img[:, x:x + bar_w].astype(int)
    bg_arr = np.array(bg, dtype=int)
    diff = np.abs(col - bg_arr).sum(axis=2).max(axis=1)
    hit = np.where(diff > tol)[0]
    return int(hit[0]) if len(hit) else None


def test_equal_values_produce_equal_bar_heights_never_stacked():
    """Three bars drawn with the IDENTICAL value must reach the
    IDENTICAL height -- if Danger #2/#3 were still being stacked on top
    of #1 (the old design), the second and third bars would start
    progressively higher (lower row index) than the first."""
    img = _blank_canvas()
    y0, ph, bar_w = 10, 180, 15
    tops = []
    for i, x in enumerate((20, 60, 100)):
        _draw_region_bar(img, x, y0, ph, bar_w, 0.5, TEAM_COLOR[0], 0.0, 1.0)
        tops.append(_topmost_colored_row(img, x, bar_w))
    assert all(t is not None for t in tops)
    assert tops[0] == tops[1] == tops[2], "equal values must produce equal bar heights -- no stacking"


def test_larger_value_never_exceeds_the_axis_even_when_drawn_independently():
    """A rank-3 bar drawn with a LARGE value on its own must reach
    (approximately) the same height as a rank-1 bar with the SAME
    value -- confirming heights are computed independently against the
    fixed [0,1] axis, never as a running cumulative sum."""
    img = _blank_canvas()
    y0, ph, bar_w = 10, 180, 15
    _draw_region_bar(img, 20, y0, ph, bar_w, 0.9, TEAM_COLOR[1], 0.0, 1.0)
    top_alone = _topmost_colored_row(img, 20, bar_w)

    img2 = _blank_canvas()
    # Two OTHER bars with real values drawn first, at DIFFERENT x
    # positions -- must not affect a third bar's own height.
    _draw_region_bar(img2, 20, y0, ph, bar_w, 0.9, TEAM_COLOR[1], 0.0, 1.0)
    _draw_region_bar(img2, 40, y0, ph, bar_w, 0.9, TEAM_COLOR[1], 0.0, 1.0)
    _draw_region_bar(img2, 60, y0, ph, bar_w, 0.9, TEAM_COLOR[1], 0.0, 1.0)
    top_with_neighbors = _topmost_colored_row(img2, 20, bar_w)
    assert top_alone == top_with_neighbors


def test_missing_value_draws_hatch_not_a_solid_team_colored_bar():
    img = _blank_canvas()
    y0, ph, bar_w = 10, 180, 15
    _draw_region_bar(img, 20, y0, ph, bar_w, None, TEAM_COLOR[0], 0.0, 1.0)
    col = img[:, 20:20 + bar_w].reshape(-1, 3)
    team_color = np.array(TEAM_COLOR[0])
    solid_team_pixels = np.all(np.abs(col.astype(int) - team_color) < 5, axis=1).sum()
    assert solid_team_pixels == 0, "a missing region must never render as a solid team-colored fill"


def test_real_zero_draws_no_visible_bar_and_no_hatch():
    """A real, confirmed zero (context known, this rank genuinely absent)
    must be visually EMPTY -- neither a solid bar nor a hatched
    placeholder, since it is a confident measurement, not uncertainty."""
    img = _blank_canvas()
    y0, ph, bar_w = 10, 180, 15
    _draw_region_bar(img, 20, y0, ph, bar_w, 0.0, TEAM_COLOR[0], 0.0, 1.0)
    assert _topmost_colored_row(img, 20, bar_w) is None


def test_rank_shades_are_three_distinct_colors():
    base = TEAM_COLOR[0]
    shades = {_shade(base, RANK_SHADE[r]) for r in range(3)}
    assert len(shades) == 3, "Danger #1/#2/#3 must be visually distinguishable shades of the same team color"


def test_team_a_bars_are_strictly_left_of_team_b_bars_in_the_same_bucket():
    """Team A's own 3 bars and Team B's own 3 bars must occupy disjoint,
    ordered x-ranges within one bucket group -- the team-level grouping
    the redesign explicitly requires."""
    img = _blank_canvas(w=300, h=220)
    x0, y0, pw, ph = 10, 10, 280, 180
    bucket_a = {"rank_severity": [0.6, 0.6, 0.6], "n_defined_samples": 100}
    bucket_b = {"rank_severity": [0.6, 0.6, 0.6], "n_defined_samples": 100}
    _draw_grouped_region_bars(img, x0, y0, pw, ph, 1, [bucket_a], [bucket_b], "rank_severity", 0.0, 1.0)

    row = img[y0 + ph - 5, x0:x0 + pw].astype(int)
    team_a_color = np.array(TEAM_COLOR[0])
    team_b_color = np.array(TEAM_COLOR[1])
    is_a = np.abs(row - team_a_color).sum(axis=1) < 30
    is_b = np.abs(row - team_b_color).sum(axis=1) < 30
    a_cols = np.where(is_a)[0]
    b_cols = np.where(is_b)[0]
    assert len(a_cols) > 0 and len(b_cols) > 0
    assert a_cols.max() < b_cols.min(), "Team A's bars must all sit to the left of Team B's bars in the same bucket"


def test_graph2_style_bars_do_not_sum_across_ranks():
    """Graph 2's own access bars must behave identically to Graph 1's --
    each rank's own bar reaches its own real height, never a combined
    total exceeding any single real value."""
    img = _blank_canvas()
    y0, ph, bar_w = 10, 180, 15
    for x in (20, 60, 100):
        _draw_region_bar(img, x, y0, ph, bar_w, 0.8, TEAM_COLOR[1], 0.0, 1.0)
    tops = [_topmost_colored_row(img, x, bar_w) for x in (20, 60, 100)]
    assert tops[0] == tops[1] == tops[2]
    # None of the three bars may reach higher (a smaller top-row index)
    # than a single bar drawn alone with the SAME value would.
    img_alone = _blank_canvas()
    _draw_region_bar(img_alone, 20, y0, ph, bar_w, 0.8, TEAM_COLOR[1], 0.0, 1.0)
    assert tops[0] == _topmost_colored_row(img_alone, 20, bar_w)


def test_zero_buckets_is_a_safe_noop():
    img = _blank_canvas()
    _draw_grouped_region_bars(img, 10, 10, 280, 180, 0, [], [], "rank_severity", 0.0, 1.0)  # must not raise


# ---------------------------------------------------------------- final presentation polish (D1 width / LIVE / fixed axis)

def _bar_column_span(img, y, x_search_range, color, tol=30):
    """The [first, last] x columns at row `y` matching `color` within
    `x_search_range` -- used to measure a drawn bar's own pixel width
    without hardcoding its expected position."""
    row = img[y, x_search_range[0]:x_search_range[1]].astype(int)
    target = np.array(color, dtype=int)
    matches = np.where(np.abs(row - target).sum(axis=1) < tol)[0]
    if len(matches) == 0:
        return None
    return matches[0] + x_search_range[0], matches[-1] + x_search_range[0]


def test_danger1_bar_is_wider_than_danger2_and_danger3():
    img = _blank_canvas(w=300, h=220)
    x0, y0, pw, ph = 10, 10, 280, 180
    bucket = {"rank_severity": [0.9, 0.9, 0.9], "n_defined_samples": 100}
    _draw_grouped_region_bars(img, x0, y0, pw, ph, 1, [bucket], [], "rank_severity", 0.0, 1.0)

    # Measure each bar's own width near the bar's own base (row just
    # above the baseline) using each rank's own known shade color.
    y_probe = y0 + ph - 5
    color_d1 = _shade(TEAM_COLOR[0], RANK_SHADE[0])
    color_d2 = _shade(TEAM_COLOR[0], RANK_SHADE[1])
    color_d3 = _shade(TEAM_COLOR[0], RANK_SHADE[2])
    span_d1 = _bar_column_span(img, y_probe, (x0, x0 + pw), color_d1)
    span_d2 = _bar_column_span(img, y_probe, (x0, x0 + pw), color_d2)
    span_d3 = _bar_column_span(img, y_probe, (x0, x0 + pw), color_d3)
    assert span_d1 and span_d2 and span_d3
    w_d1 = span_d1[1] - span_d1[0] + 1
    w_d2 = span_d2[1] - span_d2[0] + 1
    w_d3 = span_d3[1] - span_d3[0] + 1
    assert w_d1 > w_d2, "Danger #1 must be visibly wider than Danger #2"
    assert w_d1 > w_d3, "Danger #1 must be visibly wider than Danger #3"
    ratio = w_d1 / w_d2
    assert 1.05 <= ratio <= 1.25, f"D1/D2 width ratio {ratio:.2f} should be a SUBTLE ~10-15% emphasis, not dramatic"


def test_danger2_and_danger3_remain_equal_width_and_fully_visible():
    """Only Danger #1 gets the emphasis -- #2/#3 stay equal to each
    other and clearly non-zero width (never squeezed away)."""
    assert RANK_WIDTH_MULT[1] == RANK_WIDTH_MULT[2]
    assert RANK_WIDTH_MULT[1] == 1.0


def test_live_label_appears_only_on_the_current_rightmost_bucket():
    img = _blank_canvas(w=600, h=220)
    x0, y0, pw, ph, group_w = 10, 10, 580, 150, 580 / 3
    buckets = [
        {"t_start": 0.0, "t_end": 4.0},
        {"t_start": 4.0, "t_end": 8.0},
        {"t_start": 8.0, "t_end": 12.0},
    ]
    cur_time = 12.0  # only the LAST bucket's t_end matches "now"
    _bucket_axis_labels(img, buckets, x0, pw, y0, ph, group_w, cur_time)

    label_row = y0 + ph + 30
    bg = np.array(PANEL_BG, dtype=int)

    def has_live_near(bucket_idx):
        """Any anti-aliased text pixel differing from the plain
        background in the LIVE label's own row band -- robust to
        blending, unlike an exact color match."""
        cx = x0 + int((bucket_idx + 0.5) * group_w)
        band = img[label_row - 4:label_row + 4, max(0, cx - 20):cx + 20].astype(int)
        return bool(np.any(np.abs(band - bg).sum(axis=2) > 15))

    assert not has_live_near(0), "a historical bucket must never show LIVE"
    assert not has_live_near(1), "a historical bucket must never show LIVE"
    assert has_live_near(2), "the current, rightmost bucket must show LIVE"


def test_live_label_moves_with_a_shorter_growing_window():
    """Near the start of the match the window has fewer real buckets --
    LIVE must still land on whichever bucket is ACTUALLY last, not a
    hardcoded index."""
    img = _blank_canvas(w=400, h=220)
    x0, y0, pw, ph, group_w = 10, 10, 380, 150, 380 / 2
    buckets = [{"t_start": 0.0, "t_end": 4.0}, {"t_start": 4.0, "t_end": 8.0}]
    cur_time = 8.0
    _bucket_axis_labels(img, buckets, x0, pw, y0, ph, group_w, cur_time)

    label_row = y0 + ph + 30
    bg = np.array(PANEL_BG, dtype=int)
    cx_last = x0 + int(1.5 * group_w)
    band = img[label_row - 4:label_row + 4, max(0, cx_last - 20):cx_last + 20].astype(int)
    assert np.any(np.abs(band - bg).sum(axis=2) > 15)


def test_y_axis_is_locked_to_zero_one_and_never_computed_from_data():
    """Both Graph 1 (severity) and Graph 2 (access) are mathematically
    bounded to [0,1] (see HANDOFF.md's own audit: severity is a
    weighted sum of [0,1] components with weights summing to 1.0, times
    an area-gate <= 1; access is a sigmoid/explicit-bounded probability)
    -- the axis range passed to `_bar_chrome` must be the LITERAL
    `(0.0, 1.0)` in both graph functions' own source, never a value
    derived from the data being plotted (which would auto-rescale
    frame-to-frame, breaking "the same bar height means the same
    thing throughout the whole video")."""
    import inspect
    from dangerous_space_repositioning.dashboard import live_graphs
    src_g1 = inspect.getsource(live_graphs.draw_severity_bar_graph)
    src_g2 = inspect.getsource(live_graphs.draw_opponent_access_bar_graph)
    assert "(0.0, 1.0)" in src_g1, "Graph 1's y-range must be the fixed literal (0.0, 1.0)"
    assert "(0.0, 1.0)" in src_g2, "Graph 2's y-range must be the fixed literal (0.0, 1.0)"

    # And a smoke check that both actually render at that range with no data.
    img1 = draw_severity_bar_graph(700, 460, [], [], 12.0, 0.0, 12.0)
    img2 = draw_opponent_access_bar_graph(700, 460, [], [], 12.0, 0.0, 12.0)
    assert img1.shape == (460, 700, 3)
    assert img2.shape == (460, 700, 3)
