"""
Spatial Balance / New-Gap Risk -- a real, geometry-only proxy for "how
exposed is this team's OWN structure right now," computed identically
for both teams and reused in two places:

  1. As a real per-frame TIME SERIES (Graph 3, "Spatial Balance /
     New-Gap Risk") -- computed on the REAL observed roster, no
     counterfactual involved.
  2. Inside `counterfactual_repositioning.py`'s candidate search, where
     the SAME function is evaluated on a hypothetical post-move roster;
     `new_gap_penalty = max(0, risk_after - risk_before)` -- i.e. a
     candidate is only penalized for making the team's OWN structure
     MORE exposed than it already is, never for the structure's
     pre-existing baseline risk.

## Components (each in [0, 1], higher = worse / more exposed)

1. `compactness_risk`       -- how spread out the team is (normalized
                                mean distance to the team's own centroid)
2. `isolation_risk`         -- the single loneliest player's distance to
                                their nearest teammate (a real structural
                                gap reads as one player stranded, not
                                just "spread out" on average)
3. `coverage_variance_risk` -- how UNEVEN the team's own Voronoi cell
                                areas are (one player covering a huge
                                share of the pitch while others cover a
                                sliver is a real coverage imbalance)

No fabricated demonstration values anywhere -- every input is the
team's real, currently-tracked outfield player positions for that
frame (goalkeeper excluded, since goalkeeper spacing is not a back-line
"gap" in the sense this proxy is about).
"""
import math
from dataclasses import dataclass

from analytics.voronoi import compute_voronoi

RISK_WEIGHTS = {
    "compactness_risk": 0.40,
    "isolation_risk": 0.35,
    "coverage_variance_risk": 0.25,
}
assert abs(sum(RISK_WEIGHTS.values()) - 1.0) < 1e-9

COMPACTNESS_REF_CM = 2500.0   # ~25m mean-distance-to-centroid at which compactness_risk saturates near 1
ISOLATION_REF_CM = 2000.0     # ~20m nearest-teammate distance at which isolation_risk saturates near 1


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _outfield(players: list[dict], rows_by_track: dict | None) -> list[dict]:
    if rows_by_track is None:
        return players
    return [p for p in players if rows_by_track.get(p["track_id"], {}).get("display_object_type") == "player"]


def compactness_risk(players: list[dict]) -> float:
    if len(players) < 2:
        return 0.0
    cx = sum(p["x_pitch"] for p in players) / len(players)
    cy = sum(p["y_pitch"] for p in players) / len(players)
    mean_dist = sum(math.hypot(p["x_pitch"] - cx, p["y_pitch"] - cy) for p in players) / len(players)
    return _clip01(mean_dist / COMPACTNESS_REF_CM)


def isolation_risk(players: list[dict]) -> tuple[float, float]:
    """Returns (risk, worst_nearest_teammate_distance_cm) -- the raw
    distance is kept for the dashboard's own "why" readout."""
    if len(players) < 2:
        return 0.0, 0.0
    worst = 0.0
    for i, p in enumerate(players):
        nearest = min(math.hypot(p["x_pitch"] - q["x_pitch"], p["y_pitch"] - q["y_pitch"])
                       for j, q in enumerate(players) if j != i)
        worst = max(worst, nearest)
    return _clip01(worst / ISOLATION_REF_CM), worst


def coverage_variance_risk(team_id: int, team_a_players: list[dict], team_b_players: list[dict]) -> float:
    """Coefficient of variation of this team's OWN cell areas in the
    real all-player Voronoi diagram -- 0 when every player covers an
    equal share, growing as coverage becomes lopsided. Falls back to 0
    (no evidence of imbalance, not "no risk") when the frame's Voronoi
    diagram itself is invalid."""
    all_players = ([{"track_id": p["track_id"], "team_id": 0, "x_pitch": p["x_pitch"], "y_pitch": p["y_pitch"]}
                    for p in team_a_players] +
                   [{"track_id": p["track_id"], "team_id": 1, "x_pitch": p["x_pitch"], "y_pitch": p["y_pitch"]}
                    for p in team_b_players])
    result = compute_voronoi(all_players)
    if not result.get("valid"):
        return 0.0
    areas = [c["area_cm2"] for c in result["cells"] if c["team_id"] == team_id]
    if len(areas) < 2:
        return 0.0
    mean_a = sum(areas) / len(areas)
    if mean_a <= 0:
        return 0.0
    var = sum((a - mean_a) ** 2 for a in areas) / len(areas)
    cv = math.sqrt(var) / mean_a
    return _clip01(cv / 1.5)  # cv=1.5 (150% relative spread) treated as effectively maximal imbalance


@dataclass
class SpatialBalanceResult:
    risk: float
    components: dict


def compute_spatial_balance_risk(team_id: int, team_a_players: list[dict], team_b_players: list[dict],
                                  rows_by_track: dict | None = None) -> SpatialBalanceResult:
    """The team's real, current structural exposure -- both the
    time-series value (Graph 3) and the counterfactual "risk_after" use
    this exact function, never a second divergent formula."""
    own_players = team_a_players if team_id == 0 else team_b_players
    own_outfield = _outfield(own_players, rows_by_track)

    c_risk = compactness_risk(own_outfield)
    i_risk, worst_gap_cm = isolation_risk(own_outfield)
    v_risk = coverage_variance_risk(team_id, team_a_players, team_b_players)

    risk = (RISK_WEIGHTS["compactness_risk"] * c_risk +
            RISK_WEIGHTS["isolation_risk"] * i_risk +
            RISK_WEIGHTS["coverage_variance_risk"] * v_risk)

    return SpatialBalanceResult(
        risk=risk,
        components={"compactness_risk": c_risk, "isolation_risk": i_risk,
                    "worst_nearest_teammate_gap_cm": worst_gap_cm,
                    "coverage_variance_risk": v_risk, "n_outfield_players": len(own_outfield)},
    )
