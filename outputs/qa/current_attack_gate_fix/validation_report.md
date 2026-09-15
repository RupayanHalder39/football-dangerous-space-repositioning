# Validation Report — Current-Attack Eligibility Gate (Round 2)

## What changed from round 1

Round 1 (`outputs/qa/attack_relevance_fix/`) added a SOFT
multiplicative `direction_relevance` gate. Reviewing the corrected 20s
video showed the orange "Current Dangerous Space" highlight still
sometimes appearing clearly behind the active attack — a soft penalty
with a non-zero floor could still let a strongly-behind region win if
its other components were large enough.

Round 2 replaces this with a HARD eligibility filter (`classify_region`)
applied BEFORE any severity ranking. `severity` itself no longer
depends on possession/direction at all; eligibility only decides which
cells are even in the ranking pool for the primary "Current Dangerous
Space" selection.

## 1. Final backward tolerance

**`BACKWARD_TOLERANCE_CM = 500` (5 metres)** — kept at the brief's own
suggested starting value after empirical validation. Of 104 real
"resolved" primary-danger selections in a 475-frame broad sample, 37
(35.6%) fall in the within-tolerance band; every one of the 37 was
individually inspected (`behind_tolerance_audit.csv`,
`behind_tolerance_montage.png`) and sits visibly adjacent to the ball,
matching the brief's own named legitimate cases (cutback zones,
support pockets, short backward/diagonal next actions) rather than
unrelated far-behind exposure.

## 2. Final next-action relevance rule

```
next_action_relevant = (ball_distance_cm <= 3000) OR (receiver_support_score >= 0.15)
```

`3000cm` reuses the already-calibrated `BALL_PROXIMITY_REF_CM`
touchstone (no new number invented). `0.15` on the existing
`receiver_support_score` corresponds to roughly "a real attacking
player within ~15-16m." Applied to every longitudinally-eligible cell
(both "ahead" and "within backward tolerance"), this is what stops a
technically-forward but totally disconnected region (e.g. 40m from any
real play) from winning — verified directly by
`test_disconnected_far_forward_region_fails_next_action_relevance`.

## 3-5. Direction breakdown (475-frame broad sample, every 5th frame)

Among the 104 RESOLVED (eligible primary danger found) selections:

| | Round 1 (soft gate) | Round 2 (hard gate) |
|---|---|---|
| Ahead of ball / level | 53.3% | **64.4%** |
| Slightly behind (within tolerance) | 41.9% | **35.6%** |
| **Strongly behind** | 4.8% | **0.0%** |

**Strongly-behind primary-danger rate is 0% by construction** — a
structural guarantee of the hard gate (any cell beyond the tolerance is
excluded before ranking even happens), not a statistical tendency.

## 6. Uncertain / no-danger frame count

Of 475 sampled frames (every 5th frame, ≥4 tracked players):

| State | Count | % |
|---|---|---|
| Resolved (eligible primary danger) | 104 | 21.9% |
| Possession/ball/direction unknown | 308 | 64.8% |
| Context known, no eligible candidate | 63 | 13.3% |

Only ~22% of frames now show a primary Current Dangerous Space
highlight — a direct, disclosed consequence of "no recommendation
beats a nonsensical one." Graphs 1/2 are visibly sparser as a result
(see the demo clip and contact sheet).

## 7. Tests

`tests/test_attacking_phase_relevance.py`: rewritten for the new hard-
gate API, 26 tests (up from 18), all passing. `tests/
test_display_stability.py`: +1 confirmatory test (23 total). Three
pre-existing `test_dangerous_space.py` tests and one
`test_repositioning.py` test updated to supply real ball/possession
context (or bypass eligibility-gated code paths they didn't need) under
the new architecture.

```
external/sports/.venv/bin/python3 -m pytest dangerous_space_repositioning/tests/ -q
# 82 passed

external/sports/.venv/bin/python3 -m pytest tests/ -q
# 638 passed (unchanged elsewhere in the repo)
```

## 8. Corrected 20s video

`outputs/qa/current_attack_gate_fix/dangerous_space_repositioning_20s_demo.mp4`
— same clip (frames 440-1040), re-rendered with the hard eligibility
gate. Programmatic QA (frame count 601, fps 30.0, canvas 2304x1204,
duration 20.03s, 11 sampled frames non-blank and genuinely differing)
all passed. Visual inspection across the full clip (11 sample points,
every ~2 seconds) confirms: the orange highlight never appears clearly
behind the active attack — it is either a plausible, ball-adjacent
region, or absent entirely with an honest UNCERTAIN badge (with a
distinct subtitle for "insufficient tracking," "possession/direction
unknown," and "no eligible candidate this frame"). Direct old-vs-new
comparison (`gate_fix_old_vs_new_contact_sheet.png`) shows two of five
sampled timestamps (t=24.7s, t=29.7s) flip from a round-1 marginal
selection to an honest round-2 UNCERTAIN — exactly the intended
tightening.

## Display-stability interaction

No code change was needed in `dashboard/display_stability.py`. An
ineligible region flows through as `top=None`, which `render_frame`
already converts to `info=None`, the same signal already used for a
structurally-invalid Voronoi frame — both stabilizers already treat
this as an immediate, honest disappearance (established in the prior
display-stability round). A new test
(`test_region_resets_immediately_when_displayed_region_becomes_analytically_ineligible`)
locks this in explicitly. The 20-second rolling graph window, normal-
speed video, hysteresis, target smoothing, and label debounce are all
UNCHANGED and confirmed still working in the re-rendered clip.
