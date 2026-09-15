"""
The three row-2 graph panels, both teams on every graph. Same rendering
convention throughout this repo: a fixed y-range (never auto-scaled
frame to frame, so a viewer's sense of scale stays stable), real gaps
broken (never interpolated across), and a white current-time marker
pinned at the right edge (the rolling window always ends at NOW).

DISPLAY-ONLY POLISH (this round): `causal_ema_scalar()` and
`decimate_for_display()` below affect ONLY how a value is drawn, never
how it is computed. The underlying analytics
(`dangerous_space.py`/`opponent_access.py`/`spatial_balance.py`) are
untouched by this module and untouched by this round's change -- see
`dangerous_space_repositioning/HANDOFF.md` for the explicit
confirmation.
"""
import cv2
import numpy as np

from dangerous_space_repositioning.dashboard.dashboard_style import (
    FONT, PANEL_BG, BORDER_SOFT, GRID, TEXT_WHITE, TEXT_DIM, TEAM_COLOR, TEAM_LETTER, RECOMMEND_COLOR, panel_frame,
)
from dangerous_space_repositioning.analytics.coach_signals import STATUS_RESOLVED, STATUS_NO_ELIGIBLE

MAX_GAP_SEC = 1.0  # a real tracking/validity gap wider than this breaks the line rather than bridging it

MAX_RANKS_DISPLAYED = 3  # Danger #1/#2/#3 -- matches analytics.multi_region.MAX_DANGER_REGIONS
# A bucket with fewer than this many real, analytically-defined samples
# (out of up to ~121 possible at full per-frame resolution over a 4s
# bucket) is drawn with a "partial evidence" marker -- an honest signal
# that its mean rests on thin real evidence, without hiding the real
# value it does have. An ABSOLUTE count, not a coverage FRACTION,
# because this project's own Current-Attack Eligibility gate already
# means most buckets legitimately resolve only ~15-30% of their frames
# (see HANDOFF.md's "~65% possession/ball unknown" measurement) -- a
# fraction-based threshold would flag nearly every bucket, which is not
# a useful signal. Empirically measured on this clip (314 sampled
# buckets, frames 500-1040 stride 20): median 25 real samples/bucket,
# 10th percentile 6, 25th percentile 19 -- `10` sits just below the
# 25th percentile, flagging genuinely thin buckets without flagging the
# typical case.
MIN_SAMPLES_FOR_CONFIDENT_BUCKET = 10


def causal_ema_scalar(series: list[tuple], alpha: float) -> list[tuple]:
    """DISPLAY-only causal EMA over a scalar (t, v) series -- v may be
    None (a real gap). Resets (starts fresh from the raw value) right
    after any None, exactly the same reset-on-gap convention already
    used by `analytics.temporal_utils.causal_ema` for position series
    -- never bridges a still-null gap, and never looks at a future
    sample (each output only ever depends on samples up to and
    including its own timestamp). `alpha` closer to 1.0 = lighter
    smoothing (more responsive); closer to 0.0 = heavier smoothing."""
    out = []
    prev = None
    for t, v in series:
        if v is None:
            out.append((t, None))
            prev = None
            continue
        sm = v if prev is None else (alpha * v + (1 - alpha) * prev)
        out.append((t, sm))
        prev = sm
    return out


