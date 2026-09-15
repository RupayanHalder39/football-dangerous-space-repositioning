"""
Tests for the causal DISPLAY-ONLY stability layer
(`dashboard/display_stability.py`). These exercise the stabilizers as
pure state machines -- no video, no real match data -- since their job
is a display-layer decision problem, not an analytics computation.
"""
from dangerous_space_repositioning.analytics.data_loader import TEAM_A, TEAM_B
from dangerous_space_repositioning.analytics.counterfactual_repositioning import (
    CandidateResult, RepositioningRecommendation,
)
from dangerous_space_repositioning.dashboard.display_stability import (
    DangerRegionStabilizer, RecommendationStabilizer, LabelStabilizer,
)


def _rec(player_id, cx, cy, tx, ty, benefit, interpretation="candidate improved structure -- best candidate within the tested local search, not a proven optimum"):
    best = CandidateResult(tx, ty, 100.0, 0.005, 0.0, 0.0, 0.33, benefit) if tx is not None else None
    return RepositioningRecommendation(TEAM_A, player_id, cx, cy, best, [], interpretation)


def _no_candidate(player_id, cx, cy):
    return RepositioningRecommendation(TEAM_A, player_id, cx, cy, None, [],
                                        "no valid candidate found within the bounded local search")


# ---------------------------------------------------------------- recommendation

def test_recommendation_hysteresis_suppresses_switch_within_hold():
    stab = RecommendationStabilizer(min_hold_sec=0.5, switch_margin=0.002)
    raw1 = _rec(1, 0, 0, 100, 0, benefit=0.01)
    pid, res = stab.update(0.0, TEAM_A, (500, 500), {1, 2}, 1, raw1, search_fn=None)
    assert pid == 1

    # A different, even better raw candidate appears well within the hold window.
    raw2 = _rec(2, 200, 200, 300, 200, benefit=0.05)

    def search_fn(pid_):
        assert pid_ == 1  # only ever asked about the DISPLAYED player
        return _rec(1, 0, 0, 100, 0, benefit=0.01)

    pid, res = stab.update(0.2, TEAM_A, (500, 500), {1, 2}, 2, raw2, search_fn)
    assert pid == 1, "must not switch before min_hold_sec has elapsed"


def test_recommendation_switches_after_hold_when_margin_exceeded():
    stab = RecommendationStabilizer(min_hold_sec=0.5, switch_margin=0.002)
    raw1 = _rec(1, 0, 0, 100, 0, benefit=0.01)
    stab.update(0.0, TEAM_A, (500, 500), {1, 2}, 1, raw1, search_fn=None)

    raw2 = _rec(2, 200, 200, 300, 200, benefit=0.05)

    def search_fn(pid_):
        return _rec(1, 0, 0, 100, 0, benefit=0.01)

    pid, res = stab.update(0.6, TEAM_A, (500, 500), {1, 2}, 2, raw2, search_fn)
    assert pid == 2, "must switch once hold has elapsed and margin is clearly exceeded"


def test_recommendation_does_not_switch_for_a_near_equal_candidate():
    stab = RecommendationStabilizer(min_hold_sec=0.5, switch_margin=0.01)
    raw1 = _rec(1, 0, 0, 100, 0, benefit=0.010)
    stab.update(0.0, TEAM_A, (500, 500), {1, 2}, 1, raw1, search_fn=None)

    raw2 = _rec(2, 200, 200, 300, 200, benefit=0.011)  # only marginally better

    def search_fn(pid_):
        return _rec(1, 0, 0, 100, 0, benefit=0.010)

    pid, res = stab.update(1.0, TEAM_A, (500, 500), {1, 2}, 2, raw2, search_fn)
    assert pid == 1, "a near-equal candidate must not cause a flicker-inducing switch"


def test_recommendation_invalidates_immediately_when_player_leaves_roster():
    stab = RecommendationStabilizer(min_hold_sec=0.5, switch_margin=0.002)
    raw1 = _rec(1, 0, 0, 100, 0, benefit=0.01)
    stab.update(0.0, TEAM_A, (500, 500), {1, 2}, 1, raw1, search_fn=None)

    # Player 1 is no longer in this frame's candidate roster (e.g. subbed/occluded).
    raw2 = _rec(2, 200, 200, 300, 200, benefit=0.011)
    pid, res = stab.update(0.05, TEAM_A, (500, 500), {2}, 2, raw2, search_fn=None)
    assert pid == 2, "an invalid displayed player must be replaced immediately, no hold"


