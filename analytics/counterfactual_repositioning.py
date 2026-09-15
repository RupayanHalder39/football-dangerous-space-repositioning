"""
"Where should he move?" -- bounded counterfactual repositioning search.

WORDING RULE (same convention `pressing_structure.analytics.
counterfactual_pressing` already established and this module deliberately
mirrors): results are described as "the best candidate within the
tested local search" or "recommended candidate reposition," NEVER
"optimal position" -- this is a bounded local grid over ONE player at a
time, not an exhaustive multi-player optimization, so global optimality
is never claimed or implied.

## Candidate generation (bounded, realistic, never a teleport)

For the recommended (or any given) player, two families of candidate
target positions are tested, both bounded to +/-300cm:

  A. A small local grid: every (dx, dy) combination of
     {-300,-200,-100,0,100,200,300} cm on each axis (identical
     convention to `counterfactual_pressing.DEFAULT_OFFSETS_CM`).
  B. Straight-line steps of 100/200/300 cm from the player's current
     position DIRECTLY TOWARD the flagged danger region -- the single
     most football-realistic "close the gap" direction, and one this
     project's brief explicitly invites ("other bounded candidate
     directions if justified").

Any candidate whose resulting (x, y) would fall outside the real pitch
rectangle is REJECTED outright (never clamped/teleported back onto the
pitch -- a clamp would silently understate how far the move actually
is).

## Benefit formula (documented, not hidden inside the code)

    benefit = danger_removed
            - new_gap_penalty
            - structural_damage_penalty
            - movement_cost_penalty

  - `danger_removed`      = severity_before minus severity_after, BOTH
                             evaluated with the IDENTICAL scoring
                             formula (`dangerous_space.severity_at_point`)
                             AT THE SAME FLAGGED REGION -- i.e. "did this
                             specific pocket of space actually get
                             safer," not "did the pitch-wide worst cell
                             change" (a single-defender move can rarely
                             move the global worst cell if a bigger,
                             unrelated problem exists elsewhere; that is
                             a real limitation of a one-player search,
                             not something to paper over by silently
                             re-anchoring to whatever the new worst cell
                             happens to be).
  - `new_gap_penalty`      = max(0, spatial_balance_risk_after -
                             spatial_balance_risk_before) for the
                             defending team's OWN structure (see
                             `spatial_balance.py`) -- only an INCREASE
                             in the team's own exposure is penalized.
  - `structural_damage_penalty` = the moved player's own abandonment
                             penalty (see `player_responsibility.py`),
                             evaluated ONCE against their REAL, ORIGINAL
                             position (not the candidate destination --
                             "how much did leaving your current spot
                             cost" does not depend on where you went) --
                             reused, not recomputed a second way, and
                             identical across every candidate for the
                             same player.
  - `movement_cost_penalty`= (distance_moved_cm / MAX_CANDIDATE_RADIUS_CM),
                             i.e. a full-radius move costs exactly 1.0
                             of penalty, a half-radius move costs 0.5.

All four terms are on comparable [0, ~1]-ish scales by construction, so
no term numerically dominates by accident; `BENEFIT_WEIGHTS` lets a
caller re-weight them without touching the search logic.
"""
from dataclasses import dataclass, field

from tactical_shared.coordinates import DEFAULT_PITCH
from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players, replace_player_position
from dangerous_space_repositioning.analytics.dangerous_space import severity_at_point
from dangerous_space_repositioning.analytics.spatial_balance import compute_spatial_balance_risk
from dangerous_space_repositioning.analytics.player_responsibility import abandonment_penalty

MAX_CANDIDATE_RADIUS_CM = 300.0
GRID_OFFSETS_CM = (-300.0, -200.0, -100.0, 0.0, 100.0, 200.0, 300.0)
DIRECT_STEP_DISTANCES_CM = (100.0, 200.0, 300.0)

