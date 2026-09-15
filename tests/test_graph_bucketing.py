"""
Tests for the Graph 1/2 bucketed-bar aggregation
(`dashboard/live_graphs.bucket_region_history`) -- the display-only
readability redesign that replaced per-frame line charts with fixed
time-bucket bars. Exercised as pure data transforms (no video, no real
match data), since honesty of the aggregation is a data-shaping
concern, not a rendering one.
"""
from dangerous_space_repositioning.analytics.coach_signals import STATUS_RESOLVED, STATUS_NO_ELIGIBLE, STATUS_UNCERTAIN
from dangerous_space_repositioning.dashboard.live_graphs import bucket_region_history


def _sample(t, status, top3_severity=None, top3_access=None):
    return {"time_sec": t, "status": status,
            "top3_severity": top3_severity or [], "top3_access": top3_access or []}


def test_bucket_is_missing_when_every_sample_is_uncertain():
    samples = [_sample(t, STATUS_UNCERTAIN) for t in (0.5, 1.5, 2.5, 3.5)]
    buckets = bucket_region_history(samples, 0.0, 4.0, 4.0)
    assert len(buckets) == 1
    assert buckets[0]["rank_severity"] == [None, None, None]
    assert buckets[0]["rank_access"] == [None, None, None]
    assert buckets[0]["n_defined_samples"] == 0


def test_bucket_is_a_real_zero_when_every_sample_is_no_eligible():
    """A frame with known context but no eligible candidate is a REAL,
    analytically-confirmed zero -- must NOT be treated as missing."""
    samples = [_sample(t, STATUS_NO_ELIGIBLE) for t in (0.5, 1.5, 2.5, 3.5)]
    buckets = bucket_region_history(samples, 0.0, 4.0, 4.0)
    assert buckets[0]["rank_severity"] == [0.0, 0.0, 0.0]
    assert buckets[0]["n_defined_samples"] == 4


def test_bucket_mean_is_a_real_causal_mean_of_resolved_values():
    samples = [
        _sample(0.5, STATUS_RESOLVED, top3_severity=[0.4, 0.2], top3_access=[0.6, 0.3]),
        _sample(1.5, STATUS_RESOLVED, top3_severity=[0.6, 0.0], top3_access=[0.8, 0.0]),
    ]
    buckets = bucket_region_history(samples, 0.0, 4.0, 4.0)
    rank0, rank1, rank2 = buckets[0]["rank_severity"]
    assert abs(rank0 - 0.5) < 1e-9   # mean(0.4, 0.6)
    assert abs(rank1 - 0.1) < 1e-9   # mean(0.2, 0.0)
    assert rank2 == 0.0              # neither sample had a rank-2 entry -> real zero, not missing
    acc0, acc1, _ = buckets[0]["rank_access"]
    assert abs(acc0 - 0.7) < 1e-9
    assert abs(acc1 - 0.15) < 1e-9


def test_uncertain_samples_are_excluded_not_averaged_as_zero():
    """A mix of real evidence and genuinely-unknown frames must average
    over ONLY the real evidence -- an uncertain frame must not silently
    drag the mean toward zero."""
    samples = [
        _sample(0.5, STATUS_RESOLVED, top3_severity=[0.8], top3_access=[0.9]),
        _sample(1.5, STATUS_UNCERTAIN),
        _sample(2.5, STATUS_UNCERTAIN),
    ]
    buckets = bucket_region_history(samples, 0.0, 4.0, 4.0)
    assert buckets[0]["rank_severity"][0] == 0.8, "the single real sample's own value, not diluted by unknown frames"
    assert buckets[0]["n_defined_samples"] == 1


def test_bucket_count_grows_with_available_window_never_fabricates_before_kickoff():
    """Near the start of the match, the real elapsed window is shorter
    than the full rolling window -- must yield FEWER real buckets, never
    a fabricated empty one for time before frame 0 (mirrors the existing
    line-graph's own growing-window convention at the very start)."""
    samples = [_sample(t, STATUS_NO_ELIGIBLE) for t in (0.5, 4.5, 8.5)]
    buckets_short = bucket_region_history(samples, 0.0, 8.0, 4.0)
    assert len(buckets_short) == 2
    buckets_full = bucket_region_history(samples, 0.0, 24.0, 4.0)
    assert len(buckets_full) == 6


def test_bucket_never_produces_more_than_3_ranks():
    samples = [_sample(0.5, STATUS_RESOLVED, top3_severity=[0.9, 0.8, 0.7], top3_access=[0.5, 0.5, 0.5])]
    buckets = bucket_region_history(samples, 0.0, 4.0, 4.0)
    assert len(buckets[0]["rank_severity"]) == 3
    assert len(buckets[0]["rank_access"]) == 3


def test_no_future_leakage_bucket_aggregation():
    """A bucket's own aggregate must depend only on samples whose
    `time_sec` falls inside it -- appending FUTURE samples beyond the
    queried window must not change an already-computed bucket."""
    samples = [_sample(t, STATUS_RESOLVED, top3_severity=[0.5], top3_access=[0.5]) for t in (0.5, 1.5, 2.5, 3.5)]
    buckets_before = bucket_region_history(samples, 0.0, 4.0, 4.0)

    samples_with_future = samples + [_sample(99.0, STATUS_RESOLVED, top3_severity=[1.0], top3_access=[1.0])]
    buckets_after = bucket_region_history(samples_with_future, 0.0, 4.0, 4.0)

    assert buckets_before == buckets_after
