"""
Tests for Top-3 Distinct Dangerous Regions (`analytics/multi_region.py`)
and its causal display-stability layer
(`dashboard/display_stability.MultiRegionStabilizer`).
"""
from dataclasses import dataclass

from dangerous_space_repositioning.analytics.data_loader import TEAM_A, TEAM_B
from tactical_shared.coordinates import DEFAULT_PITCH
from dangerous_space_repositioning.analytics.multi_region import (
    select_top_regions, assign_regions_and_fixers, region_radius_cm,
    MAX_DANGER_REGIONS, REASON_SAME_PLAYER_CONFLICT, REASON_NO_CANDIDATE,
)
from dangerous_space_repositioning.dashboard.display_stability import MultiRegionStabilizer


# ---------------------------------------------------------------- fixtures

@dataclass
class _FakeDanger:
    track_id: object
    x: float
    y: float
    area_cm2: float
    severity: float


def _region(tid, x, y, severity, area_cm2=2_000_000.0):
    return _FakeDanger(tid, x, y, area_cm2, severity)


def _rows(players):
    return {p["track_id"]: {"display_object_type": "player"} for p in players}


# ---------------------------------------------------------------- select_top_regions

def test_top3_ranking_keeps_highest_severity_first():
    regions = [
        _region("a", 1000, 1000, 0.30),
        _region("b", 9000, 6000, 0.80),
        _region("c", 5000, 3500, 0.55),
    ]
    out = select_top_regions(regions, max_regions=MAX_DANGER_REGIONS)
    assert [r.track_id for r in out] == ["b", "c", "a"], "must be severity-sorted, not input order"


def test_top3_never_exceeds_max_regions():
    regions = [_region(i, i * 5000, 100, 1.0 - i * 0.01) for i in range(6)]  # 6 far-apart candidates
    out = select_top_regions(regions, max_regions=3)
    assert len(out) == 3


def test_fewer_than_3_valid_regions_are_never_fabricated():
    assert select_top_regions([], max_regions=3) == []
    one = [_region("a", 1000, 1000, 0.5)]
    assert len(select_top_regions(one, max_regions=3)) == 1
    two = [_region("a", 1000, 1000, 0.5), _region("b", 9000, 6000, 0.4)]
    assert len(select_top_regions(two, max_regions=3)) == 2


def test_overlapping_neighboring_candidates_are_deduplicated():
    """Two candidates whose drawn circles clearly overlap (same real
    tactical pocket) must collapse to ONE distinct region -- the
    project's own explicit anti-pattern: 'do not simply take the top 3
    Voronoi cells.'"""
    r = region_radius_cm(2_000_000.0)
    assert r > 0
    close = [
        _region("primary", 5000, 3500, 0.80, area_cm2=2_000_000.0),
        _region("neighbor", 5000 + r * 0.3, 3500, 0.70, area_cm2=2_000_000.0),  # well within overlap distance
    ]
    out = select_top_regions(close, max_regions=3)
    assert len(out) == 1
    assert out[0].track_id == "primary", "the higher-severity candidate of the pair must be the one kept"


def test_distinct_far_apart_candidates_are_not_suppressed():
    regions = [
        _region("a", 1000, 1000, 0.80),
        _region("b", 9000, 6000, 0.70),  # far away -- a genuinely separate tactical problem
    ]
    out = select_top_regions(regions, max_regions=3)
    assert {r.track_id for r in out} == {"a", "b"}


def test_first_selected_region_always_matches_the_single_region_pipelines_top():
    """`select_top_regions(...)[0]` must always be identical to what
    `dangerous_space_for_team(...)["top"]` (the existing, unchanged
    single-region selection) would pick -- the primary marker's
    real value must never change because of this round's new logic."""
    regions = [
        _region("a", 1000, 1000, 0.30),
        _region("b", 9000, 6000, 0.80),
        _region("c", 5000, 3500, 0.55),
    ]
    top = max(regions, key=lambda r: r.severity)  # mirrors eligible_ranked[0]/`top`'s own selection
    out = select_top_regions(regions, max_regions=3)
    assert out[0] is top


