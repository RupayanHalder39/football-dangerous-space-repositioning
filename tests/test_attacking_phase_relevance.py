"""
Tests for the Attacking-Phase Relevance Correction, ROUND 2 (Current-
Attack Eligibility HARD gate -- see HANDOFF.md). Round 1's soft
`direction_relevance` multiplier is gone; `classify_region` now applies
a hard eligibility filter BEFORE ranking, so an ineligible region can
never win the primary "Current Dangerous Space" selection regardless of
its other components.
"""
import os

import pytest

from tactical_shared.coordinates import DEFAULT_PITCH
from dangerous_space_repositioning.analytics.data_loader import (
    TEAM_A, TEAM_B, MatchData, _compute_attacking_context,
)
from dangerous_space_repositioning.analytics.dangerous_space import (
    classify_region, dangerous_space_for_team, severity_at_point,
    CATEGORY_CURRENT_DANGEROUS_SPACE, CATEGORY_SUPPORT_SPACE,
    CATEGORY_COUNTERATTACK_EXPOSURE, CATEGORY_UNCERTAIN,
    REASON_UNCERTAIN_CONTEXT, REASON_NO_ELIGIBLE_CANDIDATE,
    BACKWARD_TOLERANCE_CM, NEXT_ACTION_BALL_DIST_CM,
)
from dangerous_space_repositioning.analytics.counterfactual_repositioning import search_repositioning


def _team(team_id, xs_ys):
    return [{"track_id": f"{team_id}-{i}", "x_pitch": x, "y_pitch": y} for i, (x, y) in enumerate(xs_ys)]


def _ball(x, y):
    return {"x_pitch": x, "y_pitch": y}


# ---------------------------------------------------------------- classify_region: eligibility gate

def test_region_far_behind_ball_is_ineligible():
    """Team A attacks toward x=0. A cell far behind the ball (higher x)
    must be INELIGIBLE outright, not merely down-weighted."""
    attackers = _team("B", [])  # no attacker needed for the longitudinal check itself
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=9000.0, y=3500.0,
                            attacking_players=attackers, pitch=DEFAULT_PITCH)
    assert elig.eligible is False
    assert elig.category == CATEGORY_SUPPORT_SPACE
    assert elig.progress_cm == -3000.0


def test_region_2m_behind_ball_remains_eligible_when_otherwise_dangerous():
    """A small ~2-3m backward tolerance covers genuine cutback/support
    pockets -- a real attacker must be nearby for next-action relevance
    too, since that gate applies within the tolerance band as well."""
    attackers = _team("B", [(5800.0, 3500.0)])  # right next to the candidate region -- real receiver access
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=6200.0, y=3500.0,  # 200cm behind (Team A attacks toward x=0)
                            attacking_players=attackers, pitch=DEFAULT_PITCH)
    assert elig.eligible is True
    assert elig.category == CATEGORY_CURRENT_DANGEROUS_SPACE
    assert elig.progress_cm == pytest.approx(-200.0)


def test_region_exactly_at_backward_tolerance_boundary_is_eligible():
    attackers = _team("B", [(6000.0 + BACKWARD_TOLERANCE_CM, 3500.0)])
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=6000.0 + BACKWARD_TOLERANCE_CM, y=3500.0,
                            attacking_players=attackers, pitch=DEFAULT_PITCH)
    assert elig.eligible is True


def test_region_just_beyond_backward_tolerance_is_ineligible():
    attackers = _team("B", [(6000.0 + BACKWARD_TOLERANCE_CM + 50, 3500.0)])
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=6000.0 + BACKWARD_TOLERANCE_CM + 50, y=3500.0,
                            attacking_players=attackers, pitch=DEFAULT_PITCH)
    assert elig.eligible is False


def test_team_a_direction_ahead_is_eligible():
    attackers = _team("B", [(3000.0, 3500.0)])
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=3000.0, y=3500.0,
                            attacking_players=attackers, pitch=DEFAULT_PITCH)
    assert elig.progress_cm > 0
    assert elig.eligible is True


def test_team_b_direction_mirrored_works():
    """Team B attacks toward increasing x -- the mirrored geometry of
    the Team A case above must behave identically."""
    attackers = _team("A", [(7000.0, 3500.0)])
    elig = classify_region(defending_team=TEAM_A, attacking_team_actual=TEAM_B,
                            ball=_ball(4000.0, 3500.0), x=7000.0, y=3500.0,
                            attacking_players=attackers, pitch=DEFAULT_PITCH)
    assert elig.progress_cm > 0
    assert elig.eligible is True


