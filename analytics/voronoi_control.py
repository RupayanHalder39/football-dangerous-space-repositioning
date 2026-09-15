"""
Voronoi control -- THE TOOL, not the problem.

This module answers only "whose is this point right now, based on who
is geographically closest" -- the exact same "nearest-player
territory" approximation the repo's own `analytics/voronoi.py` already
implements and documents at length (never a physically-modeled pitch-
control field, never a possession probability, never an interception
probability). We reuse that module's pure-geometry engine
(`compute_voronoi`) directly rather than reimplementing clipping/area
math a second time.

Everything downstream in this project (dangerous_space.py,
opponent_access.py, counterfactual_repositioning.py, spatial_balance.py)
treats a Voronoi cell as exactly this: nearest-player territory. If a
reachability/velocity-aware model is needed, `opponent_access.py` names
it separately (it wraps `analytics/pitch_control.py`, a genuinely
different model) rather than overloading this word.
"""
from dataclasses import dataclass

from analytics.voronoi import compute_voronoi, PITCH_LENGTH_CM, PITCH_WIDTH_CM

TEAM_A = 0
TEAM_B = 1


def voronoi_for_players(team_a_players: list[dict], team_b_players: list[dict],
                         pitch_length: float = PITCH_LENGTH_CM, pitch_width: float = PITCH_WIDTH_CM) -> dict:
    """Combines both teams' real per-frame player dicts (from
    `data_loader.frame_players`) into one all-player Voronoi diagram.
    Returns the exact `compute_voronoi()` result shape -- see that
    function's own docstring for the full field list. `valid=False`
    (fewer than 4 total players, or degenerate/coincident positions) is
    reported honestly, never papered over with a fabricated diagram."""
    players = [{"track_id": p["track_id"], "team_id": TEAM_A, "x_pitch": p["x_pitch"], "y_pitch": p["y_pitch"]}
               for p in team_a_players] + \
              [{"track_id": p["track_id"], "team_id": TEAM_B, "x_pitch": p["x_pitch"], "y_pitch": p["y_pitch"]}
               for p in team_b_players]
    return compute_voronoi(players, pitch_length=pitch_length, pitch_width=pitch_width)


def replace_player_position(players: list[dict], track_id, new_x: float, new_y: float) -> list[dict]:
    """Returns a NEW list (never mutates `players`) with exactly one
    player's position replaced -- the counterfactual repositioning
    primitive every "what if this player stood here instead" question
    in this project builds on. Every other player's real observed
    position is held fixed."""
    out = []
    for p in players:
        if p["track_id"] == track_id:
            out.append({**p, "x_pitch": new_x, "y_pitch": new_y})
        else:
            out.append(p)
    return out


def cell_for_track(voronoi_result: dict, track_id) -> dict | None:
    if not voronoi_result.get("valid"):
        return None
    for cell in voronoi_result["cells"]:
        if cell["track_id"] == track_id:
            return cell
    return None


def opponent_owned_cells(voronoi_result: dict, defending_team: int) -> list[dict]:
    """Cells whose nearest player belongs to the OPPONENT of
    `defending_team` -- i.e. real space the opponent currently holds
    inside `defending_team`'s Voronoi picture. This is the candidate
    pool `dangerous_space.py` scores; this module itself makes no
    danger judgment."""
    if not voronoi_result.get("valid"):
        return []
    opponent = 1 - defending_team
    return [c for c in voronoi_result["cells"] if c["team_id"] == opponent]


def cell_centroid(cell: dict) -> tuple[float, float]:
    """Simple polygon-vertex-average centroid (not area-weighted -- the
    clipped Voronoi cells here are convex and reasonably compact, so the
    vertex average is a good-enough, cheap, honest proxy for "the middle
    of this pocket of space." Never claimed as the exact centroid of
    mass for a highly irregular polygon."""
    poly = cell["polygon"]
    if not poly:
        return (0.0, 0.0)
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


@dataclass
class VoronoiSnapshot:
    """Convenience bundle used by the dashboard renderer and the
    counterfactual search alike, so both operate on the identical
    real-vs-counterfactual pair."""
    team_a_players: list
    team_b_players: list
    result: dict
