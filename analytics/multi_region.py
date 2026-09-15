"""
Top-3 Distinct Dangerous Regions -- spatial de-duplication and
multi-region fixer assignment, layered ENTIRELY on top of the existing,
UNCHANGED Current-Attack Eligibility pipeline (`dangerous_space.py`).

This module invents NO new severity/eligibility formula. It only:

1. Takes `dangerous_space_for_team(...)["eligible_ranked"]` -- the same
   already-eligible, already-severity-ranked list `top` is already
   picked from (`eligible_ranked[0] == top`) -- and walks it in order,
   suppressing a candidate that represents the SAME tactical pocket as
   an already-kept, higher-severity candidate (`select_top_regions`).
2. Assigns each surviving distinct region a fixer via the existing,
   UNCHANGED `player_responsibility.rank_candidates` /
   `counterfactual_repositioning.search_repositioning`, resolving the
   case where the same real player would naturally be the best fixer
   for two different regions (`assign_regions_and_fixers`).

## Why NOT simply take the top 3 Voronoi cells

Two or three of the highest-severity eligible cells are frequently
neighboring pieces of the SAME opponent-controlled pocket of space --
e.g. three cells owned by three attackers standing close together just
outside a defender's coverage radius. Presenting all three as
"independent problems" would overstate how many distinct tactical
issues actually exist and would assign 2-3 different "best fixers" to
what a single defender stepping into that pocket would actually solve.

## The exact de-duplication rule

Candidates are walked in already-severity-sorted order (so the
higher-severity of any two colliding candidates is always the one kept
-- ranking is never re-decided by this module, only pruned). A
candidate is SUPPRESSED (treated as the same tactical pocket) if its
drawn danger-circle would overlap or nearly touch an ALREADY-KEPT
region's own drawn circle:

    centroid_distance(candidate, kept) < OVERLAP_FACTOR * (r_candidate + r_kept)

where `r = sqrt(area_cm2 / pi)` is the EXACT radius formula this
project's own dashboard already uses to draw the danger circle (see
`dashboard/voronoi_broadcast_overlay.draw_danger_region`'s docstring) --
reusing an already-established, already-drawn quantity rather than
inventing a new distance constant. `OVERLAP_FACTOR = 1.5` is
deliberately a little more generous than exact circle-overlap (factor
1.0): two flagged pockets separated by less than half their combined
radii still read, to a coach looking at the screen, as "the same
patch of grass," not two independent problems -- matching the brief's
own explicit warning that neighboring cells can represent one tactical
issue. This is a documented, disclosed modeling choice (like every
other constant in this project), not a measured/fitted value.

`select_top_regions` never fabricates a third region: if fewer than
`max_regions` real, mutually-distinct eligible candidates exist, it
returns fewer (down to zero, when `eligible_ranked` is empty).

## Multi-region fixer assignment and conflict resolution

`assign_regions_and_fixers` walks the (already rank-ordered) surviving
regions from PRIMARY to lowest priority, and for each one calls the
existing `rank_candidates` UNCHANGED. If that region's own top-ranked
real candidate has ALREADY been assigned to a higher-priority region
this frame (`conflict=True`), the next-best candidate in that SAME
already-computed ranked list who is not yet assigned is used instead --
never a second, different selection heuristic, and never "pick the
nearest" (the existing `rank_candidates` ordering, proximity +
feasibility + abandonment_penalty + local_support, is reused exactly).
If every real candidate on the defending team is already assigned
(exhausted), the region is reported with `fixer_track_id=None` and
`reason="Same-player conflict / no independent fixer"` -- an honest
disclosure, never a fabricated second mover for the same player.
"""
import math
from dataclasses import dataclass

from dangerous_space_repositioning.analytics.player_responsibility import rank_candidates
from dangerous_space_repositioning.analytics.counterfactual_repositioning import search_repositioning

MAX_DANGER_REGIONS = 3

# See the module docstring's "exact de-duplication rule" -- generous
# enough to catch ADJACENT, not just strictly overlapping, cells.
DEDUP_OVERLAP_FACTOR = 1.5

REASON_SAME_PLAYER_CONFLICT = "Same-player conflict / no independent fixer"
REASON_NO_CANDIDATE = "no fixer candidate available this frame"


def region_radius_cm(area_cm2: float) -> float:
    """The identical `r = sqrt(area / pi)` formula already used to draw
    the danger circle on both the Match Feed and Radar panels -- reused
    here, not re-derived, so de-duplication judges overlap using the
    SAME size a viewer actually sees on screen."""
    return math.sqrt(max(area_cm2, 0.0) / math.pi)