def test_direction_mirrored_between_teams_identical_eligibility():
    """The identical real situation, mirrored end-to-end (team swapped,
    x reflected about the halfway line), must produce the IDENTICAL
    eligibility outcome -- catches a direction-inversion bug that only
    shows up for one team."""
    L = DEFAULT_PITCH.length_cm
    attackers_a = _team("B", [(9200.0, 3500.0)])
    elig_a = classify_region(TEAM_B, TEAM_A, _ball(6000.0, 3500.0), 9000.0, 3500.0, attackers_a, DEFAULT_PITCH)

    attackers_b = _team("A", [(L - 9200.0, 3500.0)])
    elig_b = classify_region(TEAM_A, TEAM_B, _ball(L - 6000.0, 3500.0), L - 9000.0, 3500.0, attackers_b, DEFAULT_PITCH)

    assert elig_a.eligible == elig_b.eligible
    assert elig_a.progress_cm == pytest.approx(elig_b.progress_cm)


def test_final_third_cutback_case_remains_eligible():
    """Ball very advanced near the byline -- a real cutback-zone cell
    slightly behind the ball's own extreme wide/deep position, but
    central and with a real nearby attacker, must remain eligible."""
    # Team A attacks toward x=0; ball is right at the byline (x=300).
    attackers = _team("B", [(650.0, 3500.0)])  # a real attacker at the candidate cutback cell
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(300.0, 3400.0), x=650.0, y=3500.0,  # ~350cm behind the ball longitudinally, central
                            attacking_players=attackers, pitch=DEFAULT_PITCH)
    assert elig.progress_cm < 0
    assert abs(elig.progress_cm) <= BACKWARD_TOLERANCE_CM
    assert elig.eligible is True
    assert elig.category == CATEGORY_CURRENT_DANGEROUS_SPACE


def test_disconnected_far_forward_region_fails_next_action_relevance():
    """A region that is technically AHEAD of the ball but 40m away with
    no real attacker nearby must NOT be eligible -- this is exactly the
    "forward but disconnected" failure mode the next-action gate exists
    to prevent."""
    far_attackers = _team("B", [(11000.0, 6900.0)])  # nowhere near the candidate cell
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=2000.0, y=200.0,  # far ahead (progress>0) but isolated
                            attacking_players=far_attackers, pitch=DEFAULT_PITCH)
    assert elig.progress_cm > 0  # genuinely "ahead" longitudinally
    assert elig.next_action_relevant is False
    assert elig.eligible is False
    assert elig.category == CATEGORY_SUPPORT_SPACE


def test_next_action_relevant_via_ball_proximity_alone():
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=6000.0 - NEXT_ACTION_BALL_DIST_CM + 100, y=3500.0,
                            attacking_players=[], pitch=DEFAULT_PITCH)
    assert elig.next_action_relevant is True
    assert elig.eligible is True


def test_counterattack_when_defending_teams_own_side_has_the_ball():
    elig = classify_region(defending_team=TEAM_A, attacking_team_actual=TEAM_A,
                            ball=_ball(6000.0, 3500.0), x=100.0, y=3500.0,
                            attacking_players=[], pitch=DEFAULT_PITCH)
    assert elig.category == CATEGORY_COUNTERATTACK_EXPOSURE
    assert elig.attack_phase_active is False
    assert elig.eligible is False


def test_uncertain_possession_is_ineligible_never_a_fallback_guess():
    """Round 2's explicit reversal of round 1: unknown context must NOT
    fall back to an undirected ranking -- it is simply ineligible."""
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=None,
                            ball=_ball(6000.0, 3500.0), x=9000.0, y=3500.0,
                            attacking_players=[], pitch=DEFAULT_PITCH)
    assert elig.category == CATEGORY_UNCERTAIN
    assert elig.eligible is False


def test_uncertain_when_no_ball_evidence():
    elig = classify_region(defending_team=TEAM_B, attacking_team_actual=TEAM_A,
                            ball=None, x=9000.0, y=3500.0,
                            attacking_players=[], pitch=DEFAULT_PITCH)
    assert elig.category == CATEGORY_UNCERTAIN
    assert elig.eligible is False


# ---------------------------------------------------------------- dangerous_space_for_team integration

def test_dangerous_space_for_team_returns_none_top_with_honest_reason_when_uncertain():
    team_a = _team("A", [(1000, 3500), (2000, 3000), (2000, 4000)])
    team_b = _team("B", [(3000, 3500), (500, 2000)])
    result = dangerous_space_for_team(TEAM_A, team_a, team_b, ball=None, pitch=DEFAULT_PITCH)
    assert result["valid"]
    assert result["top"] is None
    assert result["reason"] == REASON_UNCERTAIN_CONTEXT


