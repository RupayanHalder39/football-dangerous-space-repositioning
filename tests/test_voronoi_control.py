import math

from dangerous_space_repositioning.analytics.voronoi_control import (
    voronoi_for_players, replace_player_position, opponent_owned_cells, cell_centroid,
)


def _grid_team(team_id, offset=0.0, n=5, spacing=1000.0):
    return [{"track_id": f"{team_id}-{i}", "x_pitch": 2000.0 + offset + i * spacing, "y_pitch": 2000.0 + (i % 2) * 1500.0}
            for i in range(n)]


def test_voronoi_clips_to_pitch():
    team_a = _grid_team("A")
    team_b = _grid_team("B", offset=6000.0)
    result = voronoi_for_players(team_a, team_b)
    assert result["valid"]
    for cell in result["cells"]:
        for x, y in cell["polygon"]:
            assert -1e-6 <= x <= 12000.0 + 1e-6
            assert -1e-6 <= y <= 7000.0 + 1e-6


def test_cell_ownership_matches_team():
    team_a = _grid_team("A")
    team_b = _grid_team("B", offset=6000.0)
    result = voronoi_for_players(team_a, team_b)
    track_ids_a = {p["track_id"] for p in team_a}
    for cell in result["cells"]:
        if cell["track_id"] in track_ids_a:
            assert cell["team_id"] == 0
        else:
            assert cell["team_id"] == 1


def test_degenerate_input_reports_invalid_not_fabricated():
    result = voronoi_for_players(_grid_team("A", n=1), [])
    assert result["valid"] is False
    assert result["cells"] == []


def test_replace_player_position_does_not_mutate_original():
    team_a = _grid_team("A")
    original = [dict(p) for p in team_a]
    moved = replace_player_position(team_a, "A-0", 9999.0, 9999.0)
    assert team_a == original  # never mutated
    moved_p = next(p for p in moved if p["track_id"] == "A-0")
    assert moved_p["x_pitch"] == 9999.0 and moved_p["y_pitch"] == 9999.0
    # every other player untouched
    for p, orig in zip(moved[1:], original[1:]):
        assert p["x_pitch"] == orig["x_pitch"] and p["y_pitch"] == orig["y_pitch"]


def test_opponent_owned_cells_are_the_other_team():
    team_a = _grid_team("A")
    team_b = _grid_team("B", offset=6000.0)
    result = voronoi_for_players(team_a, team_b)
    cells = opponent_owned_cells(result, defending_team=0)
    assert all(c["team_id"] == 1 for c in cells)


def test_cell_centroid_is_inside_or_near_polygon_bounds():
    team_a = _grid_team("A")
    team_b = _grid_team("B", offset=6000.0)
    result = voronoi_for_players(team_a, team_b)
    for cell in result["cells"]:
        cx, cy = cell_centroid(cell)
        xs = [p[0] for p in cell["polygon"]]
        ys = [p[1] for p in cell["polygon"]]
        assert min(xs) - 1.0 <= cx <= max(xs) + 1.0
        assert min(ys) - 1.0 <= cy <= max(ys) + 1.0