def test_top3_ranking_is_symmetric_between_team_roles():
    """The de-duplication/ranking logic must not hardcode any team-role
    assumption -- it operates purely on generic (x, y, area, severity)
    regions, so calling it for team A's or team B's own candidate pool
    must behave identically given equivalent inputs."""
    regions_a = [_region("x", 1000, 1000, 0.9), _region("y", 9000, 6000, 0.5)]
    regions_b = [_region("x", 1000, 1000, 0.9), _region("y", 9000, 6000, 0.5)]
    out_a = select_top_regions(regions_a, max_regions=3)
    out_b = select_top_regions(regions_b, max_regions=3)
    assert [r.track_id for r in out_a] == [r.track_id for r in out_b]


# ---------------------------------------------------------------- assign_regions_and_fixers

def test_fixer_assignment_no_conflict_when_regions_have_independent_candidates():
    team_a = [{"track_id": "near1", "x_pitch": 5100.0, "y_pitch": 3500.0},
              {"track_id": "near2", "x_pitch": 9100.0, "y_pitch": 6100.0}]
    team_b = [{"track_id": "att1", "x_pitch": 5000.0, "y_pitch": 3500.0}]
    regions = [_region("r1", 5000, 3500, 0.8), _region("r2", 9000, 6000, 0.6)]
    out = assign_regions_and_fixers(TEAM_A, regions, team_a, team_b, _rows(team_a), ball=None, pitch=DEFAULT_PITCH)
    assert out[0].fixer_track_id == "near1"
    assert out[1].fixer_track_id == "near2"
    assert out[0].conflict is False and out[1].conflict is False


def test_same_player_conflict_falls_back_to_next_best_candidate():
    """One player is CLEARLY the best fixer for both regions (equidistant,
    centrally placed) but a second, viable candidate exists for the
    lower-priority region -- the higher-priority region keeps the
    natural best fixer, and the lower-priority one must fall back to
    the next-best REAL candidate, never invent a second mover for the
    same player."""
    team_a = [{"track_id": "central", "x_pitch": 5000.0, "y_pitch": 3500.0},
              {"track_id": "backup", "x_pitch": 5300.0, "y_pitch": 3500.0}]
    team_b = [{"track_id": "att1", "x_pitch": 5000.0, "y_pitch": 3500.0}]
    # Two regions both closest to "central".
    regions = [_region("r1", 4900, 3500, 0.9), _region("r2", 5100, 3500, 0.7)]
    out = assign_regions_and_fixers(TEAM_A, regions, team_a, team_b, _rows(team_a), ball=None, pitch=DEFAULT_PITCH)
    assert out[0].fixer_track_id == "central", "primary keeps the natural best fixer"
    assert out[0].conflict is False
    assert out[1].fixer_track_id == "backup", "secondary must fall back to the next-best REAL candidate"
    assert out[1].conflict is True, "a real conflict occurred even though a fallback was found"


def test_same_player_conflict_with_no_alternative_is_reported_honestly():
    """When only ONE real candidate exists at all, a second region can
    never get an independent fixer -- must be reported honestly, never
    fabricated."""
    team_a = [{"track_id": "only_one", "x_pitch": 5000.0, "y_pitch": 3500.0}]
    team_b = [{"track_id": "att1", "x_pitch": 5000.0, "y_pitch": 3500.0}]
    regions = [_region("r1", 4900, 3500, 0.9), _region("r2", 5100, 3500, 0.7)]
    out = assign_regions_and_fixers(TEAM_A, regions, team_a, team_b, _rows(team_a), ball=None, pitch=DEFAULT_PITCH)
    assert out[0].fixer_track_id == "only_one"
    assert out[1].fixer_track_id is None
    assert out[1].conflict is True
    assert out[1].reason == REASON_SAME_PLAYER_CONFLICT
    assert out[1].reposition is None


