"""
Dangerous Space Severity -- a proxy, not a scoring-probability model.

Explicitly NOT: "largest Voronoi cell = dangerous." Cell area is used
only as a final damping gate (a vanishingly small pocket cannot be
meaningfully dangerous regardless of context), never as the primary
signal. The primary signal is a small set of interpretable, documented,
football-contextual components, each normalized to [0, 1] and combined
with DOCUMENTED weights (see `docs/METRIC_DEFINITIONS.md` for the
formal write-up -- this module's constants ARE that documentation's
source of truth, kept in sync deliberately).

## What "dangerous space" means here

For a defending team X, we look at every Voronoi cell in the all-player
diagram that the OPPONENT (1 - X) currently owns (see
`voronoi_control.opponent_owned_cells`), score each one, and report the
single highest-scoring cell as "the" dangerous region against team X
this frame, plus the full ranked list (never just a bare number -- the
`why` is always inspectable).

## Components (each in [0, 1], higher = more dangerous)

1. `goal_proximity`   -- how close the cell is to team X's own goal
2. `centrality`       -- how close the cell is to the central/half-space
                         corridor (touchline space is less dangerous)
3. `ball_proximity`   -- how close the cell is to the ball RIGHT NOW
                         (this project's own "next-action relevance"
                         proxy: how immediately reachable is this
                         specific region from the ball's current spot)
4. `receiver_support` -- how many opponent attackers could plausibly
                         receive there (a real, nearby-attacker count)
5. `coverage_gap`     -- how FEW of team X's own defenders are nearby
                         (the inverse of defensive coverage density)

`SEVERITY_WEIGHTS` documents the exact combination; `area_gate` then
damps (never zeroes) a very small cell's score.

## Current-Attack Eligibility (HARD gate, not a soft multiplier)

**Round 2 of the attacking-phase correction.** The first round
(`direction_relevance`, a soft multiplicative penalty with a non-zero
floor) measurably improved things but a strongly-behind-the-ball cell
could still win the primary ranking outright if its other components
were large enough -- unacceptable for the PRIMARY coach-facing "Current
Dangerous Space" label, whose meaning must be locked to *"space the
CURRENT attacking team can plausibly exploit in the current/next
attacking action"* -- never *"the most spatially exposed region
anywhere on the pitch."*

`classify_region()` now runs as an ELIGIBILITY FILTER **before**
ranking (see `dangerous_space_for_team`'s own docstring for the exact
pipeline order) -- an ineligible cell is EXCLUDED from the primary
ranking pool entirely, never scored down and left in contention:

1. **Possession/ball/direction unknown** → category `"UNCERTAIN"`,
   `eligible=False`. Per this round's explicit brief: *"do NOT fall
   back to a random exposed cell... return UNCERTAIN / NO CURRENT
   ATTACKING DANGER"* -- a reversal of round 1's "neutral gate, fall
   back to the undirected ranking" choice, made deliberately: showing
   no recommendation beats showing a tactically nonsensical one.
2. **`defending_team`'s own team has the ball** (not their opponent) →
   category `"COUNTERATTACK_EXPOSURE"`, `eligible=False` -- there is no
   current attack against `defending_team` at all right now. Stored
   diagnostically (`components["category"]`), never shown as the
   primary highlight.
3. **Longitudinal progress check**: `progress_cm = (x - ball_x) *
   attacking_sign(attacking_team)`. `progress_cm < -BACKWARD_TOLERANCE_CM`
   (clearly behind the live attack) → category `"SUPPORT_SPACE"`,
   `eligible=False`. Within tolerance (`>= -BACKWARD_TOLERANCE_CM`,
   covering both "ahead" and "small backward/cutback" cases) →
   continues to step 4.
4. **Next-action reachability check** (`NEXT_ACTION_BALL_DIST_CM` /
   `NEXT_ACTION_MIN_RECEIVER_SCORE`, see `classify_region`'s own
   docstring): a longitudinally-eligible cell that is nevertheless
   disconnected from the ball AND has no real attacker nearby (e.g.
   technically "ahead" but 40m away with nobody near it) → category
   `"SUPPORT_SPACE"`, `eligible=False`.
5. Only a cell passing BOTH gates → category `"CURRENT_DANGEROUS_SPACE"`,
   `eligible=True` -- eligible for the primary ranking.

`dangerous_space_for_team` ranks Dangerous Space Severity ONLY among
`eligible=True` cells for `top` (the primary highlight); the full,
unfiltered `ranked` list (every real cell, any category) is still
always returned for diagnostics -- `SUPPORT_SPACE`/
`COUNTERATTACK_EXPOSURE` cells are never silently discarded, just never
allowed to win the PRIMARY selection. See `HANDOFF.md`'s
"Current-Attack Eligibility Gate" section for the full audit/rationale
and `docs/METRIC_DEFINITIONS.md` for the exact thresholds.

## Honesty constraints

- Never called xG, scoring probability, or danger "guarantee."
- Computed symmetrically for both teams every frame.
- A frame with fewer than 4 total players, or no ball evidence for the
  ball-proximity component, degrades that ONE component to a neutral
  0.5 (documented) rather than fabricating a position -- it never
  invalidates the whole score.
- It is better to report NO primary Current Dangerous Space (honest
  `top=None`) than to force a selection that is not actually eligible.
"""
import math
from dataclasses import dataclass

