from dangerous_space_repositioning.analytics.dangerous_space import (
    dangerous_space_for_team, severity_at_point, goal_proximity_score, centrality_score,
    score_cell, SEVERITY_WEIGHTS, REASON_UNCERTAIN_CONTEXT,
)
from dangerous_space_repositioning.analytics.data_loader import TEAM_A, TEAM_B
from tactical_shared.coordinates import DEFAULT_PITCH


def _ball(x, y):
    return {"x_pitch": x, "y_pitch": y}


def _team(team_id, xs_ys):
    return [{"track_id": f"{team_id}-{i}", "x_pitch": x, "y_pitch": y} for i, (x, y) in enumerate(xs_ys)]


def test_weights_sum_to_one():
    assert abs(sum(SEVERITY_WEIGHTS.values()) - 1.0) < 1e-9


def test_not_simply_largest_cell():
    """A large, empty, far-from-goal, wide/touchline cell must NOT
    outscore a smaller, central, near-goal, uncovered cell -- this is
    the project's own explicit anti-pattern. NOTE: per
    `tactical_shared.coordinates.DEFAULT_PITCH`, team 0's own goal is at
    x=length_cm (12000), not x=0 -- `own_goal(0)` resolves to the "far"
    end for this pitch's single period."""
    # Team A (defending its own goal at x=12000): bunched well short of
    # it, leaving a central, uncovered pocket right in front of their
    # own goal (high danger) AND a big, empty, wide/touchline cell near
    # team B's own end (low danger: far from A's goal, non-central).
    team_a = _team("A", [(9000, 3500), (9200, 3300), (8800, 3700), (9100, 3600)])
    team_b = _team("B", [(11500, 3500), (500, 500)])  # one attacker right near A's goal, centrally; one far away wide
    # Team B is attacking (real possession), ball right next to the dangerous
    # near-goal attacker -- the far/wide attacker's cell is ~110m behind the
    # ball and must be INELIGIBLE outright under the Current-Attack
    # Eligibility gate, not merely outscored.
    result = dangerous_space_for_team(0, team_a, team_b, ball=_ball(11000.0, 3500.0), pitch=DEFAULT_PITCH,
                                       attacking_team_actual=TEAM_B)
    assert result["valid"]
    top = result["top"]
    assert top is not None
    # The top-ranked cell should belong to the attacker near A's goal (x_pitch=11500), not the wide/far one (x_pitch=500).
    near_goal_attacker = team_b[0]
    dist_to_near = ((top.x - near_goal_attacker["x_pitch"]) ** 2 + (top.y - near_goal_attacker["y_pitch"]) ** 2) ** 0.5
    assert dist_to_near < 3000  # the flagged region is near the dangerous attacker, not the wide/far one
    # And the far/wide cell must be explicitly ineligible (SUPPORT_SPACE), never just "lower ranked."
    far_cell = next(s for s in result["ranked"] if abs(s.x - 500) < 3000)
    assert far_cell.components["eligible"] is False
    assert far_cell.components["category"] == "SUPPORT_SPACE"


def test_symmetry_between_teams():
    """The severity SCORING FORMULA (independent of Voronoi tessellation,
    which is not what this test is about) must be symmetric between team
    roles: the identical real situation, mirrored end-to-end (team
    identity swapped, every x-coordinate reflected about the halfway
    line, ball mirrored too), must give a comparable severity -- no
    hardcoded asymmetry between the two team roles."""
    defenders_0 = _team("A", [(1000, 3500), (2000, 3000), (2000, 4000)])
    attackers_0 = _team("B", [(3000, 3500), (500, 2000)])
    s0 = severity_at_point(0, 3000.0, 3500.0, 2_000_000.0, _ball(2800.0, 3500.0),
                            defenders_0, attackers_0, DEFAULT_PITCH, attacking_team_actual=TEAM_B)

    L = DEFAULT_PITCH.length_cm
    defenders_1 = _team("B", [(L - 1000, 3500), (L - 2000, 3000), (L - 2000, 4000)])
    attackers_1 = _team("A", [(L - 3000, 3500), (L - 500, 2000)])
    s1 = severity_at_point(1, L - 3000.0, 3500.0, 2_000_000.0, _ball(L - 2800.0, 3500.0),
                            attackers_1, defenders_1, DEFAULT_PITCH, attacking_team_actual=TEAM_A)

    assert abs(s0 - s1) < 0.05


def test_severity_at_point_matches_score_cell_convention():
    team_a = _team("A", [(1000, 3500), (2000, 3000), (2000, 4000), (500, 1000)])
    team_b = _team("B", [(3000, 3500), (500, 2000)])
    s = severity_at_point(0, 3000.0, 3500.0, 2_000_000.0, None, team_a, team_b, DEFAULT_PITCH)
    assert 0.0 <= s <= 1.0


def test_goal_proximity_decays_with_distance():
    """Team 0's own goal sits at x=length_cm (12000) for this pitch's
    single period -- see `tactical_shared.coordinates.PitchConfig.own_goal`."""
    near = goal_proximity_score(0, DEFAULT_PITCH.length_cm - 200.0, 3500.0)
    far = goal_proximity_score(0, 1000.0, 3500.0)
    assert near > far


def test_centrality_peaks_at_midline():
    center = centrality_score(3500.0)
    touchline = centrality_score(100.0)
    assert center > touchline


def test_no_ball_evidence_is_neutral_not_fabricated():
    """The `ball_proximity` COMPONENT still degrades honestly to neutral
    0.5 with no ball evidence (checked directly via `score_cell`, since
    `dangerous_space_for_team`'s own `top` requires real ball evidence to
    be eligible at all -- see the next assertion)."""
    team_a = _team("A", [(1000, 3500), (2000, 3000), (2000, 4000)])
    team_b = _team("B", [(3000, 3500), (500, 2000)])
    cell = {"track_id": "B-0", "polygon": [(3000.0, 3500.0)], "area_cm2": 2_000_000.0}
    s = score_cell(0, cell, ball=None, defending_players=team_a, attacking_players=team_b, pitch=DEFAULT_PITCH)
    assert s.had_ball_evidence is False
    assert s.components["ball_proximity"] == 0.5

    # With no ball evidence at all, the PRIMARY selector must honestly
    # report no eligible current-attack candidate -- never fall back to
    # an undirected guess.
    result = dangerous_space_for_team(0, team_a, team_b, ball=None, pitch=DEFAULT_PITCH)
    assert result["valid"]
    assert result["top"] is None
    assert result["reason"] == REASON_UNCERTAIN_CONTEXT