def test_recommendation_invalidates_immediately_on_team_flip():
    stab = RecommendationStabilizer(min_hold_sec=0.5, switch_margin=0.002)
    raw1 = _rec(1, 0, 0, 100, 0, benefit=0.01)
    stab.update(0.0, TEAM_A, (500, 500), {1}, 1, raw1, search_fn=None)

    raw2 = _rec(9, 200, 200, 300, 200, benefit=0.02)
    pid, res = stab.update(0.05, TEAM_B, (600, 600), {9}, 9, raw2, search_fn=None)
    assert pid == 9, "defending team changing must switch immediately, no hold"


def test_recommendation_resets_on_no_context():
    stab = RecommendationStabilizer()
    raw1 = _rec(1, 0, 0, 100, 0, benefit=0.01)
    stab.update(0.0, TEAM_A, (500, 500), {1}, 1, raw1, search_fn=None)

    pid, res = stab.update(0.1, TEAM_A, None, set(), None, None, search_fn=None)
    assert pid is None and res is None


def test_target_smoothing_resets_on_player_change_not_blended():
    stab = RecommendationStabilizer(min_hold_sec=0.0, switch_margin=0.0, target_ema_alpha=0.3)
    raw1 = _rec(1, 0, 0, 1000, 0, benefit=0.01)
    stab.update(0.0, TEAM_A, (500, 500), {1}, 1, raw1, search_fn=None)
    stab.update(0.033, TEAM_A, (500, 500), {1}, 1, raw1, search_fn=None)
    assert stab.display_to == (1000, 0)  # converged on the one real target seen so far

    # A different player becomes the top candidate, with a target far away.
    raw2 = _rec(2, 5000, 5000, -1000, 5000, benefit=1.0)

    def search_fn(pid_):
        assert pid_ == 1
        return raw1

    pid, res = stab.update(0.066, TEAM_A, (500, 500), {1, 2}, 2, raw2, search_fn)
    assert pid == 2
    assert stab.display_to == (-1000, 5000), (
        "the new player's target must be shown at its real value immediately, "
        "never blended with the previous player's stale target"
    )


def test_target_smoothing_is_a_real_causal_ema_between_two_real_values():
    stab = RecommendationStabilizer(min_hold_sec=0.0, switch_margin=0.0, target_ema_alpha=0.3)
    raw_a = _rec(1, 0, 0, 0.0, 0.0, benefit=0.01)
    raw_b = _rec(1, 0, 0, 100.0, 0.0, benefit=0.01)
    stab.update(0.0, TEAM_A, (500, 500), {1}, 1, raw_a, search_fn=None)
    stab.update(0.033, TEAM_A, (500, 500), {1}, 1, raw_b, search_fn=None)
    x, y = stab.display_to
    assert 0.0 < x < 100.0, "must be a genuine blend of two real observations, not either raw value"
    assert abs(x - 30.0) < 1e-9  # alpha*100 + (1-alpha)*0 = 30.0


def test_target_smoothing_resets_on_real_gap():
    stab = RecommendationStabilizer(min_hold_sec=0.0, switch_margin=0.0, target_ema_alpha=0.3)
    raw1 = _rec(1, 0, 0, 1000, 0, benefit=0.01)
    stab.update(0.0, TEAM_A, (500, 500), {1}, 1, raw1, search_fn=None)

    gap = _no_candidate(1, 0, 0)
    pid, res = stab.update(0.033, TEAM_A, (500, 500), {1}, 1, gap, search_fn=None)
    assert pid == 1 and stab.display_to is None, "a real gap (no valid candidate) must clear smoothing, never bridge it"

    raw2 = _rec(1, 0, 0, 2000, 0, benefit=0.01)
    stab.update(0.066, TEAM_A, (500, 500), {1}, 1, raw2, search_fn=None)
    assert stab.display_to == (2000, 0), "must reseed fresh from the next real value, not blend across the gap"