from tactical_shared.coordinates import DEFAULT_PITCH
from dangerous_space_repositioning.analytics.voronoi_control import (
    voronoi_for_players, opponent_owned_cells, cell_centroid, cell_for_track,
)

PITCH_LENGTH_CM = DEFAULT_PITCH.length_cm
PITCH_WIDTH_CM = DEFAULT_PITCH.width_cm

# Documented severity-component weights -- sum to 1.0.
#
# ROUND: Attacking-Phase Relevance Correction. The OLD weights (kept
# here as a comment for the historical record) were:
#   goal_proximity=0.20, centrality=0.10, ball_proximity=0.10,
#   receiver_support=0.15, coverage_gap=0.35, progression_value=0.10
# `progression_value` -- a WEAK (10%), always-blended attempt at
# directional relevance that never checked real possession -- has been
# REMOVED and replaced by the much stronger, possession-aware
# `direction_relevance` MULTIPLICATIVE gate below (same pattern as
# `area_gate`: a gate scales the whole score, an additive term only
# nudges it). Its freed 0.10 was NOT spread evenly or re-derived from
# scratch -- it was given entirely to the two components that most
# directly answer "how immediately exploitable/attack-relevant is this
# region," to keep the fix targeted and explainable:
#   ball_proximity:   0.10 -> 0.15  (+0.05 -- this project's own
#                      "next-action relevance" proxy: distance-based
#                      immediate reachability from the ball)
#   receiver_support: 0.15 -> 0.20  (+0.05 -- real attacking players
#                      actually near enough to receive there)
# `goal_proximity`, `centrality`, and `coverage_gap` are UNCHANGED --
# they were not implicated in the bug (see HANDOFF.md's audit) and
# retuning them would not be principled, just cosmetic.
#
# `coverage_gap` and `receiver_support` still carry the largest
# combined share (0.55) because they are the components most sensitive
# to real PLAYER positions -- `goal_proximity`/`centrality` depend only
# on the region's fixed (x, y) and the pitch's own geometry. If those
# static components dominated the total, no repositioning could ever
# meaningfully change a region's severity regardless of tactics, which
# would contradict this project's entire premise (that defensive
# structure affects danger). Not fit to any outcome data (none exists
# at this sample size, same disclosed limitation as PSV_proxy in the
# pressing_structure project) -- a disclosed modeling choice, not a
# measured constant.
SEVERITY_WEIGHTS = {
    "goal_proximity": 0.20,
    "centrality": 0.10,
    "ball_proximity": 0.15,
    "receiver_support": 0.20,
    "coverage_gap": 0.35,
}
assert abs(sum(SEVERITY_WEIGHTS.values()) - 1.0) < 1e-9

