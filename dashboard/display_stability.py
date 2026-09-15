"""
Causal DISPLAY-ONLY stability layer for the dangerous-space dashboard.

Everything in this file only ever decides WHICH already-real, already-
computed value to show on screen this frame, or applies a light causal
EMA to a value that is about to be drawn. Nothing here calls into
`analytics/dangerous_space.py`, `analytics/opponent_access.py`, or
`analytics/spatial_balance.py`, and nothing here changes what
`analytics/counterfactual_repositioning.search_repositioning` or
`analytics/player_responsibility.rank_candidates` compute -- both are
still called with the real, current-frame roster and region on every
frame, for every candidate this module asks about. This module can
only choose which of those already-real results to keep showing, hold
it for a minimum duration, or blend two REAL consecutive values with an
exponential moving average -- exactly the same "display vs computation"
separation already established for the graphs in `live_graphs.py`
(`causal_ema_scalar`, `decimate_for_display`).

Causality: every `update()` here is a pure function of the current
frame's real inputs plus this object's own PAST state -- never a future
frame. Calling `update()` for frame f twice with two different possible
futures produces the identical result both times (see
`tests/test_display_stability.py::test_no_future_leakage`).

Honesty over smoothness, in every mechanism below: genuine loss of
evidence (missing tracking, a vanished danger region, a recommendation
that is no longer valid) is always reflected IMMEDIATELY, never held or
faded to preserve a calmer-looking frame.
"""
from dataclasses import dataclass

from dangerous_space_repositioning.analytics.data_loader import TEAM_A, TEAM_B

MIN_HOLD_SEC_REGION = 0.5
SWITCH_MARGIN_REGION = 0.03          # severity units (0-1 scale)
REGION_DRAW_EMA_ALPHA = 0.35         # cosmetic only -- smooths the drawn circle's centroid/radius

MIN_HOLD_SEC_RECOMMENDATION = 0.5
SWITCH_MARGIN_RECOMMENDATION = 0.002  # benefit units -- realistic benefits sit in the 0.001-0.01 range (see docs/REPOSITIONING_LOGIC.md)
TARGET_DISPLAY_EMA_ALPHA = 0.30       # within the requested 0.25-0.4 range

MIN_DWELL_SEC_LABEL = 0.5

MIN_HOLD_SEC_MULTI_REGION = 0.5
SWITCH_MARGIN_MULTI_REGION = 0.03    # same units/scale as SWITCH_MARGIN_REGION -- severity is 0-1 regardless of rank slot


class DangerRegionStabilizer:
    """DISPLAY-only causal hysteresis for WHICH team's flagged region is
    highlighted, plus a light EMA on the DRAWN circle's centroid/radius.

    The two team severities are frequently close, so a per-frame
    argmax (the original behavior) flips the highlighted team and
    region constantly even when neither team's real situation actually
    changed much. This class instead: (1) keeps showing the same
    team's region unless the other team becomes clearly worse by
    `switch_margin` AND at least `min_hold_sec` has passed since the
    last switch, or the displayed team's own evidence genuinely
    vanishes (immediate, no hold); (2) separately smooths the DRAWN
    circle's centroid/radius with a causal EMA so the disc doesn't
    jump between two nearby real cells frame to frame.

    Every number fed to `opponent_control_of_region` /
    `search_repositioning` by the caller should be the REAL (x, y) and
    the REAL area returned here -- unsmoothed. Only the two `draw_*`
    return values are for drawing the circle.
    """

    def __init__(self, min_hold_sec: float = MIN_HOLD_SEC_REGION,
                 switch_margin: float = SWITCH_MARGIN_REGION,
                 ema_alpha: float = REGION_DRAW_EMA_ALPHA):
        self.min_hold_sec = min_hold_sec
        self.switch_margin = switch_margin
        self.ema_alpha = ema_alpha
        self.reset()

    def reset(self):
        self.team = None
        self.since_t = None
        self.draw_point = None
        self.draw_area = None

    def update(self, t: float, team_a_info: tuple | None, team_b_info: tuple | None):
        """`team_x_info`: None (no valid region for that team this real
        frame), or a real `(severity, x, y, area_cm2)` tuple. Returns
        `(team, real_point, real_area, draw_point, draw_area)` -- all
        `None` if neither team has a valid region this frame (a
        genuine, immediate disappearance -- never held, never
        interpolated across)."""
        has_a, has_b = team_a_info is not None, team_b_info is not None
        if not has_a and not has_b:
            self.reset()
            return None, None, None, None, None

        sev_a = team_a_info[0] if has_a else None
        sev_b = team_b_info[0] if has_b else None
        raw_team = TEAM_A if (has_a and (not has_b or sev_a >= sev_b)) else TEAM_B

        if self.team is None:
            self._adopt(t, raw_team)
        elif self.team != raw_team:
            cur_info = team_a_info if self.team == TEAM_A else team_b_info
            if cur_info is None:
                self._adopt(t, raw_team)  # displayed team's own evidence vanished -- honest, immediate
            elif t - self.since_t >= self.min_hold_sec:
                raw_sev = sev_a if raw_team == TEAM_A else sev_b
                if raw_sev > cur_info[0] + self.switch_margin:
                    self._adopt(t, raw_team)

        cur_info = team_a_info if self.team == TEAM_A else team_b_info
        if cur_info is None:
            # displayed team's evidence vanished and no switch fired above
            # (both branches already try to _adopt when that happens, but
            # guard here too so this can never return a stale point).
            self.reset()
            return None, None, None, None, None

        _, rx, ry, rarea = cur_info
        if self.draw_point is None:
            self.draw_point, self.draw_area = (rx, ry), rarea
        else:
            a = self.ema_alpha
            self.draw_point = (a * rx + (1 - a) * self.draw_point[0],
                                a * ry + (1 - a) * self.draw_point[1])
            self.draw_area = a * rarea + (1 - a) * self.draw_area

        return self.team, (rx, ry), rarea, self.draw_point, self.draw_area

    def _adopt(self, t: float, team: int):
        self.team = team
        self.since_t = t
        self.draw_point = None  # re-seed at the new team's real point -- never blend across a team switch
        self.draw_area = None


