"""
Time-series signal builder for the three coach-mode graphs. Every value
is computed CAUSALLY, frame by frame, from the real tracking data --
never smoothed with a centered/future-aware filter, never fabricated
for a frame with insufficient evidence (such a frame reports `None`
values, which the renderer draws as a real gap, not an interpolated
line).

Produces one row per sampled frame with:
  - severity_a / severity_b            (Graph 1: Dangerous Space Severity,
    PRIMARY region only)
  - threat_against_a / threat_against_b (Graph 2: Opponent Control of
    Dangerous Space -- "how strongly the opponent can access this
    team's own flagged dangerous region", PRIMARY region only)
  - risk_a / risk_b                     (Graph 3: Spatial Balance / New-Gap Risk)
  - region_a / region_b                 ((x, y) of each team's flagged
    dangerous region this frame, or None -- used by the dashboard to
    draw the badge/overlay without re-running the full scan)
  - status_a / status_b                 ("resolved" / "no_eligible" /
    "uncertain" -- see the Top-3 fields below for why this distinction
    matters for honest bucketed aggregation)
  - top3_severity_a / top3_severity_b   (list of 0-3 severities, rank
    order, from the SAME already-computed `eligible_ranked` pool via
    the existing, unchanged `multi_region.select_top_regions` -- no new
    severity/eligibility formula, purely additive)
  - top3_access_a / top3_access_b       (opponent-control per ranked
    region, same list length/order as top3_severity_*)

The Top-3/status fields exist for the bucketed bar-chart graphs (see
`dashboard/live_graphs.py`'s `bucket_region_history`) -- they let a
bucket distinguish a REAL zero ("no eligible candidate this frame,"
`status="no_eligible"`) from GENUINELY UNKNOWN ("possession/tracking
unknown," `status="uncertain"`), so a bucket with no real signal at all
can be drawn as honestly MISSING rather than a fabricated zero.
"""
from dataclasses import dataclass, field

from dangerous_space_repositioning.analytics.data_loader import (
    MatchData, frame_players, rows_by_track_id, TEAM_A, TEAM_B,
)
from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players
from dangerous_space_repositioning.analytics.dangerous_space import (
    dangerous_space_for_team, REASON_UNCERTAIN_CONTEXT, REASON_NO_ELIGIBLE_CANDIDATE,
)
from dangerous_space_repositioning.analytics.opponent_access import opponent_control_of_region
from dangerous_space_repositioning.analytics.spatial_balance import compute_spatial_balance_risk
from dangerous_space_repositioning.analytics.multi_region import select_top_regions, MAX_DANGER_REGIONS

STATUS_RESOLVED = "resolved"
STATUS_NO_ELIGIBLE = "no_eligible"
STATUS_UNCERTAIN = "uncertain"


@dataclass
class FrameSignal:
    frame: int
    time_sec: float
    severity_a: float | None
    severity_b: float | None
    threat_against_a: float | None
    threat_against_b: float | None
    risk_a: float | None
    risk_b: float | None
    region_a: tuple | None
    region_b: tuple | None
    valid: bool
    attacking_team: int | None = None          # best available CAUSAL possession estimate this frame (None = unknown)
    possession_confidence: str = "uncertain"   # "current" / "4s_majority" / "12s_majority" / "30s_majority" / "uncertain"
    status_a: str = STATUS_UNCERTAIN
    status_b: str = STATUS_UNCERTAIN
    top3_severity_a: list = field(default_factory=list)
    top3_severity_b: list = field(default_factory=list)
    top3_access_a: list = field(default_factory=list)
    top3_access_b: list = field(default_factory=list)


def _status_and_top3(defending_team: int, danger: dict, team_a: list[dict], team_b: list[dict]):
    """Derives the honest bucketing `status` plus the Top-3 severity/
    access lists for ONE team, reusing already-computed results only --
    no new `dangerous_space_for_team` call, no new severity/eligibility
    formula."""
    if not danger["valid"]:
        return STATUS_UNCERTAIN, [], []
    if danger["top"] is None:
        reason = danger.get("reason")
        status = STATUS_NO_ELIGIBLE if reason == REASON_NO_ELIGIBLE_CANDIDATE else STATUS_UNCERTAIN
        return status, [], []
    distinct = select_top_regions(danger["eligible_ranked"], max_regions=MAX_DANGER_REGIONS)
    severities = [d.severity for d in distinct]
    accesses = [opponent_control_of_region(defending_team, (d.x, d.y), team_a, team_b) for d in distinct]
    return STATUS_RESOLVED, severities, accesses


def compute_frame_signal(match: MatchData, frame: int) -> FrameSignal:
    team_a, team_b = frame_players(match, frame)
    ball = match.ball_at(frame)
    rows = rows_by_track_id(match, frame)
    time_sec = frame / match.fps
    attacking_team_actual, possession_confidence = match.attacking_team_at(frame)

    if len(team_a) + len(team_b) < 4:
        return FrameSignal(frame, time_sec, None, None, None, None, None, None, None, None, False,
                            attacking_team_actual, possession_confidence)

    danger_a = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, match.pitch,
                                         attacking_team_actual=attacking_team_actual)
    danger_b = dangerous_space_for_team(TEAM_B, team_a, team_b, ball, match.pitch,
                                         attacking_team_actual=attacking_team_actual)

    severity_a = danger_a["top"].severity if danger_a["valid"] and danger_a["top"] else None
    severity_b = danger_b["top"].severity if danger_b["valid"] and danger_b["top"] else None
    region_a = (danger_a["top"].x, danger_a["top"].y) if danger_a["valid"] and danger_a["top"] else None
    region_b = (danger_b["top"].x, danger_b["top"].y) if danger_b["valid"] and danger_b["top"] else None

    threat_a = opponent_control_of_region(TEAM_A, region_a, team_a, team_b) if region_a else None
    threat_b = opponent_control_of_region(TEAM_B, region_b, team_a, team_b) if region_b else None

    risk_a = compute_spatial_balance_risk(TEAM_A, team_a, team_b, rows).risk
    risk_b = compute_spatial_balance_risk(TEAM_B, team_a, team_b, rows).risk

    status_a, top3_sev_a, top3_acc_a = _status_and_top3(TEAM_A, danger_a, team_a, team_b)
    status_b, top3_sev_b, top3_acc_b = _status_and_top3(TEAM_B, danger_b, team_a, team_b)

    return FrameSignal(frame, time_sec, severity_a, severity_b, threat_a, threat_b,
                        risk_a, risk_b, region_a, region_b, True,
                        attacking_team_actual, possession_confidence,
                        status_a, status_b, top3_sev_a, top3_sev_b, top3_acc_a, top3_acc_b)


def build_signal_series(match: MatchData, stride: int = 5, start_frame: int = 0,
                         end_frame: int | None = None) -> list[FrameSignal]:
    """Samples every `stride` frames across [start_frame, end_frame]
    (default: the whole clip). `stride` trades signal density for
    compute cost -- identical rationale to `analytics/voronoi.py`'s own
    `pitch_control_summary_series(stride=5)` default, reused here."""
    end_frame = match.n_frames - 1 if end_frame is None else end_frame
    return [compute_frame_signal(match, f) for f in range(start_frame, end_frame + 1, stride)]