# Calibrated from this clip's OWN measured spacing (median real
# nearest-TEAMMATE distance ~8m, 90th percentile ~15m -- see
# `docs/METHODOLOGY.md` for the measurement), not a textbook guess:
# "meaningful coverage/reception range" is set a little above the
# typical real spacing between two of a team's own players, i.e. a
# defender/attacker this close is plausibly already influencing the
# space, not literally standing on top of it.
RECEIVER_RADIUS_CM = 2000.0       # ~20m -- "plausibly could receive a pass here"
COVERAGE_RADIUS_CM = 2500.0       # ~25m -- "a defender this close is providing real coverage"
GOAL_PROXIMITY_REF_CM = 4500.0    # ~45m: distance at which goal_proximity has decayed to ~0
BALL_PROXIMITY_REF_CM = 3000.0    # ~30m: distance at which ball_proximity has decayed to ~0
AREA_REF_CM2 = 3_000_000.0        # ~300 m^2 reference cell size for the area gate (see area_gate())
AREA_GATE_MIN = 0.15              # a real but tiny cell is damped, never zeroed

# Current-Attack Eligibility gate constants (see the module docstring's
# "Current-Attack Eligibility" section and `classify_region()` below).
# These are HARD thresholds, not soft-decay references -- deliberately,
# per this round's explicit brief ("a candidate strongly behind the
# current attacking phase must be INELIGIBLE," not merely down-weighted).
CATEGORY_CURRENT_DANGEROUS_SPACE = "CURRENT_DANGEROUS_SPACE"
CATEGORY_SUPPORT_SPACE = "SUPPORT_SPACE"
CATEGORY_COUNTERATTACK_EXPOSURE = "COUNTERATTACK_EXPOSURE"
CATEGORY_UNCERTAIN = "UNCERTAIN"

REASON_UNCERTAIN_CONTEXT = "possession/ball/attacking-direction unknown this frame"
REASON_NO_ELIGIBLE_CANDIDATE = "no candidate satisfies current-attack eligibility"

# ~5m backward tolerance -- the brief's own suggested starting point,
# kept after empirical validation (see HANDOFF.md's "Current-Attack
# Eligibility Gate" section): the real allowed slightly-behind cases in
# this clip's broad audit sample, inspected individually, do look like
# genuine cutback/support pockets (central, near-goal) rather than
# unrelated far-behind exposure -- see
# outputs/qa/current_attack_gate_fix/behind_tolerance_audit.csv and its
# montage. A single tolerance value (rather than a separate "is this a
# plausible cutback shape" sub-rule) was kept deliberately small enough
# that the ranking's own goal_proximity/centrality/receiver_support
# components already do the work of preferring genuine cutback-like
# cells within this narrow band, without a second, harder-to-justify
# heuristic layered on top.
BACKWARD_TOLERANCE_CM = 500.0

# Next-action reachability gate (see `classify_region`): a
# longitudinally-eligible cell must ALSO be plausibly reachable soon,
# via EITHER real proximity to the ball OR a real nearby attacker --
# never a fabricated pass-probability model.
NEXT_ACTION_BALL_DIST_CM = 3000.0          # reuses BALL_PROXIMITY_REF_CM's own touchstone -- ~30m plausible carry/pass reach
NEXT_ACTION_MIN_RECEIVER_SCORE = 0.15      # roughly "a real attacking player within ~15-16m" -- see receiver_support_score's own soft-count math


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _decay(distance_cm: float, ref_cm: float) -> float:
    """Smooth 1 -> 0 falloff, 1.0 at distance=0, ~0.37 at distance=ref,
    ~0 well beyond it. A simple exponential decay -- disclosed as a
    modeling choice (not fit to data), chosen only for its smoothness
    (a hard cutoff would make the counterfactual search's benefit
    landscape discontinuous, which is a genuine incorrectness risk for
    a "does this incremental move help" comparison)."""
    return math.exp(-max(0.0, distance_cm) / max(1.0, ref_cm))