class RecommendationStabilizer:
    """DISPLAY-only causal hysteresis for WHICH player is recommended
    and where, plus a causal EMA on the DISPLAYED target point only.

    `rank_candidates`/`search_repositioning` are called by the caller
    exactly as before, with real, current-frame data -- this class only
    decides which already-real `RepositioningRecommendation` to show.
    It never fabricates a benefit value: when it needs to compare the
    currently-displayed player against a new raw candidate, it asks the
    caller (via `search_fn`) to run the SAME real search for the
    displayed player's current real position, so both sides of the
    comparison are real, current-frame numbers.
    """

    def __init__(self, min_hold_sec: float = MIN_HOLD_SEC_RECOMMENDATION,
                 switch_margin: float = SWITCH_MARGIN_RECOMMENDATION,
                 target_ema_alpha: float = TARGET_DISPLAY_EMA_ALPHA):
        self.min_hold_sec = min_hold_sec
        self.switch_margin = switch_margin
        self.target_ema_alpha = target_ema_alpha
        self.reset()

    def reset(self):
        self.player_id = None
        self.team = None
        self.since_t = None
        self.result = None
        self.smoothed_to = None

    def update(self, t: float, defending_team, danger_point, valid_ids: set,
               raw_player_id, raw_result, search_fn):
        """
        t: current match time in seconds.
        defending_team: this frame's (already region-stabilized) worse team.
        danger_point: this frame's real flagged-region point, or None.
        valid_ids: track_ids eligible as a candidate this frame (from `rank_candidates`).
        raw_player_id: this frame's raw top-ranked candidate's track_id, or None.
        raw_result: the `RepositioningRecommendation` already computed for
            `raw_player_id` this frame (or None).
        search_fn: `callable(player_id) -> RepositioningRecommendation`,
            bound to THIS frame's real roster/region -- used only to
            re-query the CURRENTLY DISPLAYED player's real, current-frame
            numbers when a fair comparison is needed. Never called for a
            past or future frame.

        Returns `(player_id, result)` for what to display this frame, or
        `(None, None)` if there is no valid recommendation context at all
        (an honest, immediate reset -- never held).
        """
        no_context = danger_point is None or raw_player_id is None
        if no_context:
            self.reset()
            return None, None

        displayed_invalid = (
            self.player_id is None or
            self.team != defending_team or
            self.player_id not in valid_ids
        )
        if displayed_invalid:
            self._adopt(t, defending_team, raw_player_id, raw_result)
            return self.player_id, self.result

        if self.player_id == raw_player_id:
            self._refresh(raw_result)
            return self.player_id, self.result

        if t - self.since_t < self.min_hold_sec:
            self._refresh(search_fn(self.player_id))
            return self.player_id, self.result

        disp_result = search_fn(self.player_id)
        disp_benefit = disp_result.best.benefit if disp_result and disp_result.best else float("-inf")
        raw_benefit = raw_result.best.benefit if raw_result and raw_result.best else float("-inf")
        if raw_benefit > disp_benefit + self.switch_margin:
            self._adopt(t, defending_team, raw_player_id, raw_result)
        else:
            self._refresh(disp_result)
        return self.player_id, self.result

    @property
    def display_to(self):
        """The causally-smoothed (x, y) target point to draw, or None."""
        return self.smoothed_to

    def _adopt(self, t: float, team, player_id, result):
        self.team = team
        self.player_id = player_id
        self.since_t = t
        self.smoothed_to = None  # never blend a new player's target with the old player's stale one
        self._refresh(result)

    def _refresh(self, result):
        self.result = result
        to = (result.best.x, result.best.y) if (result is not None and result.best is not None) else None
        if to is None:
            self.smoothed_to = None  # invalid/no candidate this frame -- a real gap, never bridged
        elif self.smoothed_to is None:
            self.smoothed_to = to
        else:
            a = self.target_ema_alpha
            self.smoothed_to = (a * to[0] + (1 - a) * self.smoothed_to[0],
                                 a * to[1] + (1 - a) * self.smoothed_to[1])


