from dangerous_space_repositioning.analytics.spatial_balance import (
    compute_spatial_balance_risk, compactness_risk, isolation_risk, RISK_WEIGHTS,
)


def _team(prefix, xs_ys):
    return [{"track_id": f"{prefix}-{i}", "x_pitch": x, "y_pitch": y} for i, (x, y) in enumerate(xs_ys)]


def test_weights_sum_to_one():
    assert abs(sum(RISK_WEIGHTS.values()) - 1.0) < 1e-9


def test_compact_team_has_lower_risk_than_spread_team():
    compact = _team("A", [(5000, 3400), (5100, 3500), (5000, 3600), (5100, 3450)])
    spread = _team("B", [(500, 500), (11500, 6500), (500, 6500), (11500, 500)])
    r_compact = compactness_risk(compact)
    r_spread = compactness_risk(spread)
    assert r_compact < r_spread


def test_isolated_player_raises_isolation_risk():
    together = _team("A", [(5000, 3400), (5100, 3500), (5000, 3600)])
    one_isolated = _team("B", [(5000, 3400), (5100, 3500), (11000, 6500)])
    risk_together, gap_together = isolation_risk(together)
    risk_isolated, gap_isolated = isolation_risk(one_isolated)
    assert risk_isolated > risk_together
    assert gap_isolated > gap_together


def test_both_teams_get_a_real_score():
    team_a = _team("A", [(5000, 3400), (5100, 3500), (5000, 3600), (4800, 3200)])
    team_b = _team("B", [(7000, 3400), (7100, 3500), (7000, 3600), (6800, 3200)])
    rows = {p["track_id"]: {"display_object_type": "player"} for p in team_a + team_b}
    result_a = compute_spatial_balance_risk(0, team_a, team_b, rows)
    result_b = compute_spatial_balance_risk(1, team_a, team_b, rows)
    assert 0.0 <= result_a.risk <= 1.0
    assert 0.0 <= result_b.risk <= 1.0


def test_single_player_team_has_zero_compactness_and_isolation_risk():
    """Not enough players for a meaningful spread/gap reading -- honest
    0.0 (no evidence of a gap), never a fabricated high risk."""
    assert compactness_risk(_team("A", [(5000, 3500)])) == 0.0
    risk, gap = isolation_risk(_team("A", [(5000, 3500)]))
    assert risk == 0.0 and gap == 0.0