def test_no_future_leakage_recommendation():
    """Feeding two different futures after an identical prefix must not
    change any output produced during that shared prefix."""
    def make_prefix_outputs(stab):
        raw1 = _rec(1, 0, 0, 100, 0, benefit=0.01)
        out = [stab.update(0.0, TEAM_A, (500, 500), {1, 2}, 1, raw1, search_fn=None)]
        raw1b = _rec(1, 1, 1, 100, 0, benefit=0.012)
        out.append(stab.update(0.2, TEAM_A, (500, 500), {1, 2}, 1, raw1b, search_fn=None))
        return out

    stab_a = RecommendationStabilizer(min_hold_sec=0.5, switch_margin=0.002)
    prefix_a = make_prefix_outputs(stab_a)
    # Future A: a wildly better candidate shows up.
    stab_a.update(0.9, TEAM_A, (500, 500), {1, 2}, 2, _rec(2, 9, 9, 9, 9, benefit=99.0),
                  search_fn=lambda pid_: _rec(1, 1, 1, 100, 0, benefit=0.012))

    stab_b = RecommendationStabilizer(min_hold_sec=0.5, switch_margin=0.002)
    prefix_b = make_prefix_outputs(stab_b)
    # Future B: no candidate at all.
    stab_b.update(0.9, TEAM_A, None, set(), None, None, search_fn=None)

    assert prefix_a == prefix_b, "identical real prefixes must produce identical outputs regardless of what happens after"


# ---------------------------------------------------------------- danger region

def test_region_hysteresis_suppresses_flip_within_hold():
    stab = DangerRegionStabilizer(min_hold_sec=0.5, switch_margin=0.03)
    a = (0.60, 100, 100, 1_000_000)
    b = (0.40, 900, 900, 1_000_000)
    team, pt, area, dp, da = stab.update(0.0, a, b)
    assert team == TEAM_A

    b_now_worse = (0.90, 900, 900, 1_000_000)  # would clearly justify a switch on margin alone
    team, pt, area, dp, da = stab.update(0.1, a, b_now_worse)
    assert team == TEAM_A, "must not flip before min_hold_sec has elapsed, even if the margin would justify it"


def test_region_switches_after_hold_when_margin_exceeded():
    stab = DangerRegionStabilizer(min_hold_sec=0.5, switch_margin=0.03)
    a = (0.50, 100, 100, 1_000_000)
    b = (0.40, 900, 900, 1_000_000)
    stab.update(0.0, a, b)

    b_worse = (0.90, 900, 900, 1_000_000)
    team, pt, area, dp, da = stab.update(0.6, a, b_worse)
    assert team == TEAM_B, "must switch once hold elapsed and the other team is clearly worse now"


def test_region_disappears_immediately_when_evidence_lost():
    stab = DangerRegionStabilizer()
    a = (0.50, 100, 100, 1_000_000)
    stab.update(0.0, a, None)
    team, pt, area, dp, da = stab.update(0.05, None, None)
    assert team is None and pt is None, "genuine full data loss must be immediate, never held"


def test_region_forced_switch_when_displayed_team_evidence_vanishes():
    stab = DangerRegionStabilizer(min_hold_sec=0.5, switch_margin=0.03)
    a = (0.50, 100, 100, 1_000_000)
    stab.update(0.0, a, None)
    b = (0.10, 900, 900, 1_000_000)
    # Team A's evidence vanished this frame -- must switch to B immediately
    # even though B is not "clearly better" and the hold has not elapsed.
    team, pt, area, dp, da = stab.update(0.05, None, b)
    assert team == TEAM_B


def test_region_resets_immediately_when_displayed_region_becomes_analytically_ineligible():
    """Critical requirement from the Current-Attack Eligibility round
    (HANDOFF.md): once the upstream analytics reject the previously
    highlighted region (e.g. the real attack moved on and it no longer
    passes the eligibility gate), the display-stability layer must NEVER
    keep it on screen via hysteresis. `render_frame` feeds this
    stabilizer `None` for a team's info whenever
    `dangerous_space_for_team`'s `top` is `None` (ineligible) for that
    team -- exactly the same "evidence vanished" signal already used for
    a structurally-invalid Voronoi frame, so the existing immediate-reset
    path is what actually enforces this; this test locks that contract
    in explicitly for the eligibility case."""
    stab = DangerRegionStabilizer(min_hold_sec=0.5, switch_margin=0.03)
    a = (0.50, 100, 100, 1_000_000)
    stab.update(0.0, a, None)  # Team A's region is displayed (was eligible)

    # Next frame: Team A's region is now ANALYTICALLY INELIGIBLE (e.g. the
    # live attack progressed past it) -- render_frame would pass
    # info_a=None here, identical to a genuine data gap.
    team, pt, area, dp, da = stab.update(0.1, None, None)
    assert team is None and pt is None and dp is None, (
        "an ineligible region must be dropped immediately, never held "
        "on screen by hysteresis just because it was eligible a moment ago"
    )


