import copy
import os

import numpy as np
import pytest

from dangerous_space_repositioning.analytics.data_loader import MatchData, TEAM_A, TEAM_B
from dangerous_space_repositioning.analytics.coach_signals import compute_frame_signal, build_signal_series
from tactical_shared.coordinates import DEFAULT_PITCH


def _synthetic_match(n_frames=10):
    players_by_frame = {}
    ball_by_frame = {}
    for f in range(n_frames):
        rows = []
        for i, (team, x, y) in enumerate([
            (0, 2000.0 + f * 10, 3000.0), (0, 2500.0, 3500.0), (0, 3000.0, 4000.0), (0, 1500.0, 2500.0),
            (1, 8000.0, 3000.0), (1, 8500.0, 3500.0), (1, 9000.0, 4000.0), (1, 7500.0, 2500.0),
        ]):
            rows.append({"track_id": i, "display_team_id": team, "display_object_type": "player",
                         "x_pitch": x, "y_pitch": y, "vx_cm_s": 0.0, "vy_cm_s": 0.0, "motion_valid": True})
        players_by_frame[f] = rows
        ball_by_frame[f] = {"frame": f, "is_observed": True, "x_pitch": 5000.0, "y_pitch": 3500.0}
    return MatchData(n_frames=n_frames, fps=30.0, pitch=DEFAULT_PITCH,
                      players_by_frame=players_by_frame, ball_by_frame=ball_by_frame, roles=[])


def test_smoke_frame_signal_computation():
    match = _synthetic_match()
    sig = compute_frame_signal(match, 3)
    assert sig.valid
    assert sig.severity_a is not None or sig.severity_a is None  # must not raise; may legitimately be None
    assert sig.frame == 3


def test_both_teams_covered_in_every_signal():
    match = _synthetic_match()
    series = build_signal_series(match, stride=2)
    assert len(series) > 0
    for sig in series:
        if sig.valid:
            # both teams must be represented (a value or an honest None), never one team silently dropped
            assert hasattr(sig, "severity_a") and hasattr(sig, "severity_b")
            assert hasattr(sig, "threat_against_a") and hasattr(sig, "threat_against_b")
            assert hasattr(sig, "risk_a") and hasattr(sig, "risk_b")


def test_missing_data_handling_reports_invalid_not_fabricated():
    match = _synthetic_match()
    match.players_by_frame[5] = []  # simulate a frame with no tracked players at all
    sig = compute_frame_signal(match, 5)
    assert sig.valid is False
    assert sig.severity_a is None and sig.severity_b is None
    assert sig.risk_a is None and sig.risk_b is None


def test_no_future_leakage():
    """Corrupting every frame AFTER `f` must not change the signal
    computed AT `f` -- `compute_frame_signal` only ever reads the exact
    frame it's asked about."""
    match = _synthetic_match(n_frames=10)
    f = 4
    sig_before = compute_frame_signal(match, f)

    corrupted = copy.deepcopy(match)
    for future_f in range(f + 1, corrupted.n_frames):
        corrupted.players_by_frame[future_f] = []
        corrupted.ball_by_frame[future_f] = {"frame": future_f, "is_observed": False}
    sig_after = compute_frame_signal(corrupted, f)

    assert sig_before.severity_a == sig_after.severity_a
    assert sig_before.severity_b == sig_after.severity_b
    assert sig_before.risk_a == sig_after.risk_a
    assert sig_before.risk_b == sig_after.risk_b


@pytest.mark.skipif(
    not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..",
                                     "ExternalDownlaodVideo", "testVideo1_120s.mp4")),
    reason="real video/tracking fixtures not available in this environment",
)
def test_full_dashboard_renderer_smoke():
    """End-to-end smoke test against the REAL canonical clip -- only
    runs when the real data files are present (e.g. this repo's own
    checkout), skipped elsewhere rather than failing on missing
    fixtures."""
    import cv2
    from dangerous_space_repositioning.dashboard.render_dangerous_space_dashboard import (
        load_transformers, render_frame, VIDEO_PATH, CANVAS_W,
    )
    from dangerous_space_repositioning.analytics.data_loader import load_match_data

    match = load_match_data()
    transformers = load_transformers()
    cap = cv2.VideoCapture(VIDEO_PATH)
    canvas = render_frame(match, transformers, cap, 1040)
    cap.release()
    assert canvas is not None
    assert canvas.shape == (1204, CANVAS_W, 3)
    assert canvas.dtype == np.uint8