def area_gate(area_cm2: float) -> float:
    return AREA_GATE_MIN + (1.0 - AREA_GATE_MIN) * _clip01(area_cm2 / AREA_REF_CM2)


def goal_proximity_score(defending_team: int, x: float, y: float, pitch=DEFAULT_PITCH) -> float:
    goal_x = pitch.own_goal(defending_team)
    goal_y = pitch.width_cm / 2.0
    d = math.hypot(x - goal_x, y - goal_y)
    return _decay(d, GOAL_PROXIMITY_REF_CM)


def centrality_score(y: float, pitch=DEFAULT_PITCH) -> float:
    """1.0 at the exact centre of the pitch width, decaying toward the
    touchlines -- rewards the central/half-space corridor real coaching
    language calls out, never a hard "is it inside this box" gate."""
    half = pitch.width_cm / 2.0
    dist_from_mid = abs(y - half)
    return _clip01(1.0 - dist_from_mid / half)


def ball_proximity_score(ball, x: float, y: float) -> tuple[float, bool]:
    """Returns (score, had_real_ball_evidence). No observed ball this
    frame -> neutral 0.5, flagged False, never a fabricated ball
    position."""
    if ball is None:
        return 0.5, False
    d = math.hypot(x - ball["x_pitch"], y - ball["y_pitch"])
    return _decay(d, BALL_PROXIMITY_REF_CM), True


def _soft_count(players: list[dict], x: float, y: float, ref_cm: float) -> float:
    """A smooth "effective number of players nearby": each player
    contributes `_decay(distance, ref_cm)` -- 1.0 if right on top of the
    point, decaying continuously to ~0 well beyond `ref_cm`, rather than
    a hard in/out radius count. This matters beyond tidiness: a
    discrete count is a STEP function of position, so a small
    counterfactual move (the bounded +/-100..300cm search this project
    runs) very often crosses zero real thresholds and reports NO change
    at all even when a player genuinely moved closer -- see
    `docs/METHODOLOGY.md` for the specific case this was caught on. The
    real, disclosed number of nearby players used elsewhere (e.g. the
    dashboard's own "why" readout) is still reported by ALSO returning
    the hard count."""
    return sum(_decay(math.hypot(p["x_pitch"] - x, p["y_pitch"] - y), ref_cm) for p in players)


def _hard_count(players: list[dict], x: float, y: float, radius_cm: float) -> int:
    return sum(1 for p in players if math.hypot(p["x_pitch"] - x, p["y_pitch"] - y) <= radius_cm)


def receiver_support_score(x: float, y: float, attacking_team_players: list[dict]) -> tuple[float, int]:
    """Smooth effective count of the attacking team's own players near
    (x,y), normalized by a soft cap of 3 (a 4th+ nearby attacker adds no
    further realistic marginal danger for this proxy). Returns (score,
    raw_hard_count) -- the hard count is kept for the dashboard's own
    "why" readout; the smooth soft-count drives the actual score."""
    soft_n = _soft_count(attacking_team_players, x, y, RECEIVER_RADIUS_CM)
    hard_n = _hard_count(attacking_team_players, x, y, RECEIVER_RADIUS_CM)
    return _clip01(soft_n / 3.0), hard_n


def coverage_gap_score(x: float, y: float, defending_team_players: list[dict]) -> tuple[float, int]:
    """1 - smooth effective count of the DEFENDING team's own players
    near (x,y) -- fewer/farther nearby defenders means a bigger
    coverage gap (more dangerous). Same soft-count reasoning and soft
    cap of 3 as `receiver_support_score`."""
    soft_n = _soft_count(defending_team_players, x, y, COVERAGE_RADIUS_CM)
    hard_n = _hard_count(defending_team_players, x, y, COVERAGE_RADIUS_CM)
    return _clip01(1.0 - soft_n / 3.0), hard_n