def decimate_for_display(series: list[tuple], max_points: int) -> list[tuple]:
    """Point-thinning ONLY (never interpolation/averaging) -- keeps
    every `stride`-th real sample (including any real None gap that
    lands on a kept index) and always keeps the FINAL sample (the
    current NOW instant) so the right-edge cursor is never off by a
    stride. A no-op when the series already fits within `max_points`
    (the common case for a 16s window at full per-frame resolution
    isn't actually that many points; this is a safety net, not a
    routine step)."""
    n = len(series)
    if n <= max_points:
        return series
    stride = -(-n // max_points)  # ceil division
    out = series[::stride]
    if out[-1][0] != series[-1][0]:
        out.append(series[-1])
    return out


def bucket_region_history(samples: list[dict], t_lo: float, t_hi: float, bucket_sec: float) -> list[dict]:
    """Aggregates a CAUSAL list of per-frame samples (one team's own
    `{"time_sec", "status", "top3_severity", "top3_access"}` dicts, from
    `coach_signals.FrameSignal`) into fixed `bucket_sec`-wide buckets
    covering `[t_lo, t_hi]`. `t_lo`/`t_hi` may span LESS than a full
    `COACH_WINDOW_SEC` near the very start of the match (mirrors the
    existing line-graph's own `t_lo = max(0, cur_time - window)`
    growing-window convention) -- this produces FEWER buckets, never a
    fabricated empty one for time before kickoff.

    Per bucket, per rank (0=Danger #1, 1=#2, 2=#3):
      - `STATUS_UNCERTAIN` samples (possession/tracking genuinely
        unknown) are EXCLUDED from the average entirely -- they neither
        pull it down nor up.
      - `STATUS_NO_ELIGIBLE` samples contribute a REAL 0.0 (an
        analytically-confirmed "no eligible danger this instant," not a
        gap).
      - `STATUS_RESOLVED` samples contribute their real value at that
        rank (0.0 if fewer than `rank+1` distinct regions existed that
        instant -- also a real, confirmed absence, not a gap).
      - If EVERY sample in the bucket is uncertain (zero real evidence
        at all), the bucket's value is `None` -- drawn as an honest
        MISSING placeholder, never a fabricated zero.

    Returns one dict per bucket: `{t_start, t_end, n_samples,
    n_defined_samples, coverage, rank_severity: [v0, v1, v2],
    rank_access: [v0, v1, v2]}` (`rank_*` entries are `None` where no
    real evidence exists for that rank across the whole bucket)."""
    n_buckets = max(0, int(round((t_hi - t_lo) / bucket_sec)))
    buckets = []
    for i in range(n_buckets):
        b_lo = t_lo + i * bucket_sec
        b_hi = b_lo + bucket_sec
        in_bucket = [s for s in samples if b_lo - 1e-9 <= s["time_sec"] < b_hi + 1e-9]
        defined = [s for s in in_bucket if s["status"] in (STATUS_RESOLVED, STATUS_NO_ELIGIBLE)]
        rank_severity, rank_access = [], []
        for r in range(MAX_RANKS_DISPLAYED):
            if not defined:
                rank_severity.append(None)
                rank_access.append(None)
                continue
            sev_vals = [(s["top3_severity"][r] if s["status"] == STATUS_RESOLVED and len(s["top3_severity"]) > r else 0.0)
                        for s in defined]
            acc_vals = [(s["top3_access"][r] if s["status"] == STATUS_RESOLVED and len(s["top3_access"]) > r else 0.0)
                        for s in defined]
            rank_severity.append(sum(sev_vals) / len(sev_vals))
            rank_access.append(sum(acc_vals) / len(acc_vals))
        coverage = (len(defined) / len(in_bucket)) if in_bucket else 0.0
        buckets.append({
            "t_start": b_lo, "t_end": b_hi, "n_samples": len(in_bucket), "n_defined_samples": len(defined),
            "coverage": coverage, "rank_severity": rank_severity, "rank_access": rank_access,
        })
    return buckets


def _shade(color, factor: float):
    """Blends `color` toward white by `(1 - factor)` -- used to give
    Danger #1/#2/#3 progressively lighter shades of the SAME team color
    within one grouped set of bars, rather than inventing unrelated new
    colors per rank."""
    return tuple(int(c + (255 - c) * (1 - factor)) for c in color)


RANK_SHADE = {0: 1.0, 1: 0.62, 2: 0.36}  # Danger #1 full color, #2 medium, #3 faint
# Danger #1 drawn slightly WIDER than #2/#3 -- a subtle emphasis (this
# is the PRIMARY tactical problem) without making #2/#3 hard to read.
# +15% sits at the top of the requested 10-15% range, chosen (not
# 10%) because at this panel's typical ~15px bar width a 10% delta
# rounds to a 1-2px difference that is barely perceptible; 15% reliably
# reads as "a bit wider" at every bucket count from 1 to 6.
RANK_WIDTH_MULT = {0: 1.15, 1: 1.0, 2: 1.0}


def _bar_chrome(w, h, title, subtitle, y_label, y_range, tick_fmt, n_buckets):
    """Same visual chrome/frame as `_chrome`, adapted for a categorical
    (one group per time bucket) x-axis instead of a continuous time
    axis -- bucket boundary labels are drawn by the caller once bucket
    times are known."""
    img = panel_frame(w, h)
    cv2.rectangle(img, (12, 8), (15, 24), (60, 60, 220), -1)
    cv2.putText(img, title, (22, 20), FONT, 0.46, TEXT_WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, subtitle, (14, 36), FONT, 0.28, TEXT_DIM, 1, cv2.LINE_AA)

    pad_l, pad_r, pad_t, pad_b = 46, 14, 52, 34
    x0, y0 = pad_l, pad_t
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    y_lo, y_hi = y_range

    cv2.rectangle(img, (x0, y0), (x0 + pw, y0 + ph), BORDER_SOFT, 1)
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        gy = y0 + int(ph * (1 - frac))
        cv2.line(img, (x0, gy), (x0 + pw, gy), GRID, 1, cv2.LINE_AA)
        val = y_lo + frac * (y_hi - y_lo)
        cv2.putText(img, tick_fmt.format(val), (4, gy + 4), FONT, 0.28, TEXT_DIM, 1, cv2.LINE_AA)

    cv2.putText(img, y_label, (x0, h - 6), FONT, 0.26, TEXT_DIM, 1, cv2.LINE_AA)
    return img, x0, y0, pw, ph, y_lo, y_hi


def _draw_missing_bar(img, x, y_base, bar_w, max_bar_h, color=TEXT_DIM):
    """An honest "no real evidence this bucket" placeholder -- a short,
    dim, diagonally-hatched box instead of a fabricated zero-height (or
    any-height) bar, so a coach never mistakes genuine uncertainty for
    a confirmed absence of danger."""
    h = max(10, int(max_bar_h * 0.12))
    x0, y0, x1, y1 = x, y_base - h, x + bar_w, y_base
    cv2.rectangle(img, (x0, y0), (x1, y1), color, 1, cv2.LINE_AA)
    step = 6
    n_lines = max(2, bar_w // step + 2)
    for i in range(-1, n_lines):
        lx = x0 + i * step
        p0 = (min(max(lx, x0), x1), y1)
        p1 = (min(max(lx + h, x0), x1), y0)
        cv2.line(img, p0, p1, color, 1, cv2.LINE_AA)


def _draw_partial_coverage_marker(img, x, bar_w, y_base, color=TEXT_DIM):
    """A small dashed tick along the bar's own baseline signaling "this
    bucket's mean rests on thin real evidence" (coverage below
    `MIN_SAMPLES_FOR_CONFIDENT_BUCKET`) -- drawn regardless of whether the
    real value happens to be zero or not, so a low-confidence real zero
    is never visually indistinguishable from a confidently-measured
    one."""
    dash, gap = 4, 3
    xx = x
    while xx < x + bar_w:
        x2 = min(xx + dash, x + bar_w)
        cv2.line(img, (xx, y_base + 3), (x2, y_base + 3), color, 2, cv2.LINE_AA)
        xx += dash + gap


def _draw_region_bar(img, x, y0, ph, bar_w, value, color, y_lo, y_hi, n_defined_samples: int = 999):
    """ONE independent bar for a SINGLE (team, rank) pair -- height is
    purely that region's own real value, never combined with any other
    rank's (no stacking, no summing -- see this module's own "grouped
    region bars" redesign). `value=None` -> an honest hatched missing
    placeholder (zero real evidence this bucket for the WHOLE rank set);
    `value=0.0` -> a real, confirmed zero (a solid bar that simply has
    no height -- visually distinct from the hatched placeholder). A
    bucket resting on fewer than `MIN_SAMPLES_FOR_CONFIDENT_BUCKET` real
    samples gets a dashed baseline marker regardless of the value shown,
    an honest "thin evidence" signal."""
    y_base = y0 + ph
    if value is None:
        _draw_missing_bar(img, x, y_base, bar_w, ph)
        return
    if value > 1e-9:
        y_top = y0 + ph - int((min(y_hi, value) - y_lo) / max(1e-6, (y_hi - y_lo)) * ph)
        cv2.rectangle(img, (x, y_top), (x + bar_w, y_base), color, -1)
        cv2.rectangle(img, (x, y_top), (x + bar_w, y_base), (15, 15, 15), 1, cv2.LINE_AA)
    if n_defined_samples < MIN_SAMPLES_FOR_CONFIDENT_BUCKET:
        _draw_partial_coverage_marker(img, x, bar_w, y_base)


def _draw_grouped_region_bars(img, x0, y0, pw, ph, n_buckets, buckets_a, buckets_b, value_key, y_lo, y_hi):
    """Shared grouped-bar layout for BOTH Graph 1 (`value_key=
    "rank_severity"`) and Graph 2 (`value_key="rank_access"`) -- the
    ONLY difference between the two graphs is which already-bucketed
    value list is drawn; the layout/hierarchy is identical: time bucket
    -> team -> region rank. Each of the up to 3x2=6 bars per bucket is
    drawn INDEPENDENTLY via `_draw_region_bar` (never stacked, never
    summed), so Danger #1/#2/#3 and Team A/B are always simultaneously,
    separately readable. Spacing widens outward through the hierarchy
    (region gap < team gap < bucket gap) so the eye groups bars
    correctly at a glance without needing a label under every bar."""
    if n_buckets == 0:
        return
    group_w = pw / n_buckets
    team_gap = group_w * 0.14
    region_gap = max(1.0, group_w * 0.015)
    team_w = (group_w - team_gap) / 2.0
    # Danger #1 is drawn RANK_WIDTH_MULT[0]x wider than #2/#3 (see its
    # own constant docstring) -- solve for a base unit width so the 3
    # (unequal) bars plus their 2 inter-region gaps still exactly fill
    # team_w, rather than a uniform stride.
    total_mult = sum(RANK_WIDTH_MULT[r] for r in range(MAX_RANKS_DISPLAYED))
    base_w = max(2.0, (team_w - (MAX_RANKS_DISPLAYED - 1) * region_gap) / total_mult)
    bar_widths = {r: max(3, int(round(base_w * RANK_WIDTH_MULT[r]))) for r in range(MAX_RANKS_DISPLAYED)}
    for i in range(n_buckets):
        gx = x0 + i * group_w
        team_x0 = {0: gx, 1: gx + team_w + team_gap}
        for team, buckets in ((0, buckets_a), (1, buckets_b)):
            if i >= len(buckets):
                continue
            values = buckets[i][value_key]
            n_defined = buckets[i]["n_defined_samples"]
            cursor = team_x0[team]
            for r in range(MAX_RANKS_DISPLAYED):
                bw = bar_widths[r]
                bar_color = _shade(TEAM_COLOR[team], RANK_SHADE[r])
                v = values[r] if r < len(values) else None
                _draw_region_bar(img, int(round(cursor)), y0, ph, bw, v, bar_color, y_lo, y_hi, n_defined_samples=n_defined)
                cursor += bw + region_gap


def _bucket_axis_labels(img, buckets, x0, pw, y0, ph, group_w, cur_time):
    """Draws each bucket's own `t_start-t_end` label, plus a "LIVE" tag
    (in the dashboard's own established cyan, `RECOMMEND_COLOR` -- the
    same color already used for the spotlight/recommendation ring, so
    it reads as "this is still actively updating" rather than an
    unrelated new color) under ONLY the current, rightmost bucket --
    the one still accumulating real samples as time advances. Never
    applied to a historical (fully-elapsed) bucket; moves with the
    rolling window since it is keyed to `cur_time`, not a fixed index."""
    for i, b in enumerate(buckets):
        cx = x0 + int((i + 0.5) * group_w)
        label = f"{int(b['t_start'])}–{int(b['t_end'])}s"
        tw = cv2.getTextSize(label, FONT, 0.26, 1)[0][0]
        cv2.putText(img, label, (cx - tw // 2, y0 + ph + 16), FONT, 0.26, TEXT_DIM, 1, cv2.LINE_AA)
        if b["t_end"] >= cur_time - 1e-6:
            live_label = "LIVE"
            live_w = cv2.getTextSize(live_label, FONT, 0.24, 1)[0][0]
            cv2.putText(img, live_label, (cx - live_w // 2, y0 + ph + 30), FONT, 0.24, RECOMMEND_COLOR, 1, cv2.LINE_AA)


def draw_severity_bar_graph(w, h, buckets_a, buckets_b, cur_time, t_lo, t_hi, tick_spacing=None):
    """Graph 1 (grouped-bar redesign): for each `bucket_sec`-wide time
    bucket, SIX independent bars -- Team A's Danger #1/#2/#3 and Team
    B's Danger #1/#2/#3 -- side by side, never stacked or summed. Each
    bar's own height is that SPECIFIC region's own real MEAN severity in
    that bucket, so a coach reads Region #1/#2/#3's own severity, and
    which team is conceding more individual dangerous pockets, directly
    -- with no combined "burden" number implied. See
    `bucket_region_history`'s own docstring for the exact honest-
    missing-data rule and `_draw_grouped_region_bars` for the shared
    layout this shares with Graph 2."""
    n_buckets = max(len(buckets_a), len(buckets_b))
    img, x0, y0, pw, ph, y_lo, y_hi = _bar_chrome(
        w, h, "DANGEROUS SPACE SEVERITY BY REGION",
        "Danger #1/#2/#3 severity (separate bars), averaged per 4s bucket -- never summed",
        "Severity Score (0 to 1)", (0.0, 1.0), "{:.1f}", n_buckets)
    _draw_grouped_region_bars(img, x0, y0, pw, ph, n_buckets, buckets_a, buckets_b, "rank_severity", y_lo, y_hi)
    _bucket_axis_labels(img, buckets_a or buckets_b, x0, pw, y0, ph, pw / max(1, n_buckets), cur_time)
    _rank_legend(img, x0, pw, y0)
    return img


def draw_opponent_access_bar_graph(w, h, buckets_a, buckets_b, cur_time, t_lo, t_hi, tick_spacing=None):
    """Graph 2 (grouped-bar redesign): identical layout to Graph 1 (see
    `_draw_grouped_region_bars`), plotting each region's own real
    opponent-access probability instead of severity -- Danger #1/#2/#3
    are independent bars, NEVER stacked/summed, since access
    probabilities across different physical regions have no meaningful
    combined value. Answers "which specific dangerous region was
    actually easiest for the opponent to exploit," region by region."""
    n_buckets = max(len(buckets_a), len(buckets_b))
    img, x0, y0, pw, ph, y_lo, y_hi = _bar_chrome(
        w, h, "EXPLOITABLE DANGER BY REGION",
        "Danger #1/#2/#3 opponent-access (separate bars), averaged per 4s bucket -- never summed",
        "Access Probability (0 to 1)", (0.0, 1.0), "{:.1f}", n_buckets)
    _draw_grouped_region_bars(img, x0, y0, pw, ph, n_buckets, buckets_a, buckets_b, "rank_access", y_lo, y_hi)
    _bucket_axis_labels(img, buckets_a or buckets_b, x0, pw, y0, ph, pw / max(1, n_buckets), cur_time)
    _rank_legend(img, x0, pw, y0)
    return img


def _rank_legend(img, x0, pw, y0):
    """Legend for the bucketed bar graphs: both teams' base colors plus
    a Danger #1/#2/#3 shade key -- kept compact/simple per this round's
    own "make legends simpler" requirement."""
    lx = x0 + pw
    for team in (1, 0):
        label = f"Team {TEAM_LETTER[team]}"
        tw = cv2.getTextSize(label, FONT, 0.28, 1)[0][0]
        lx -= tw
        cv2.putText(img, label, (lx, y0 - 8), FONT, 0.28, TEXT_WHITE, 1, cv2.LINE_AA)
        lx -= 15
        cv2.rectangle(img, (lx, y0 - 18), (lx + 9, y0 - 10), TEAM_COLOR[team], -1)
        lx -= 14
    lx -= 6
    for r in (2, 1, 0):
        cv2.rectangle(img, (lx, y0 - 18), (lx + 9, y0 - 10), _shade((190, 190, 190), RANK_SHADE[r]), -1)
        lx -= 12
    label = "Danger #1/#2/#3"
    tw = cv2.getTextSize(label, FONT, 0.26, 1)[0][0]
    cv2.putText(img, label, (lx - tw - 4, y0 - 8), FONT, 0.26, TEXT_DIM, 1, cv2.LINE_AA)


def _chrome(w, h, title, subtitle, y_label, y_range, tick_fmt, t_lo, t_hi, tick_spacing):
    img = panel_frame(w, h)
    cv2.rectangle(img, (12, 8), (15, 24), (60, 60, 220), -1)
    cv2.putText(img, title, (22, 20), FONT, 0.46, TEXT_WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, subtitle, (14, 36), FONT, 0.28, TEXT_DIM, 1, cv2.LINE_AA)

    pad_l, pad_r, pad_t, pad_b = 46, 14, 52, 34
    x0, y0 = pad_l, pad_t
    pw, ph = w - pad_l - pad_r, h - pad_t - pad_b
    y_lo, y_hi = y_range

    cv2.rectangle(img, (x0, y0), (x0 + pw, y0 + ph), BORDER_SOFT, 1)
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        gy = y0 + int(ph * (1 - frac))
        cv2.line(img, (x0, gy), (x0 + pw, gy), GRID, 1, cv2.LINE_AA)
        val = y_lo + frac * (y_hi - y_lo)
        cv2.putText(img, tick_fmt.format(val), (4, gy + 4), FONT, 0.28, TEXT_DIM, 1, cv2.LINE_AA)

    import math
    t = math.ceil(t_lo / tick_spacing) * tick_spacing
    while t <= t_hi + 1e-6:
        x = x0 + int((t - t_lo) / max(1e-6, (t_hi - t_lo)) * pw)
        cv2.line(img, (x, y0), (x, y0 + ph), GRID, 1, cv2.LINE_AA)
        label = f"{int(round(t))}s"
        tw = cv2.getTextSize(label, FONT, 0.26, 1)[0][0]
        cv2.putText(img, label, (max(0, x - tw // 2), y0 + ph + 16), FONT, 0.26, TEXT_DIM, 1, cv2.LINE_AA)
        t += tick_spacing

    cv2.putText(img, y_label, (x0, h - 6), FONT, 0.26, TEXT_DIM, 1, cv2.LINE_AA)
    return img, x0, y0, pw, ph, y_lo, y_hi


def _to_px(t, v, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph):
    x = x0 + int((t - t_lo) / max(1e-6, (t_hi - t_lo)) * pw)
    y = y0 + ph - int((v - y_lo) / max(1e-6, (y_hi - y_lo)) * ph)
    return x, y


def _plot_series(img, history, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph, color, max_gap_sec=MAX_GAP_SEC):
    windowed = [(t, v) for t, v in history if t_lo - max_gap_sec <= t <= t_hi + 1e-9]
    segment, last_t = [], None
    for t, v in windowed:
        gap = (last_t is not None) and (t - last_t > max_gap_sec)
        if v is None or gap:
            if len(segment) >= 2:
                cv2.polylines(img, [np.array(segment, dtype=np.int32)], False, color, 2, cv2.LINE_AA)
            segment = []
        if v is not None:
            segment.append(_to_px(t, np.clip(v, y_lo, y_hi), t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph))
        last_t = t
    if len(segment) >= 2:
        cv2.polylines(img, [np.array(segment, dtype=np.int32)], False, color, 2, cv2.LINE_AA)
    elif len(segment) == 1:
        cv2.circle(img, segment[0], 3, color, -1, cv2.LINE_AA)


def _legend(img, x0, pw, y0):
    lx = x0 + pw
    for team in (1, 0):
        label = f"Team {TEAM_LETTER[team]}"
        tw = cv2.getTextSize(label, FONT, 0.30, 1)[0][0]
        lx -= tw
        cv2.putText(img, label, (lx, y0 - 8), FONT, 0.30, TEXT_WHITE, 1, cv2.LINE_AA)
        lx -= 16
        cv2.rectangle(img, (lx, y0 - 18), (lx + 10, y0 - 10), TEAM_COLOR[team], -1)
        lx -= 12


def _current_marker(img, cur_time, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph):
    cx, _ = _to_px(cur_time, y_lo, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph)
    cv2.line(img, (cx, y0), (cx, y0 + ph), (0, 0, 0), 3, cv2.LINE_AA)
    cv2.line(img, (cx, y0), (cx, y0 + ph), TEXT_WHITE, 1, cv2.LINE_AA)


def draw_severity_graph(w, h, hist_a, hist_b, cur_time, t_lo, t_hi, tick_spacing):
    img, x0, y0, pw, ph, y_lo, y_hi = _chrome(
        w, h, "DANGEROUS SPACE SEVERITY OVER TIME", "Higher values = more concerning dangerous space is being conceded",
        "Severity Score (0 to 1)", (0.0, 1.0), "{:.1f}", t_lo, t_hi, tick_spacing)
    _plot_series(img, hist_a, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph, TEAM_COLOR[0])
    _plot_series(img, hist_b, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph, TEAM_COLOR[1])
    _legend(img, x0, pw, y0)
    _current_marker(img, cur_time, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph)
    return img


def draw_opponent_control_graph(w, h, hist_a, hist_b, cur_time, t_lo, t_hi, tick_spacing):
    img, x0, y0, pw, ph, y_lo, y_hi = _chrome(
        w, h, "OPPONENT CONTROL OF DANGEROUS SPACE",
        "Threat Against A = Team B's access to A's danger zone; Threat Against B = Team A's access to B's",
        "Access Probability (0 to 1)", (0.0, 1.0), "{:.1f}", t_lo, t_hi, tick_spacing)
    _plot_series(img, hist_a, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph, TEAM_COLOR[0])
    _plot_series(img, hist_b, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph, TEAM_COLOR[1])
    lx = x0 + pw
    for team, label in ((1, "Threat vs B"), (0, "Threat vs A")):
        tw = cv2.getTextSize(label, FONT, 0.28, 1)[0][0]
        lx -= tw
        cv2.putText(img, label, (lx, y0 - 8), FONT, 0.28, TEXT_WHITE, 1, cv2.LINE_AA)
        lx -= 14
        cv2.rectangle(img, (lx, y0 - 18), (lx + 10, y0 - 10), TEAM_COLOR[team], -1)
        lx -= 12
    _current_marker(img, cur_time, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph)
    return img


def draw_spatial_balance_graph(w, h, hist_a, hist_b, cur_time, t_lo, t_hi, tick_spacing):
    img, x0, y0, pw, ph, y_lo, y_hi = _chrome(
        w, h, "SPATIAL BALANCE / NEW-GAP RISK", "Higher values = greater risk of an exposed structural gap",
        "Risk Score (0 to 1)", (0.0, 1.0), "{:.1f}", t_lo, t_hi, tick_spacing)
    _plot_series(img, hist_a, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph, TEAM_COLOR[0])
    _plot_series(img, hist_b, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph, TEAM_COLOR[1])
    _legend(img, x0, pw, y0)
    _current_marker(img, cur_time, t_lo, t_hi, y_lo, y_hi, x0, y0, pw, ph)
    return img