def test_no_candidate_available_is_a_distinct_reason_from_conflict():
    """An empty defending roster is a different honest condition from a
    same-player conflict -- must not be mislabeled as a conflict."""
    regions = [_region("r1", 4900, 3500, 0.9)]
    out = assign_regions_and_fixers(TEAM_A, regions, [], [], {}, ball=None, pitch=DEFAULT_PITCH)
    assert out[0].fixer_track_id is None
    assert out[0].conflict is False
    assert out[0].reason == REASON_NO_CANDIDATE


def test_already_assigned_seed_prevents_reusing_the_primary_fixer():
    """The primary region's own already-stabilized fixer, passed in via
    `already_assigned`, must never be re-selected for a secondary
    region even though this call never itself computed that primary
    assignment."""
    team_a = [{"track_id": "primary_fixer", "x_pitch": 5000.0, "y_pitch": 3500.0},
              {"track_id": "other", "x_pitch": 5300.0, "y_pitch": 3500.0}]
    team_b = [{"track_id": "att1", "x_pitch": 5000.0, "y_pitch": 3500.0}]
    regions = [_region("r2", 5000, 3500, 0.7)]  # closest real candidate is "primary_fixer"
    out = assign_regions_and_fixers(TEAM_A, regions, team_a, team_b, _rows(team_a), ball=None, pitch=DEFAULT_PITCH,
                                     already_assigned={"primary_fixer"}, start_rank=2)
    assert out[0].rank == 2
    assert out[0].fixer_track_id == "other"
    assert out[0].conflict is True


def test_fixer_assignment_symmetric_between_team_roles():
    team_1_style = [{"track_id": "near1", "x_pitch": 5100.0, "y_pitch": 3500.0}]
    team_0_style = [{"track_id": "att1", "x_pitch": 5000.0, "y_pitch": 3500.0}]
    regions = [_region("r1", 5000, 3500, 0.8)]
    out_a = assign_regions_and_fixers(TEAM_A, regions, team_1_style, team_0_style, _rows(team_1_style), ball=None, pitch=DEFAULT_PITCH)
    out_b = assign_regions_and_fixers(TEAM_B, regions, team_0_style, team_1_style, _rows(team_1_style), ball=None, pitch=DEFAULT_PITCH)
    assert out_a[0].fixer_track_id == out_b[0].fixer_track_id == "near1"


# ---------------------------------------------------------------- MultiRegionStabilizer

def test_multi_region_stabilizer_keeps_occupant_when_still_present():
    stab = MultiRegionStabilizer(n_slots=2, min_hold_sec=0.5, switch_margin=0.03)
    frame1 = [_region("a", 1000, 1000, 0.5), _region("b", 9000, 6000, 0.4)]
    out1 = stab.update(0.0, frame1)
    assert [r.track_id for r in out1] == ["a", "b"]

    # Same two candidates, slightly refreshed severities -- must not reorder/flicker.
    frame2 = [_region("a", 1010, 1000, 0.52), _region("b", 9010, 6000, 0.45)]
    out2 = stab.update(0.033, frame2)
    assert [r.track_id for r in out2] == ["a", "b"]


def test_multi_region_stabilizer_does_not_switch_within_hold():
    stab = MultiRegionStabilizer(n_slots=1, min_hold_sec=0.5, switch_margin=0.03)
    stab.update(0.0, [_region("a", 1000, 1000, 0.50)])
    # A clearly stronger candidate appears, but within the hold window.
    out = stab.update(0.1, [_region("a", 1000, 1000, 0.50), _region("b", 9000, 6000, 0.90)])
    assert [r.track_id for r in out] == ["a"], "must not switch before min_hold_sec has elapsed"