@dataclass
class RegionEligibility:
    category: str                        # CATEGORY_CURRENT_DANGEROUS_SPACE / _SUPPORT_SPACE / _COUNTERATTACK_EXPOSURE / _UNCERTAIN
    attack_phase_active: bool | None      # True = defending_team's opponent really has the ball; False = they don't; None = unknown
    progress_cm: float | None             # signed longitudinal progress of this cell vs. the ball (positive = ahead); None if not computable
    next_action_relevant: bool | None     # None when not evaluated (already ineligible on longitudinal grounds, or context unknown)
    eligible: bool                        # True ONLY for CATEGORY_CURRENT_DANGEROUS_SPACE -- the hard gate for primary ranking


def classify_region(defending_team: int, attacking_team_actual: int | None, ball,
                     x: float, y: float, attacking_players: list[dict],
                     pitch=DEFAULT_PITCH) -> RegionEligibility:
    """The Current-Attack Eligibility HARD gate (see the module
    docstring). Unlike a soft multiplicative penalty, an ineligible
    region can NEVER win the primary "Current Dangerous Space" ranking
    regardless of how large its other components are -- eligibility is
    decided BEFORE severity is ever compared across candidates.

    Step order (mirrors HANDOFF.md's documented pipeline exactly):
    1. Possession/ball unknown -> CATEGORY_UNCERTAIN, ineligible. Never
       falls back to an undirected/random selection.
    2. `defending_team`'s own team has the ball (not their opponent) ->
       CATEGORY_COUNTERATTACK_EXPOSURE, ineligible -- there is no
       current attack against `defending_team` at all.
    3. Longitudinal progress `(x - ball_x) * attacking_sign(attacking_team)`
       more than `BACKWARD_TOLERANCE_CM` behind the ball ->
       CATEGORY_SUPPORT_SPACE, ineligible.
    4. Next-action reachability: within the longitudinally-eligible
       band, a cell must ALSO be plausibly reachable soon -- real
       distance to the ball within `NEXT_ACTION_BALL_DIST_CM`, OR a
       real attacking player's `receiver_support_score` at (x,y) at
       least `NEXT_ACTION_MIN_RECEIVER_SCORE`. Failing this ->
       CATEGORY_SUPPORT_SPACE, ineligible (prevents a technically-ahead
       but totally disconnected region, e.g. 40m from any real play,
       from winning).
    5. Otherwise -> CATEGORY_CURRENT_DANGEROUS_SPACE, eligible."""
    attacking_team_hypothesis = 1 - defending_team
    if attacking_team_actual is None or ball is None:
        return RegionEligibility(CATEGORY_UNCERTAIN, None, None, None, False)
    if attacking_team_actual != attacking_team_hypothesis:
        return RegionEligibility(CATEGORY_COUNTERATTACK_EXPOSURE, False, None, None, False)

    progress_cm = (x - ball["x_pitch"]) * pitch.attacking_sign(attacking_team_actual)
    if progress_cm < -BACKWARD_TOLERANCE_CM:
        return RegionEligibility(CATEGORY_SUPPORT_SPACE, True, progress_cm, None, False)

    ball_dist_cm = math.hypot(x - ball["x_pitch"], y - ball["y_pitch"])
    receiver_score, _ = receiver_support_score(x, y, attacking_players)
    next_action_relevant = (ball_dist_cm <= NEXT_ACTION_BALL_DIST_CM) or (receiver_score >= NEXT_ACTION_MIN_RECEIVER_SCORE)
    if not next_action_relevant:
        return RegionEligibility(CATEGORY_SUPPORT_SPACE, True, progress_cm, False, False)

    return RegionEligibility(CATEGORY_CURRENT_DANGEROUS_SPACE, True, progress_cm, True, True)


