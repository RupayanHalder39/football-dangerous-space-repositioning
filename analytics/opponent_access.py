"""
Opponent Control / Access of Dangerous Space.

Answers a DIFFERENT question than `voronoi_control.py`: not "who is
geographically closest to this point right now" (nearest-player
territory), but "which team could realistically get a player to this
exact point fastest" -- reusing the repo's own existing, documented,
disclosed-as-simplified reachability model from `analytics/pitch_control.py`
(time-to-intercept with a short reaction-time extrapolation, logistic
blend of the two teams' fastest responders). No new physical model is
invented here; the SAME constants (`PLAYER_MAX_SPEED_CM_S`,
`REACTION_TIME_SEC`, `CONTROL_SIGMA_SEC`) are imported, never
redefined, so this module can never silently drift from the project's
one already-calibrated speed constant.

This module evaluates that model at SPECIFIC POINTS (a handful of
dangerous-space region centroids) rather than a full pitch grid --
identical math, far cheaper, since a bounded counterfactual search
calls this many times per candidate.
"""
import math

from analytics.pitch_control import PLAYER_MAX_SPEED_CM_S, REACTION_TIME_SEC, CONTROL_SIGMA_SEC


def _team_min_time_to_point(players: list[dict], x: float, y: float,
                             max_speed_cm_s: float = PLAYER_MAX_SPEED_CM_S,
                             reaction_time_sec: float = REACTION_TIME_SEC) -> float:
    """Fastest real responder's time-to-reach (x,y), in seconds. Velocity
    is whatever the caller supplied (this project always supplies the
    CAUSAL vx_cm_s/vy_cm_s from `data_loader.player_dict`, 0.0 when
    motion isn't trustworthy -- never a fabricated direction)."""
    if not players:
        return float("inf")
    best = float("inf")
    for p in players:
        eff_x = p["x_pitch"] + p.get("vx_cm_s", 0.0) * reaction_time_sec
        eff_y = p["y_pitch"] + p.get("vy_cm_s", 0.0) * reaction_time_sec
        dist = math.hypot(x - eff_x, y - eff_y)
        t = dist / max_speed_cm_s
        best = min(best, t)
    return best


def access_probability(attacking_players: list[dict], defending_players: list[dict], x: float, y: float,
                        sigma_sec: float = CONTROL_SIGMA_SEC) -> float:
    """P(the ATTACKING team could get a player to (x,y) before the
    defending team), in [0, 1], via the SAME logistic-of-time-advantage
    blend `analytics/pitch_control.py` already uses for its full-grid
    version. 0.5 exactly when both teams are equally fast to arrive --
    never a hard/discontinuous ownership boundary."""
    t_att = _team_min_time_to_point(attacking_players, x, y)
    t_def = _team_min_time_to_point(defending_players, x, y)
    if math.isinf(t_att) and math.isinf(t_def):
        return 0.5  # neither team has a visible player this frame -- an honest "can't tell", not a guess
    if math.isinf(t_att):
        return 0.0
    if math.isinf(t_def):
        return 1.0
    return 1.0 / (1.0 + math.exp(-(t_def - t_att) / sigma_sec))


def opponent_control_of_region(defending_team: int, region_point: tuple[float, float],
                                team_a_players: list[dict], team_b_players: list[dict]) -> float:
    """"Threat Against Team `defending_team`" -- how strongly the
    OPPONENT can access `defending_team`'s own flagged dangerous
    region. This is the exact quantity Graph 2 ("Opponent Control of
    Dangerous Space") plots for each team, and the exact quantity the
    dashboard's region badge reads."""
    attacking_players = team_b_players if defending_team == 0 else team_a_players
    defending_players = team_a_players if defending_team == 0 else team_b_players
    x, y = region_point
    return access_probability(attacking_players, defending_players, x, y)