class LabelStabilizer:
    """DISPLAY-only causal debounce for the top-row status badge text.

    Rules (in priority order):
    1. Any transition INTO or OUT OF "UNCERTAIN" is always immediate --
       genuinely missing/invalid evidence is never delayed for cosmetic
       smoothness, and once real evidence returns, continuing to show a
       stale "UNCERTAIN" would itself be hiding real information, so
       leaving it is held to exactly the same immediate standard.
    2. Leaving "RECOMMENDATION FOUND" is always immediate -- once the
       recommendation itself is genuinely gone this frame, the badge
       must not keep claiming one exists just to finish its dwell time.
    3. Every other transition (LOW/MODERATE/HIGH RISK churn, or
       entering RECOMMENDATION FOUND) is held for at least
       `min_dwell_sec` before switching.
    The subtitle/color for the CURRENTLY shown title are always
    refreshed to this frame's real numbers even while the title itself
    is being held (e.g. "Team A: 0.52  Team B: 0.41" keeps updating
    live under a held "MODERATE RISK" title).
    """

    def __init__(self, min_dwell_sec: float = MIN_DWELL_SEC_LABEL):
        self.min_dwell_sec = min_dwell_sec
        self.reset()

    def reset(self):
        self.title = None
        self.subtitle = None
        self.color = None
        self.since_t = None

    def update(self, t: float, raw_title: str, raw_subtitle: str, raw_color):
        if raw_title == self.title:
            self.subtitle, self.color = raw_subtitle, raw_color
            return self.title, self.subtitle, self.color

        # Every transition touching "UNCERTAIN" (entering OR leaving) is
        # immediate, in both directions -- once real evidence returns,
        # continuing to show a stale "UNCERTAIN" would itself be hiding
        # real information, exactly as wrong as delaying entry into it.
        # Leaving "RECOMMENDATION FOUND" is likewise always immediate --
        # a genuinely-gone recommendation is never held for cosmetic
        # smoothness. Only churn among LOW/MODERATE/HIGH RISK (and
        # freshly entering RECOMMENDATION FOUND) is ever debounced.
        immediate = (
            self.title is None or
            raw_title == "UNCERTAIN" or
            self.title == "UNCERTAIN" or
            (self.title == "RECOMMENDATION FOUND" and raw_title != "RECOMMENDATION FOUND")
        )
        if immediate or (t - self.since_t >= self.min_dwell_sec):
            self._adopt(t, raw_title, raw_subtitle, raw_color)
        return self.title, self.subtitle, self.color

    def _adopt(self, t: float, title: str, subtitle: str, color):
        self.title, self.subtitle, self.color = title, subtitle, color
        self.since_t = t