@dataclass
class DangerScore:
    track_id: object          # the opponent player whose Voronoi cell this is
    x: float
    y: float
    area_cm2: float
    severity: float
    components: dict
    had_ball_evidence: bool


def score_cell(defending_team: int, cell: dict, ball, defending_players: list[dict],
               attacking_players: list[dict], pitch=DEFAULT_PITCH,
               attacking_team_actual: int | None = None) -> DangerScore:
    x, y = cell_centroid(cell)

    g = goal_proximity_score(defending_team, x, y, pitch)
    c = centrality_score(y, pitch)
    b, had_ball = ball_proximity_score(ball, x, y)
    r, n_receivers = receiver_support_score(x, y, attacking_players)
    cov, n_defenders = coverage_gap_score(x, y, defending_players)
    elig = classify_region(defending_team, attacking_team_actual, ball, x, y, attacking_players, pitch)

    # Severity itself is NEVER scaled by eligibility -- eligibility is a
    # HARD PRE-FILTER applied at ranking time (`dangerous_space_for_team`),
    # not a soft down-weighting baked into the score. An eligible cell's
    # severity is exactly this weighted-sum-times-area-gate value; an
    # ineligible cell's severity is still reported honestly (for
    # SUPPORT_SPACE/COUNTERATTACK_EXPOSURE diagnostics) but can never
    # enter the primary ranking regardless of how large it is.
    raw = (SEVERITY_WEIGHTS["goal_proximity"] * g +
           SEVERITY_WEIGHTS["centrality"] * c +
           SEVERITY_WEIGHTS["ball_proximity"] * b +
           SEVERITY_WEIGHTS["receiver_support"] * r +
           SEVERITY_WEIGHTS["coverage_gap"] * cov)
    severity = raw * area_gate(cell["area_cm2"])

    return DangerScore(
        track_id=cell["track_id"], x=x, y=y, area_cm2=cell["area_cm2"], severity=severity,
        components={"goal_proximity": g, "centrality": c, "ball_proximity": b,
                    "receiver_support": r, "n_receivers": n_receivers,
                    "coverage_gap": cov, "n_defenders_nearby": n_defenders,
                    "area_gate": area_gate(cell["area_cm2"]),
                    "category": elig.category,
                    "progress_cm": elig.progress_cm,
                    "next_action_relevant": elig.next_action_relevant,
                    "eligible": elig.eligible,
                    "attack_phase_active": elig.attack_phase_active},
        had_ball_evidence=had_ball,
    )


