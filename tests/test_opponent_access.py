from dangerous_space_repositioning.analytics.opponent_access import access_probability, opponent_control_of_region


def test_access_probability_favors_closer_team():
    attackers = [{"x_pitch": 1000.0, "y_pitch": 3500.0, "vx_cm_s": 0.0, "vy_cm_s": 0.0}]
    defenders = [{"x_pitch": 9000.0, "y_pitch": 3500.0, "vx_cm_s": 0.0, "vy_cm_s": 0.0}]
    p = access_probability(attackers, defenders, x=1200.0, y=3500.0)
    assert p > 0.5  # attackers are much closer to this point


def test_access_probability_is_bounded():
    attackers = [{"x_pitch": 1000.0, "y_pitch": 3500.0, "vx_cm_s": 0.0, "vy_cm_s": 0.0}]
    defenders = [{"x_pitch": 1000.0, "y_pitch": 3500.0, "vx_cm_s": 0.0, "vy_cm_s": 0.0}]
    p = access_probability(attackers, defenders, x=1000.0, y=3500.0)
    assert 0.0 <= p <= 1.0
    assert abs(p - 0.5) < 1e-6  # exactly equidistant, equal velocity -> a tie


def test_no_visible_players_is_honest_neutral():
    p = access_probability([], [], x=5000.0, y=3500.0)
    assert p == 0.5


def test_opponent_control_of_region_uses_correct_opponent():
    team_a = [{"track_id": 1, "x_pitch": 1000.0, "y_pitch": 3500.0, "vx_cm_s": 0.0, "vy_cm_s": 0.0}]
    team_b = [{"track_id": 2, "x_pitch": 9000.0, "y_pitch": 3500.0, "vx_cm_s": 0.0, "vy_cm_s": 0.0}]
    threat_vs_a = opponent_control_of_region(0, (1200.0, 3500.0), team_a, team_b)
    threat_vs_b = opponent_control_of_region(1, (8800.0, 3500.0), team_a, team_b)
    # team B is far from A's flagged region -> low threat vs A
    assert threat_vs_a < 0.5
    # team A is far from B's flagged region -> low threat vs B
    assert threat_vs_b < 0.5