class MultiRegionStabilizer:
    """DISPLAY-only causal hysteresis for the ranked list of ADDITIONAL
    (secondary/tertiary) distinct dangerous regions for one team (see
    `analytics/multi_region.select_top_regions`), generalizing
    `DangerRegionStabilizer`'s own single-region hold/margin logic to
    `n_slots` ranked slots. The PRIMARY region/team decision itself is
    left entirely to the existing `DangerRegionStabilizer` -- this class
    only stabilizes the EXTRA slots layered on top of it.

    Each slot independently remembers WHICH opponent Voronoi cell
    (identified by its owning `track_id` -- a natural identity anchor,
    since a real cell tracks one real opponent player frame to frame,
    exactly the same convention `RecommendationStabilizer` already uses
    for a player identity) it is currently showing:

    1. If that track_id is still present among this frame's fresh,
       already-deduplicated candidate list -- keep showing IT in this
       SAME slot (refreshed with its current real severity/x/y/area),
       even if its raw rank among the fresh candidates shifted
       slightly, UNLESS a different, not-yet-claimed candidate is more
       severe by more than `switch_margin` AND at least `min_hold_sec`
       has passed since this slot's last change.
    2. If that track_id is no longer present at all (ineligible now,
       merged away by de-duplication, or fewer real distinct regions
       exist this frame) -- the slot is cleared IMMEDIATELY, no hold
       (the same "genuine loss of evidence is never held" principle
       every other stabilizer in this file follows).
    3. A currently-empty slot adopts the best available not-yet-claimed
       fresh candidate immediately -- no hold is needed to START
       showing something in an empty slot; the hold only protects
       against churn BETWEEN two already-real options.

    Never uses a future frame -- `update()` is a pure function of the
    current frame's real candidates plus this object's own past state."""

    def __init__(self, n_slots: int = 2, min_hold_sec: float = MIN_HOLD_SEC_MULTI_REGION,
                 switch_margin: float = SWITCH_MARGIN_MULTI_REGION):
        self.n_slots = n_slots
        self.min_hold_sec = min_hold_sec
        self.switch_margin = switch_margin
        self.reset()

    def reset(self):
        self.slot_track_id = [None] * self.n_slots
        self.slot_since_t = [None] * self.n_slots

    def update(self, t: float, fresh_candidates: list) -> list:
        """`fresh_candidates`: this frame's REAL, already-deduplicated,
        severity-descending list of candidates for the extra slots
        (e.g. `select_top_regions(...)[1:]`). Returns a list of length
        <= `n_slots`, one entry per OCCUPIED slot in slot order (index 0
        = the higher-priority extra slot) -- an unfilled slot is simply
        omitted, never fabricated."""
        by_id = {c.track_id: c for c in fresh_candidates}
        claimed = set()
        out = [None] * self.n_slots

        # Pass 1: a slot whose previous occupant is still real this
        # frame keeps it, refreshed.
        for i in range(self.n_slots):
            tid = self.slot_track_id[i]
            if tid is not None and tid in by_id and tid not in claimed:
                out[i] = by_id[tid]
                claimed.add(tid)

        # Pass 2: consider displacing a held slot by a stronger,
        # not-yet-claimed fresh candidate, respecting min_hold_sec.
        remaining = sorted((c for c in fresh_candidates if c.track_id not in claimed),
                           key=lambda c: c.severity, reverse=True)
        for i in range(self.n_slots):
            if out[i] is None or self.slot_since_t[i] is None:
                continue
            if t - self.slot_since_t[i] < self.min_hold_sec:
                continue
            if remaining and remaining[0].severity > out[i].severity + self.switch_margin:
                displaced = remaining.pop(0)
                claimed.discard(out[i].track_id)
                out[i] = displaced
                self.slot_track_id[i] = displaced.track_id
                self.slot_since_t[i] = t
                claimed.add(displaced.track_id)

        # Pass 3: fill any still-empty slot immediately from whatever
        # real candidates remain unclaimed.
        remaining = sorted((c for c in fresh_candidates if c.track_id not in claimed),
                           key=lambda c: c.severity, reverse=True)
        for i in range(self.n_slots):
            if out[i] is not None:
                continue
            if remaining:
                chosen = remaining.pop(0)
                out[i] = chosen
                self.slot_track_id[i] = chosen.track_id
                self.slot_since_t[i] = t
                claimed.add(chosen.track_id)
            else:
                self.slot_track_id[i] = None
                self.slot_since_t[i] = None

        return [x for x in out if x is not None]


@dataclass
class DashboardDisplayStabilizers:
    """Bundles the three causal DISPLAY-only stabilizers for ONE
    continuous rendering session. Pass a FRESH instance per independent,
    non-sequential render (each of the 6 standalone previews are pulled
    from unrelated random-access frames, so no history should carry
    between them -- a fresh instance's first observation always adopts
    immediately, identical to having no stabilizer at all). Reuse ONE
    instance across a sequential video export (`--out_path`) so the
    hold/margin/EMA mechanisms can actually do their job across time."""
    region: DangerRegionStabilizer = None
    recommendation: RecommendationStabilizer = None
    label: LabelStabilizer = None
    extra_regions: MultiRegionStabilizer = None

    def __post_init__(self):
        if self.region is None:
            self.region = DangerRegionStabilizer()
        if self.recommendation is None:
            self.recommendation = RecommendationStabilizer()
        if self.label is None:
            self.label = LabelStabilizer()
        if self.extra_regions is None:
            self.extra_regions = MultiRegionStabilizer(n_slots=2)