def dangerous_space_for_team(defending_team: int, team_a_players: list[dict], team_b_players: list[dict],
                              ball, pitch=DEFAULT_PITCH, voronoi_result: dict | None = None,
                              attacking_team_actual: int | None = None) -> dict:
    """Full, honest result for one team, one frame.

    PIPELINE ORDER (matters -- see HANDOFF.md): every opponent-owned
    cell is first SCORED (real geometry, always computed), then
    CLASSIFIED for Current-Attack Eligibility, and ONLY THEN is Dangerous
    Space Severity ranked -- exclusively among `eligible=True` cells.
    Cells are never ranked first and cosmetically hidden afterward.

    Returns:
    - `top`: the highest-severity ELIGIBLE cell (the primary "Current
      Dangerous Space" answer), or `None` if no cell is eligible this
      frame (honest -- see `reason`).
    - `ranked`: EVERY real opponent-owned cell's DangerScore, any
      category, sorted by severity -- never discarded, for
      SUPPORT_SPACE/COUNTERATTACK_EXPOSURE diagnostics.
    - `eligible_ranked`: same list, filtered to `eligible=True` only
      (i.e. `[top] + the rest of the eligible pool`, in ranked order).
    - `reason`: when `top is None`, distinguishes WHY -- structurally
      invalid Voronoi, no opponent-owned cell at all,
      `REASON_UNCERTAIN_CONTEXT` (possession/ball/direction unknown --
      never falls back to an undirected guess), or
      `REASON_NO_ELIGIBLE_CANDIDATE` (context known, but nothing passed
      the eligibility gate this frame).

    `attacking_team_actual`: the best available CAUSAL estimate of which
    team currently has the ball (see `data_loader.attacking_team_at`),
    or `None` if genuinely unknown. Passing `None` is NOT a neutral
    fallback -- it makes every cell `CATEGORY_UNCERTAIN`/ineligible (see
    `classify_region`), matching this round's explicit "no recommendation
    beats a nonsensical one" requirement. Every real dashboard/analytics
    call site in this project passes a real value."""
    if voronoi_result is None:
        voronoi_result = voronoi_for_players(team_a_players, team_b_players)
    if not voronoi_result.get("valid"):
        return {"valid": False, "reason": voronoi_result.get("reason"), "top": None, "ranked": [], "eligible_ranked": []}

    defending_players = team_a_players if defending_team == 0 else team_b_players
    attacking_players = team_b_players if defending_team == 0 else team_a_players

    cells = opponent_owned_cells(voronoi_result, defending_team)
    if not cells:
        return {"valid": True, "reason": "opponent owns no cell this frame", "top": None, "ranked": [], "eligible_ranked": []}

    scored = [score_cell(defending_team, c, ball, defending_players, attacking_players, pitch,
                          attacking_team_actual=attacking_team_actual) for c in cells]
    scored.sort(key=lambda s: s.severity, reverse=True)

    eligible_ranked = [s for s in scored if s.components["eligible"]]
    eligible_ranked.sort(key=lambda s: s.severity, reverse=True)
    top = eligible_ranked[0] if eligible_ranked else None

    if top is not None:
        reason = None
    elif attacking_team_actual is None or ball is None:
        reason = REASON_UNCERTAIN_CONTEXT
    else:
        reason = REASON_NO_ELIGIBLE_CANDIDATE

    return {"valid": True, "reason": reason, "top": top, "ranked": scored, "eligible_ranked": eligible_ranked,
            "attacking_team_actual": attacking_team_actual}


def severity_at_point(defending_team: int, x: float, y: float, area_cm2: float, ball,
                       defending_players: list[dict], attacking_players: list[dict],
                       pitch=DEFAULT_PITCH, attacking_team_actual: int | None = None) -> float:
    """Re-scores an ARBITRARY point (not necessarily a real current
    Voronoi cell) with the identical formula -- used by
    `counterfactual_repositioning.py` to re-evaluate the SAME region
    under a hypothetical player arrangement without re-deriving the
    scoring math a second time.

    NOTE: as of the Current-Attack Eligibility gate (round 2 of the
    Attacking-Phase Relevance Correction), eligibility is a HARD
    ranking-time FILTER, not a severity multiplier -- so this function's
    returned float no longer depends on `attacking_team_actual` at all
    (it only affects `score_cell`'s internal `components["eligible"]`/
    `["category"]`, which this function doesn't surface). The real
    anchoring guarantee lives one level up: `search_repositioning` is
    only ever invoked with a `danger_region` that came from an ALREADY
    ELIGIBLE `top` (§9 of HANDOFF.md's "Attacking-Phase Relevance
    Correction") -- an ineligible region is never handed to the
    counterfactual search in the first place, so it can never be
    "optimized." `attacking_team_actual` is still accepted here purely
    for API consistency with `score_cell`/`dangerous_space_for_team`."""
    fake_cell = {"track_id": None, "polygon": [(x, y)], "area_cm2": area_cm2}
    s = score_cell(defending_team, fake_cell, ball, defending_players, attacking_players, pitch,
                    attacking_team_actual=attacking_team_actual)
    return s.severity