BENEFIT_WEIGHTS = {
    # `danger_removed` is amplified (3x) because it is the project's
    # PRIMARY objective and, by construction, can only ever be a small
    # number: a single bounded (<=300cm) defensive move can only move
    # the ~50%-of-severity that is player-position-sensitive at all
    # (see dangerous_space.SEVERITY_WEIGHTS), through a smooth distance
    # decay -- realistic swings are on the order of 0.01-0.10, not
    # 0-1. Without this amplification the two guardrail penalties
    # (which sit on their own natural 0-1 scales) would numerically
    # dominate every case and the search could never recommend ANY
    # move, which would misrepresent the guardrails as more important
    # than the objective rather than honestly reflecting a real
    # improvement when one exists.
    "danger_removed": 3.0,
    "new_gap_penalty": 1.5,
    "structural_damage_penalty": 1.5,
    # Deliberately small: even the smallest tested step (100cm) already
    # carries a RAW movement_cost_penalty of 0.33 (100/300), which would
    # swamp every realistic `danger_removed` value (typically 0.001-0.02,
    # see the `danger_removed` comment above) at any weight above ~0.05.
    # This term exists to gently prefer a smaller move between two
    # otherwise-similar candidates, never to veto a genuine improvement
    # over moving at all.
    "movement_cost_penalty": 0.01,
}


def _grid_candidates(cx: float, cy: float) -> list[tuple[float, float]]:
    return [(cx + dx, cy + dy) for dx in GRID_OFFSETS_CM for dy in GRID_OFFSETS_CM]


def _direct_candidates(cx: float, cy: float, target_x: float, target_y: float) -> list[tuple[float, float]]:
    import math
    dx, dy = target_x - cx, target_y - cy
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return []
    ux, uy = dx / dist, dy / dist
    return [(cx + ux * step, cy + uy * step) for step in DIRECT_STEP_DISTANCES_CM
            if step <= dist]  # never overshoot past the danger region itself


def _in_pitch(x: float, y: float, pitch) -> bool:
    return 0.0 <= x <= pitch.length_cm and 0.0 <= y <= pitch.width_cm


@dataclass
class CandidateResult:
    x: float
    y: float
    distance_moved_cm: float
    danger_removed: float
    new_gap_penalty: float
    structural_damage_penalty: float
    movement_cost_penalty: float
    benefit: float
    rejected_reason: str | None = None


@dataclass
class RepositioningRecommendation:
    defending_team: int
    player_track_id: object
    current_x: float
    current_y: float
    best: CandidateResult | None
    all_candidates: list  # includes rejected ones, for full transparency
    interpretation: str


def evaluate_candidate(defending_team: int, player_track_id, candidate_xy: tuple[float, float],
                        team_a_players: list[dict], team_b_players: list[dict],
                        ball, rows_by_track: dict, danger_region: tuple[float, float], region_area_cm2: float,
                        severity_before: float, risk_before: float, structural_damage_penalty: float,
                        pitch=DEFAULT_PITCH, attacking_team_actual: int | None = None) -> CandidateResult:
    import math
    cur = next(p for p in (team_a_players if defending_team == 0 else team_b_players)
               if p["track_id"] == player_track_id)
    cx, cy = cur["x_pitch"], cur["y_pitch"]
    tx, ty = candidate_xy
    distance_moved = math.hypot(tx - cx, ty - cy)

    if not _in_pitch(tx, ty, pitch):
        return CandidateResult(tx, ty, distance_moved, 0.0, 0.0, 0.0, 0.0, float("-inf"),
                                rejected_reason="outside pitch bounds")
    if distance_moved > MAX_CANDIDATE_RADIUS_CM + 1e-6:
        return CandidateResult(tx, ty, distance_moved, 0.0, 0.0, 0.0, 0.0, float("-inf"),
                                rejected_reason=f"movement {distance_moved:.0f}cm exceeds bounded radius {MAX_CANDIDATE_RADIUS_CM:.0f}cm")

    if defending_team == 0:
        cf_a = replace_player_position(team_a_players, player_track_id, tx, ty)
        cf_b = team_b_players
    else:
        cf_a = team_a_players
        cf_b = replace_player_position(team_b_players, player_track_id, tx, ty)

    cf_defending = cf_a if defending_team == 0 else cf_b
    cf_attacking = cf_b if defending_team == 0 else cf_a
    rx, ry = danger_region
    severity_after = severity_at_point(defending_team, rx, ry, region_area_cm2, ball, cf_defending, cf_attacking,
                                        pitch, attacking_team_actual=attacking_team_actual)
    danger_removed = severity_before - severity_after

    risk_after = compute_spatial_balance_risk(defending_team, cf_a, cf_b, rows_by_track).risk
    new_gap_penalty = max(0.0, risk_after - risk_before)

    movement_cost_penalty = distance_moved / MAX_CANDIDATE_RADIUS_CM

    benefit = (BENEFIT_WEIGHTS["danger_removed"] * danger_removed -
               BENEFIT_WEIGHTS["new_gap_penalty"] * new_gap_penalty -
               BENEFIT_WEIGHTS["structural_damage_penalty"] * structural_damage_penalty -
               BENEFIT_WEIGHTS["movement_cost_penalty"] * movement_cost_penalty)

    return CandidateResult(tx, ty, distance_moved, danger_removed, new_gap_penalty,
                            structural_damage_penalty, movement_cost_penalty, benefit, None)


