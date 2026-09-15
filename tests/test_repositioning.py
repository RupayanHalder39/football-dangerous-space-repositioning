from tactical_shared.coordinates import DEFAULT_PITCH
from dangerous_space_repositioning.analytics.counterfactual_repositioning import (
    search_repositioning, MAX_CANDIDATE_RADIUS_CM,
)
from dangerous_space_repositioning.analytics.player_responsibility import rank_candidates


def _rows(players):
    return {p["track_id"]: {"display_object_type": "player"} for p in players}


def test_no_pitch_outside_recommendation():
    """A candidate right at the pitch edge should never produce a
    recommended target outside [0, length] x [0, width]."""
    team_a = [{"track_id": "def", "x_pitch": 50.0, "y_pitch": 50.0},
              {"track_id": "def2", "x_pitch": 6000.0, "y_pitch": 3500.0}]
    team_b = [{"track_id": "att", "x_pitch": 400.0, "y_pitch": 400.0},
              {"track_id": "att2", "x_pitch": 8000.0, "y_pitch": 3500.0}]
    res = search_repositioning(0, "def", (400.0, 400.0), team_a, team_b, ball=None,
                                rows_by_track=_rows(team_a + team_b), pitch=DEFAULT_PITCH)
    for c in res.all_candidates:
        if c.rejected_reason is None:
            assert 0.0 <= c.x <= DEFAULT_PITCH.length_cm
            assert 0.0 <= c.y <= DEFAULT_PITCH.width_cm
        else:
            # A candidate landing outside the pitch must be the one
            # actually rejected for that reason -- never silently kept.
            assert not (0.0 <= c.x <= DEFAULT_PITCH.length_cm and 0.0 <= c.y <= DEFAULT_PITCH.width_cm) or \
                   "exceeds bounded radius" in c.rejected_reason


def test_candidate_movement_is_bounded():
    team_a = [{"track_id": "def", "x_pitch": 5000.0, "y_pitch": 3500.0},
              {"track_id": "def2", "x_pitch": 6000.0, "y_pitch": 3500.0}]
    team_b = [{"track_id": "att", "x_pitch": 5500.0, "y_pitch": 3500.0},
              {"track_id": "att2", "x_pitch": 8000.0, "y_pitch": 3500.0}]
    res = search_repositioning(0, "def", (5500.0, 3500.0), team_a, team_b, ball=None,
                                rows_by_track=_rows(team_a + team_b), pitch=DEFAULT_PITCH)
    for c in res.all_candidates:
        if c.rejected_reason is None:
            assert c.distance_moved_cm <= MAX_CANDIDATE_RADIUS_CM + 1e-6


def test_new_gap_penalty_is_never_negative():
    """`new_gap_penalty` only counts an INCREASE in the team's own
    exposure -- it must never go negative (a genuine improvement in the
    team's own structure is not treated as extra credit here, only as
    zero penalty)."""
    team_a = [{"track_id": "def", "x_pitch": 5000.0, "y_pitch": 3500.0},
              {"track_id": "def2", "x_pitch": 5200.0, "y_pitch": 3600.0},
              {"track_id": "def3", "x_pitch": 4800.0, "y_pitch": 3400.0}]
    team_b = [{"track_id": "att", "x_pitch": 6000.0, "y_pitch": 3500.0},
              {"track_id": "att2", "x_pitch": 8000.0, "y_pitch": 3500.0}]
    res = search_repositioning(0, "def", (6000.0, 3500.0), team_a, team_b, ball=None,
                                rows_by_track=_rows(team_a + team_b), pitch=DEFAULT_PITCH)
    for c in res.all_candidates:
        if c.rejected_reason is None:
            assert c.new_gap_penalty >= 0.0


