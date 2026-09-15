"""
"Who should fix it?" -- candidate defender selection.

Explicitly NOT "pick the nearest defender." Every candidate from the
defending team's OWN outfield players (goalkeeper excluded -- asking a
keeper to abandon the goal line is never a realistic recommendation) is
scored on four real, geometry-derived components:

1. `proximity`           -- closer to the dangerous region is better
                             (but not the only factor)
2. `feasibility`         -- a smooth, saturating version of proximity
                             (a very close and a moderately-close
                             candidate shouldn't be scored near-linearly
                             different once both are clearly "close
                             enough to matter")
3. `abandonment_penalty` -- would moving this player leave THEIR
                             current position dangerously uncovered?
                             Estimated by re-running the real Dangerous
                             Space scan with this one candidate removed
                             from the defending team and checking
                             whether a new/worse danger cell appears
                             near their current position.
4. `local_support`       -- how many other teammates are already near
                             this candidate's CURRENT position (more
                             support nearby = safer to move them, a
                             teammate can partially cover)

`CandidateScore.score` is a documented weighted combination; the
top-ranked candidate becomes the "recommended player," but the FULL
ranked list (with every component) is always returned so the
dashboard/report can show its reasoning, never just a bare name.
"""
import math
from dataclasses import dataclass, field

from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players
from dangerous_space_repositioning.analytics.dangerous_space import dangerous_space_for_team

SUPPORT_RADIUS_CM = 1500.0        # ~15m -- "a teammate close enough to help cover"
PROXIMITY_REF_CM = 3500.0         # ~35m -- distance at which proximity/feasibility have decayed to ~0

CANDIDATE_WEIGHTS = {
    "proximity": 0.35,
    "feasibility": 0.20,
    "abandonment_penalty": 0.30,   # subtracted, not added -- see compute_candidate_score
    "local_support": 0.15,
}


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _decay(distance_cm: float, ref_cm: float) -> float:
    return math.exp(-max(0.0, distance_cm) / max(1.0, ref_cm))


@dataclass
class CandidateScore:
    track_id: object
    x: float
    y: float
    distance_to_region_cm: float
    score: float
    components: dict


def _local_support(candidate: dict, teammates: list[dict]) -> tuple[float, int]:
    n = sum(1 for t in teammates if t["track_id"] != candidate["track_id"] and
            math.hypot(t["x_pitch"] - candidate["x_pitch"], t["y_pitch"] - candidate["y_pitch"]) <= SUPPORT_RADIUS_CM)
    return _clip01(n / 3.0), n


def abandonment_penalty(defending_team: int, candidate: dict, team_a_players: list[dict],
                          team_b_players: list[dict], ball, pitch,
                          attacking_team_actual: int | None = None) -> float:
    """A DELTA, not an absolute severity: removes `candidate` from the
    defending team entirely, re-scans Dangerous Space, and compares the
    resulting worst opponent-owned cell's severity to the worst cell
    WITH the candidate present. Only an INCREASE counts as a real
    abandonment cost -- same "only penalize a genuine worsening"
    convention `spatial_balance.py`'s own `new_gap_penalty` already
    uses, and for the same reason: this dataset's baseline severity
    tends to sit well above 0 everywhere (space is rarely perfectly
    "safe" on a real pitch), so an ABSOLUTE severity reading would flag
    almost every player as structurally load-bearing regardless of
    whether removing them specifically made anything worse. A real,
    re-derived comparison (not a static heuristic tag), using the exact
    same `dangerous_space_for_team` scoring the rest of this project
    already relies on."""
    own = team_a_players if defending_team == 0 else team_b_players
    other = team_b_players if defending_team == 0 else team_a_players
    reduced_own = [p for p in own if p["track_id"] != candidate["track_id"]]
    reduced_a = reduced_own if defending_team == 0 else other
    reduced_b = other if defending_team == 0 else reduced_own

    before = dangerous_space_for_team(defending_team, team_a_players, team_b_players, ball, pitch,
                                       attacking_team_actual=attacking_team_actual)
    after = dangerous_space_for_team(defending_team, reduced_a, reduced_b, ball, pitch,
                                      attacking_team_actual=attacking_team_actual)
    severity_before = before["top"].severity if before["valid"] and before["top"] else 0.0
    severity_after = after["top"].severity if after["valid"] and after["top"] else 0.0
    return _clip01(severity_after - severity_before)


def rank_candidates(defending_team: int, danger_region: tuple[float, float],
                     team_a_players: list[dict], team_b_players: list[dict],
                     rows_by_track: dict, ball=None, pitch=None,
                     attacking_team_actual: int | None = None) -> list[CandidateScore]:
    """`rows_by_track`: {track_id: raw build_quality_view row}, used
    only to exclude the goalkeeper from candidacy. `attacking_team_actual`
    is forwarded unchanged to `abandonment_penalty`'s own before/after
    `dangerous_space_for_team` calls, so a candidate's abandonment cost
    is judged by the SAME attacking-phase-aware severity as the rest of
    this round's correction."""
    from tactical_shared.coordinates import DEFAULT_PITCH
    pitch = pitch or DEFAULT_PITCH

    own = team_a_players if defending_team == 0 else team_b_players
    outfield = [p for p in own if rows_by_track.get(p["track_id"], {}).get("display_object_type") == "player"]
    rx, ry = danger_region

    scored = []
    for cand in outfield:
        dist = math.hypot(cand["x_pitch"] - rx, cand["y_pitch"] - ry)
        proximity = _decay(dist, PROXIMITY_REF_CM)
        feasibility = _clip01(1.0 - (dist / PROXIMITY_REF_CM) ** 2)
        abandon = abandonment_penalty(defending_team, cand, team_a_players, team_b_players, ball, pitch,
                                       attacking_team_actual=attacking_team_actual)
        support, n_support = _local_support(cand, outfield)

        score = (CANDIDATE_WEIGHTS["proximity"] * proximity +
                 CANDIDATE_WEIGHTS["feasibility"] * feasibility -
                 CANDIDATE_WEIGHTS["abandonment_penalty"] * abandon +
                 CANDIDATE_WEIGHTS["local_support"] * support)

        scored.append(CandidateScore(
            track_id=cand["track_id"], x=cand["x_pitch"], y=cand["y_pitch"],
            distance_to_region_cm=dist, score=score,
            components={"proximity": proximity, "feasibility": feasibility,
                        "abandonment_penalty": abandon, "local_support": support,
                        "n_teammates_supporting": n_support},
        ))
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored


def recommend_player(defending_team: int, danger_region: tuple[float, float],
                      team_a_players: list[dict], team_b_players: list[dict],
                      rows_by_track: dict, ball=None, pitch=None,
                      attacking_team_actual: int | None = None) -> CandidateScore | None:
    ranked = rank_candidates(defending_team, danger_region, team_a_players, team_b_players,
                              rows_by_track, ball, pitch, attacking_team_actual=attacking_team_actual)
    return ranked[0] if ranked else None