def test_region_draw_point_is_ema_of_real_points_never_a_third_value():
    stab = DangerRegionStabilizer(min_hold_sec=0.5, switch_margin=0.03, ema_alpha=0.5)
    a1 = (0.50, 0, 0, 1_000_000)
    stab.update(0.0, a1, None)
    a2 = (0.50, 100, 0, 1_000_000)
    team, pt, area, dp, da = stab.update(0.033, a2, None)
    assert pt == (100, 0), "the REAL point fed downstream to analytics must be exact, never smoothed"
    assert dp == (50.0, 0.0), "the DRAWN point is a real EMA blend of the two real observations"


def test_no_future_leakage_region():
    def make_prefix_outputs(stab):
        a1 = (0.50, 0, 0, 1_000_000)
        out = [stab.update(0.0, a1, None)]
        a2 = (0.55, 10, 0, 1_000_000)
        out.append(stab.update(0.2, a2, None))
        return out

    stab_a = DangerRegionStabilizer(min_hold_sec=0.5, switch_margin=0.03)
    prefix_a = make_prefix_outputs(stab_a)
    stab_a.update(0.9, None, (0.99, 500, 500, 1_000_000))

    stab_b = DangerRegionStabilizer(min_hold_sec=0.5, switch_margin=0.03)
    prefix_b = make_prefix_outputs(stab_b)
    stab_b.update(0.9, None, None)

    assert prefix_a == prefix_b


# ---------------------------------------------------------------- label

def test_label_dwell_suppresses_rapid_switch():
    stab = LabelStabilizer(min_dwell_sec=0.5)
    stab.update(0.0, "MODERATE RISK", "sub", (1, 2, 3))
    title, sub, color = stab.update(0.1, "HIGH RISK", "sub2", (4, 5, 6))
    assert title == "MODERATE RISK", "must hold through the dwell window"


def test_label_switches_after_dwell_elapses():
    stab = LabelStabilizer(min_dwell_sec=0.5)
    stab.update(0.0, "MODERATE RISK", "sub", (1, 2, 3))
    title, sub, color = stab.update(0.6, "HIGH RISK", "sub2", (4, 5, 6))
    assert title == "HIGH RISK"


def test_label_uncertain_is_always_immediate():
    stab = LabelStabilizer(min_dwell_sec=0.5)
    stab.update(0.0, "RECOMMENDATION FOUND", "sub", (1, 2, 3))
    title, sub, color = stab.update(0.01, "UNCERTAIN", "no evidence", (0, 0, 0))
    assert title == "UNCERTAIN", "missing/invalid evidence must never be hidden by dwell"


def test_label_leaving_uncertain_is_also_always_immediate():
    """Regression test: a brief real gap must not leave a STALE
    "UNCERTAIN" on screen after real evidence returns -- that would
    itself be hiding real information, exactly as wrong as delaying
    entry into UNCERTAIN would be."""
    stab = LabelStabilizer(min_dwell_sec=0.5)
    stab.update(0.0, "MODERATE RISK", "sub", (1, 2, 3))
    stab.update(0.1, "UNCERTAIN", "no evidence", (0, 0, 0))
    title, sub, color = stab.update(0.11, "RECOMMENDATION FOUND", "sub2", (4, 5, 6))
    assert title == "RECOMMENDATION FOUND", (
        "leaving UNCERTAIN must be immediate once real evidence returns, "
        "never held for the remainder of a dwell window"
    )


def test_label_leaving_recommendation_is_always_immediate():
    stab = LabelStabilizer(min_dwell_sec=0.5)
    stab.update(0.0, "RECOMMENDATION FOUND", "sub", (1, 2, 3))
    title, sub, color = stab.update(0.01, "MODERATE RISK", "sub2", (4, 5, 6))
    assert title == "MODERATE RISK", "a genuinely-gone recommendation must not be held for cosmetic smoothness"


def test_label_refreshes_subtitle_while_holding_title():
    stab = LabelStabilizer(min_dwell_sec=0.5)
    stab.update(0.0, "MODERATE RISK", "Team A: 0.40  Team B: 0.50", (1, 2, 3))
    title, sub, color = stab.update(0.1, "MODERATE RISK", "Team A: 0.41  Team B: 0.52", (1, 2, 3))
    assert title == "MODERATE RISK"
    assert sub == "Team A: 0.41  Team B: 0.52", "the live numbers under a held title must stay real/current"