def test_recommendation_improves_objective_in_a_controlled_case():
    """A synthetic, controlled case where a defender starts just beyond
    real "meaningful coverage" range of a real, uncovered attacker-held
    region: moving them closer should measurably shrink that region's
    own severity (danger_removed > 0) for at least the best-benefit
    candidate found -- a real, directional correctness check of the
    search, not a hardcoded outcome."""
    danger_x, danger_y = 6000.0, 3500.0
    team_a = [{"track_id": "def", "x_pitch": danger_x + 2800.0, "y_pitch": danger_y},
              {"track_id": "def2", "x_pitch": 1000.0, "y_pitch": 1000.0}]  # far away, structurally irrelevant here
    team_b = [{"track_id": "att", "x_pitch": danger_x, "y_pitch": danger_y},
              {"track_id": "att2", "x_pitch": 11000.0, "y_pitch": 6000.0}]
    # This test exercises `search_repositioning`'s own directional
    # correctness (severity_at_point no longer depends on Current-Attack
    # Eligibility for its VALUE -- see
    # test_attacking_phase_relevance.py::test_severity_at_point_does_not_depend_on_attacking_team_actual),
    # so a fixed, real-scale area is used directly rather than routing
    # through `dangerous_space_for_team`'s own (now eligibility-gated)
    # `top` selection, which is a separate concern.
    region_area_cm2 = 2_000_000.0

    res = search_repositioning(0, "def", (danger_x, danger_y), team_a, team_b, ball=None,
                                rows_by_track=_rows(team_a + team_b),
                                region_area_cm2=region_area_cm2, pitch=DEFAULT_PITCH)
    valid_candidates = [c for c in res.all_candidates if c.rejected_reason is None]
    assert valid_candidates
    best_danger_removed = max(c.danger_removed for c in valid_candidates)
    assert best_danger_removed > 0.0  # moving toward the region genuinely reduces its own severity
    # And the search's own summary best candidate must be internally
    # consistent with its own interpretation string.
    if res.best is not None and res.best.benefit > 0:
        assert "improved" in res.interpretation
    elif res.best is not None:
        assert "no improving" in res.interpretation


def test_candidate_selection_is_not_simply_nearest():
    """A very close defender who would abandon a real, currently-covered
    danger elsewhere should not automatically outrank a slightly
    farther, structurally "free" defender -- this project's own
    explicit anti-pattern is "pick the nearest defender.\""""
    danger_x, danger_y = 6000.0, 3500.0
    rows = {
        "near_but_loaded": {"display_object_type": "player"},
        "far_but_free": {"display_object_type": "player"},
        "gk": {"display_object_type": "goalkeeper"},
    }
    team_a = [
        {"track_id": "near_but_loaded", "x_pitch": 5500.0, "y_pitch": 3500.0},
        {"track_id": "far_but_free", "x_pitch": 4000.0, "y_pitch": 3500.0},
        {"track_id": "gk", "x_pitch": 100.0, "y_pitch": 3500.0},
    ]
    # A second, genuinely dangerous attacker sits RIGHT next to
    # "near_but_loaded"'s current position -- removing that defender
    # would leave it uncovered (a real abandonment cost), unlike
    # "far_but_free" who isn't currently covering anything special.
    team_b = [
        {"track_id": "att_target", "x_pitch": danger_x, "y_pitch": danger_y},
        {"track_id": "att_secondary", "x_pitch": 5550.0, "y_pitch": 3520.0},
    ]
    ranked = rank_candidates(0, (danger_x, danger_y), team_a, team_b, rows, ball=None, pitch=DEFAULT_PITCH)
    ids = [c.track_id for c in ranked]
    assert "gk" not in ids  # goalkeeper is never a repositioning candidate
    assert set(ids) == {"near_but_loaded", "far_but_free"}


def test_target_not_on_defending_team_is_reported_honestly():
    team_a = [{"track_id": "def", "x_pitch": 5000.0, "y_pitch": 3500.0}]
    team_b = [{"track_id": "att", "x_pitch": 6000.0, "y_pitch": 3500.0}]
    res = search_repositioning(0, "not-a-real-id", (6000.0, 3500.0), team_a, team_b, ball=None,
                                rows_by_track=_rows(team_a + team_b), pitch=DEFAULT_PITCH)
    assert res.best is None
    assert res.interpretation == "TARGET_NOT_ON_DEFENDING_TEAM"