def select_top_regions(eligible_ranked: list, max_regions: int = MAX_DANGER_REGIONS,
                        overlap_factor: float = DEDUP_OVERLAP_FACTOR) -> list:
    """`eligible_ranked`: a real, already-severity-sorted-descending list
    of scored regions (each with `.x`, `.y`, `.area_cm2`, `.severity`
    attributes -- `dangerous_space.DangerScore` in production, any
    duck-typed object in tests). Returns up to `max_regions` mutually
    DISTINCT regions, highest severity first, never fabricating a
    region that doesn't exist: an empty or short input yields an empty
    or short output.

    `eligible_ranked[0]`, if present, is ALWAYS kept (nothing outranks
    it to suppress it against), so `select_top_regions(...)[0]` is
    always identical to `dangerous_space_for_team(...)["top"]` -- the
    existing single-region pipeline's own primary selection is
    preserved exactly as index 0 of this richer result. Sorts
    defensively by severity descending itself (rather than trusting the
    caller already did) so this guarantee holds regardless of input
    order -- `dangerous_space_for_team`'s own `eligible_ranked` is
    already sorted this way, so this is a no-op in production, purely a
    robustness guard."""
    ranked = sorted(eligible_ranked, key=lambda c: c.severity, reverse=True)
    kept: list = []
    for cand in ranked:
        cand_r = region_radius_cm(cand.area_cm2)
        is_duplicate = any(
            math.hypot(cand.x - k.x, cand.y - k.y) < overlap_factor * (cand_r + region_radius_cm(k.area_cm2))
            for k in kept
        )
        if not is_duplicate:
            kept.append(cand)
        if len(kept) >= max_regions:
            break
    return kept


@dataclass
class RegionAssignment:
    rank: int                      # 1 = primary, 2 = secondary, 3 = tertiary
    danger: object                 # the DangerScore (or duck-typed equivalent) for this region
    fixer_track_id: object | None
    fixer_candidate: object | None  # the CandidateScore for the assigned fixer, or None
    conflict: bool                  # True iff this region's own top-ranked candidate was already claimed by a higher-priority region
    reason: str | None              # set only when fixer_track_id is None
    reposition: object | None       # the RepositioningRecommendation for the assigned fixer, or None


def assign_regions_and_fixers(defending_team: int, regions: list, team_a_players: list[dict],
                               team_b_players: list[dict], rows_by_track: dict, ball, pitch,
                               attacking_team_actual: int | None = None,
                               already_assigned: set | None = None, start_rank: int = 1) -> list[RegionAssignment]:
    """Walks `regions` (already rank-ordered, highest priority first --
    typically `select_top_regions`'s own output, or a slice of it) and
    assigns each a fixer via the existing, UNCHANGED `rank_candidates` /
    `search_repositioning`. `already_assigned`: track_ids to treat as
    already claimed BEFORE this call starts (e.g. the primary region's
    own already-stabilized fixer, when this function is called only for
    the secondary/tertiary slots) -- a region can never be assigned a
    fixer already claimed by a higher-priority region, whether that
    claim happened inside this call or before it. `start_rank`: the
    rank number of `regions[0]` (1 if `regions` includes the primary
    region itself, 2 if it starts at the secondary slot)."""
    assigned_ids = set(already_assigned or ())
    out = []
    for i, region in enumerate(regions):
        danger_point = (region.x, region.y)
        ranked = rank_candidates(defending_team, danger_point, team_a_players, team_b_players,
                                  rows_by_track, ball, pitch, attacking_team_actual=attacking_team_actual)
        conflict = bool(ranked) and ranked[0].track_id in assigned_ids
        chosen = next((c for c in ranked if c.track_id not in assigned_ids), None)

        reason = None
        reposition = None
        if chosen is not None:
            assigned_ids.add(chosen.track_id)
            reposition = search_repositioning(defending_team, chosen.track_id, danger_point,
                                               team_a_players, team_b_players, ball, rows_by_track,
                                               region.area_cm2, pitch, attacking_team_actual=attacking_team_actual)
        elif ranked:
            reason = REASON_SAME_PLAYER_CONFLICT
        else:
            reason = REASON_NO_CANDIDATE

        out.append(RegionAssignment(
            rank=start_rank + i, danger=region,
            fixer_track_id=(chosen.track_id if chosen else None),
            fixer_candidate=chosen, conflict=conflict, reason=reason, reposition=reposition,
        ))
    return out