def search_repositioning(defending_team: int, player_track_id, danger_region: tuple[float, float],
                          team_a_players: list[dict], team_b_players: list[dict],
                          ball, rows_by_track: dict, region_area_cm2: float = 3_000_000.0,
                          pitch=DEFAULT_PITCH, attacking_team_actual: int | None = None) -> RepositioningRecommendation:
    """The main entry point: bounded local search for ONE player. Never
    claims a global optimum -- `interpretation` says so explicitly.
    `region_area_cm2`: the flagged danger cell's real area (from
    `dangerous_space.DangerScore.area_cm2`) -- passed through so
    `severity_at_point` scores the counterfactual using the same
    real area-gate, not a made-up default. A caller that doesn't have
    it (e.g. a synthetic test) may leave the disclosed default.

    `attacking_team_actual`: the best available CAUSAL possession
    estimate for this frame (or `None` if unknown), forwarded UNCHANGED
    to every `severity_at_point`/`abandonment_penalty` call this search
    makes -- `danger_region` and `attacking_team_actual` are both held
    fixed across the WHOLE search, so severity_before and every
    candidate's severity_after are evaluated with the identical
    attacking-phase-relevance gate at the identical point. The search
    can never "win" by having a hypothetical move accidentally change
    which region or which attacking-phase context is being judged (see
    HANDOFF.md's "Attacking-Phase Relevance Correction" §9)."""
    cur = next((p for p in (team_a_players if defending_team == 0 else team_b_players)
                if p["track_id"] == player_track_id), None)
    if cur is None:
        return RepositioningRecommendation(defending_team, player_track_id, 0.0, 0.0, None, [],
                                            "TARGET_NOT_ON_DEFENDING_TEAM")
    cx, cy = cur["x_pitch"], cur["y_pitch"]

    defending_players = team_a_players if defending_team == 0 else team_b_players
    attacking_players = team_b_players if defending_team == 0 else team_a_players
    rx, ry = danger_region
    severity_before = severity_at_point(defending_team, rx, ry, region_area_cm2, ball,
                                         defending_players, attacking_players, pitch,
                                         attacking_team_actual=attacking_team_actual)
    risk_before = compute_spatial_balance_risk(defending_team, team_a_players, team_b_players, rows_by_track).risk
    # Structural cost of leaving the CURRENT position -- independent of
    # destination, so computed once and reused for every candidate.
    structural_damage_penalty = abandonment_penalty(defending_team, cur, team_a_players, team_b_players, ball, pitch,
                                                      attacking_team_actual=attacking_team_actual)

    candidates_xy = set(_grid_candidates(cx, cy)) | set(_direct_candidates(cx, cy, *danger_region))
    candidates_xy.discard((cx, cy))  # the zero-move baseline is meaningless as a "recommendation"

    results = [evaluate_candidate(defending_team, player_track_id, xy, team_a_players, team_b_players,
                                   ball, rows_by_track, danger_region, region_area_cm2,
                                   severity_before, risk_before, structural_damage_penalty, pitch,
                                   attacking_team_actual=attacking_team_actual)
               for xy in candidates_xy]

    valid_results = [r for r in results if r.rejected_reason is None]
    best = max(valid_results, key=lambda r: r.benefit) if valid_results else None

    if best is None:
        interpretation = "no valid candidate found within the bounded local search"
    elif best.benefit > 0:
        interpretation = "candidate improved structure -- best candidate within the tested local search, not a proven optimum"
    else:
        interpretation = "no improving local candidate found -- the observed position already scores best within the searched grid"

    return RepositioningRecommendation(defending_team, player_track_id, cx, cy, best, results, interpretation)