def test_dangerous_space_for_team_reports_no_eligible_candidate_reason():
    """Context IS known, but every real opponent-owned cell is strongly
    behind the ball -- `top` must be None with the distinct
    "no eligible candidate" reason (not the "uncertain context" one)."""
    team_a = _team("A", [(9500.0, 3500.0), (9500.0, 3600.0)])
    team_b = _team("B", [(500.0, 3500.0), (700.0, 3600.0)])  # both attackers ~55m behind the ball
    ball = _ball(6000.0, 3500.0)
    result = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, DEFAULT_PITCH, attacking_team_actual=TEAM_B)
    assert result["valid"]
    assert result["top"] is None
    assert result["reason"] == REASON_NO_ELIGIBLE_CANDIDATE
    # But the real cells are still there, categorized, for diagnostics -- never silently discarded.
    assert len(result["ranked"]) >= 1
    assert all(s.components["category"] == CATEGORY_SUPPORT_SPACE for s in result["ranked"])


def test_ahead_of_ball_region_selected_over_ineligible_behind_one():
    ball = _ball(6000.0, 3500.0)
    team_a = _team("A", [(9500.0, 3500.0), (9500.0, 3600.0)])
    ahead_x, behind_x = 8500.0, 2500.0
    team_b = _team("B", [(ahead_x, 3500.0), (behind_x, 3500.0)])
    result = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, DEFAULT_PITCH, attacking_team_actual=TEAM_B)
    assert result["valid"] and result["top"] is not None
    assert result["top"].components["progress_cm"] > 0
    assert result["top"].components["eligible"] is True


def test_counterattack_exposure_never_wins_when_a_real_current_attack_exists():
    # Ball placed to land near the real Voronoi cell centroid for the
    # near-ball attacker (a denser 4-defender configuration, matching
    # `test_not_simply_largest_cell`'s own pattern, to keep cells
    # reasonably localized on this otherwise-empty synthetic pitch).
    ball = _ball(6600.0, 3400.0)
    team_a = _team("A", [(9000.0, 3500.0), (9200.0, 3300.0), (8800.0, 3700.0), (9100.0, 3600.0)])
    team_b = _team("B", [(8200.0, 3500.0), (200.0, 6800.0)])
    danger_to_a = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, DEFAULT_PITCH, attacking_team_actual=TEAM_B)
    assert danger_to_a["valid"] and danger_to_a["top"] is not None

    team_a_big_gap = _team("A", [(500.0, 3500.0), (600.0, 6800.0)])
    team_b_2 = _team("B", [(11500.0, 3500.0), (11300.0, 3300.0)])
    danger_to_b = dangerous_space_for_team(TEAM_B, team_a_big_gap, team_b_2, ball, DEFAULT_PITCH,
                                            attacking_team_actual=TEAM_B)
    assert danger_to_b["valid"] and danger_to_b["top"] is None  # ineligible outright now, not just outscored
    assert danger_to_b["reason"] == REASON_NO_ELIGIBLE_CANDIDATE
    assert danger_to_a["top"].severity > 0.0


# ---------------------------------------------------------------- possession context (data_loader) -- unchanged from round 1

def _synthetic_roles(carrier_sequence):
    return [{"frame": f, "carrier_team": c} for f, c in enumerate(carrier_sequence)]


def test_attacking_context_never_fabricates_when_no_evidence_ever():
    roles = _synthetic_roles([None] * 50)
    ctx = _compute_attacking_context(roles, fps=30.0)
    assert all(c["attacking_team"] is None and c["confidence"] == "uncertain" for c in ctx)


def test_attacking_context_current_frame_confident():
    roles = _synthetic_roles([None, None, TEAM_A, None, None])
    ctx = _compute_attacking_context(roles, fps=30.0)
    assert ctx[2]["attacking_team"] == TEAM_A and ctx[2]["confidence"] == "current"


def test_attacking_context_falls_back_to_majority_window_not_future():
    roles = _synthetic_roles([TEAM_B] * 5 + [None] * 60)
    ctx = _compute_attacking_context(roles, fps=30.0)
    assert ctx[10]["attacking_team"] == TEAM_B
    assert ctx[10]["confidence"] != "current"


def test_no_future_leakage_attacking_context():
    prefix = [TEAM_A, None, None, TEAM_A, None]
    roles_future_1 = _synthetic_roles(prefix + [TEAM_B] * 200)
    roles_future_2 = _synthetic_roles(prefix + [None] * 200)
    ctx_1 = _compute_attacking_context(roles_future_1, fps=30.0)
    ctx_2 = _compute_attacking_context(roles_future_2, fps=30.0)
    assert ctx_1[:len(prefix)] == ctx_2[:len(prefix)]