def test_multi_region_stabilizer_switches_after_hold_when_meaningfully_stronger():
    stab = MultiRegionStabilizer(n_slots=1, min_hold_sec=0.5, switch_margin=0.03)
    stab.update(0.0, [_region("a", 1000, 1000, 0.50)])
    out = stab.update(0.6, [_region("a", 1000, 1000, 0.50), _region("b", 9000, 6000, 0.90)])
    assert [r.track_id for r in out] == ["b"], "must switch once hold has elapsed and the new candidate is clearly stronger"


def test_multi_region_stabilizer_does_not_switch_for_near_equal_candidate():
    stab = MultiRegionStabilizer(n_slots=1, min_hold_sec=0.0, switch_margin=0.03)
    stab.update(0.0, [_region("a", 1000, 1000, 0.50)])
    out = stab.update(1.0, [_region("a", 1000, 1000, 0.50), _region("b", 9000, 6000, 0.51)])
    assert [r.track_id for r in out] == ["a"], "a near-equal candidate must not cause a flicker-inducing switch"


def test_multi_region_stabilizer_removes_slot_immediately_when_track_id_disappears():
    stab = MultiRegionStabilizer(n_slots=2, min_hold_sec=0.5, switch_margin=0.03)
    stab.update(0.0, [_region("a", 1000, 1000, 0.5), _region("b", 9000, 6000, 0.4)])
    # "b" is analytically gone this frame (e.g. merged away / no longer eligible) -- no replacement offered.
    out = stab.update(0.05, [_region("a", 1000, 1000, 0.5)])
    assert [r.track_id for r in out] == ["a"], "a vanished region must be dropped immediately, never held"


def test_multi_region_stabilizer_fills_empty_slot_immediately_no_hold_needed():
    stab = MultiRegionStabilizer(n_slots=2, min_hold_sec=0.5, switch_margin=0.03)
    stab.update(0.0, [_region("a", 1000, 1000, 0.5)])  # only 1 real region this frame
    # A second real region appears moments later -- must fill the empty slot immediately.
    out = stab.update(0.01, [_region("a", 1000, 1000, 0.5), _region("b", 9000, 6000, 0.4)])
    assert {r.track_id for r in out} == {"a", "b"}


def test_multi_region_stabilizer_clears_all_slots_on_full_gap():
    stab = MultiRegionStabilizer(n_slots=2)
    stab.update(0.0, [_region("a", 1000, 1000, 0.5), _region("b", 9000, 6000, 0.4)])
    out = stab.update(0.05, [])
    assert out == []


def test_multi_region_stabilizer_never_exceeds_n_slots():
    stab = MultiRegionStabilizer(n_slots=2)
    out = stab.update(0.0, [_region(i, i * 3000, 1000, 1.0 - i * 0.1) for i in range(5)])
    assert len(out) <= 2


def test_no_future_leakage_multi_region_stabilizer():
    def make_prefix_outputs(stab):
        out = [stab.update(0.0, [_region("a", 1000, 1000, 0.5), _region("b", 9000, 6000, 0.4)])]
        out.append(stab.update(0.2, [_region("a", 1010, 1000, 0.52), _region("b", 9010, 6000, 0.41)]))
        return [[r.track_id for r in frame_out] for frame_out in out]

    stab_a = MultiRegionStabilizer(n_slots=2, min_hold_sec=0.5, switch_margin=0.03)
    prefix_a = make_prefix_outputs(stab_a)
    stab_a.update(0.9, [_region("c", 500, 500, 99.0)])  # future A: a wildly stronger candidate appears

    stab_b = MultiRegionStabilizer(n_slots=2, min_hold_sec=0.5, switch_margin=0.03)
    prefix_b = make_prefix_outputs(stab_b)
    stab_b.update(0.9, [])  # future B: everything disappears

    assert prefix_a == prefix_b, "identical real prefixes must produce identical outputs regardless of what happens after"