def test_match_data_attacking_team_at_degrades_gracefully_without_context():
    match = MatchData(n_frames=5, fps=30.0, pitch=DEFAULT_PITCH,
                       players_by_frame={}, ball_by_frame={}, roles=[])
    assert match.attacking_team_at(0) == (None, "uncertain")
    assert match.attacking_team_at(100) == (None, "uncertain")


# ---------------------------------------------------------------- counterfactual cannot optimize an ineligible region

def test_counterfactual_repositioning_never_invoked_for_an_ineligible_region():
    """The recommendation pipeline is only ever handed a `danger_region`
    that came from an ALREADY-ELIGIBLE `top` -- when nothing is
    eligible, `top` is None and no search happens at all. This test
    proves the upstream guarantee: an ineligible (strongly-behind)
    region never becomes a `top` that any caller could hand to
    `search_repositioning` in the first place."""
    ball = _ball(6000.0, 3500.0)
    team_a = _team("A", [(9500.0, 3500.0), (9500.0, 3600.0)])
    team_b = _team("B", [(500.0, 3500.0), (700.0, 3600.0)])  # both strongly behind the ball
    result = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, DEFAULT_PITCH, attacking_team_actual=TEAM_B)
    assert result["top"] is None
    # Confirming the real behind cells were never quietly promoted:
    assert all(not s.components["eligible"] for s in result["ranked"])


def test_severity_at_point_does_not_depend_on_attacking_team_actual():
    """Eligibility is now a ranking-time FILTER, not a severity
    multiplier -- `severity_at_point`'s returned float must be identical
    regardless of `attacking_team_actual`, since that value only affects
    `components["eligible"]`/["category"], not the score itself. This is
    what makes the counterfactual search's before/after comparison at a
    fixed, already-eligible region meaningful without any hidden
    possession-dependent scaling."""
    team_a = _team("A", [(9000.0, 3500.0), (9200.0, 3300.0)])
    team_b = _team("B", [(8200.0, 3500.0), (200.0, 6800.0)])
    ball = _ball(8000.0, 3500.0)
    s_live = severity_at_point(TEAM_A, 7900.0, 3500.0, 2_000_000.0, ball, team_a, team_b, DEFAULT_PITCH,
                                attacking_team_actual=TEAM_B)
    s_counter = severity_at_point(TEAM_A, 7900.0, 3500.0, 2_000_000.0, ball, team_a, team_b, DEFAULT_PITCH,
                                   attacking_team_actual=TEAM_A)
    assert s_live == pytest.approx(s_counter)


def test_search_repositioning_still_works_for_an_eligible_anchored_region():
    danger_x, danger_y = 6000.0, 3500.0
    team_a = [{"track_id": "def", "x_pitch": danger_x + 2800.0, "y_pitch": danger_y},
              {"track_id": "def2", "x_pitch": 1000.0, "y_pitch": 1000.0}]
    team_b = [{"track_id": "att", "x_pitch": danger_x, "y_pitch": danger_y},
              {"track_id": "att2", "x_pitch": 11000.0, "y_pitch": 6000.0}]
    rows = {p["track_id"]: {"display_object_type": "player"} for p in team_a + team_b}
    ball = _ball(danger_x, danger_y)
    res = search_repositioning(TEAM_A, "def", (danger_x, danger_y), team_a, team_b, ball, rows,
                                attacking_team_actual=TEAM_B)
    valid_candidates = [c for c in res.all_candidates if c.rejected_reason is None]
    assert valid_candidates
    assert max(c.danger_removed for c in valid_candidates) > 0.0


# ---------------------------------------------------------------- end-to-end (real data)

@pytest.mark.skipif(
    not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..",
                                     "ExternalDownlaodVideo", "testVideo1_120s.mp4")),
    reason="real video/tracking fixtures not available in this environment",
)
def test_flagship_frame_now_selects_the_real_attacked_team():
    from dangerous_space_repositioning.analytics.data_loader import load_match_data, frame_players
    from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players

    match = load_match_data()
    frame = 1040
    attacking_team_actual, confidence = match.attacking_team_at(frame)
    assert attacking_team_actual == TEAM_B

    team_a, team_b = frame_players(match, frame)
    ball = match.ball_at(frame)
    voronoi_result = voronoi_for_players(team_a, team_b)
    danger_a = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, match.pitch, voronoi_result,
                                         attacking_team_actual=attacking_team_actual)
    danger_b = dangerous_space_for_team(TEAM_B, team_a, team_b, ball, match.pitch, voronoi_result,
                                         attacking_team_actual=attacking_team_actual)
    assert danger_a["top"] is not None
    severity_a = danger_a["top"].severity
    severity_b = danger_b["top"].severity if danger_b["top"] is not None else 0.0
    assert severity_a > severity_b
