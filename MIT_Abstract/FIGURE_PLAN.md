# Figure Plan — Dangerous Space Repositioning (MIT Sloan SSAC Abstract)

Per `sloan_abstract_writing_guide.md`: **up to 2 tables/figures combined**
for the Phase 1 abstract. This plan uses exactly 2 — one figure, one
table — chosen because together they cover both required things a
judge needs to see in 30 seconds: (1) that the method's output is a
real, legible tactical recommendation on real tracking data, and (2)
that the paper's central quantitative claim (the eligibility gate
actually changes selection quality, not just adds a filter in name) is
directly visible as a number, not asserted in prose alone.

Neither is chosen for visual appeal. A full 4-panel dashboard
screenshot (Match Feed + Radar + all 3 graphs + status badges) was
explicitly considered and **rejected** — it is a product/engineering
artifact (spotlight, LIVE tag, panel chrome) that would read as a demo,
not evidence, and would bury the one thing worth showing a reviewer
inside UI clutter the abstract itself never mentions.

## Figure 1 (image): the method's output on a real frame

**What it shows**: a single real broadcast frame (from
`ExternalDownlaodVideo/testVideo1_120s.mp4`) with ONLY the
research-relevant overlay — the real per-frame Voronoi tessellation,
the Top-3 ranked attack-relevant dangerous regions (color/opacity
coded by rank), the assigned fixer for the primary region, and the
bounded candidate move (arrow to the target position). No dashboard
chrome (no status badge, no LIVE tag, no spotlight glow, no graph
panels, no radar duplicate view).

**Why this frame**: frame 1700 (t=56.7s) — independently verified
during final project QA as a genuine 3-distinct-region instance with a
correctly-resolved primary fixer, OUTSIDE the frame range used for any
of the paper's quantitative claims (which draw from the 440-1040
demo segment and the 475-frame broad sample) — so the figure is a
different, independently-representative instance, not the same frame
the numbers in Results are computed from.

**Source**: re-crop/re-render from
`dangerous_space_repositioning/dashboard/render_dangerous_space_dashboard.py`'s
own `render_frame()` at frame 1700, extracting only the Tactical Match
Feed panel's own pixel region (top-left quadrant) and cropping out the
status badge — OR a fresh, minimal-chrome render written specifically
for the paper (recommended, so the figure never implies the abstract
is describing a shipped product UI). **Not yet generated** — to be
built when the full paper (not just this Phase-1 abstract, which does
not require the figure file itself, only the plan) is drafted.

**What it supports**: the Methods claim that the pipeline outputs a
ranked, non-duplicated set of regions with an assigned fixer and a
bounded candidate move — makes the abstract's central mechanism
inspectable, not just described.

## Figure 2 (table): eligibility-gate correction, before vs. after

**What it shows**: the exact 3-row table already computed and verified
in `HANDOFF.md` §6c ("11. Full-clip re-audit"), reproduced verbatim:

| | Round 1 (soft gate) | Round 2 (hard gate) |
|---|---|---|
| Ahead/level | 53.3% | 64.4% |
| Slightly behind (within tolerance) | 41.9% | 35.6% |
| **Strongly behind** | 4.8% | **0.0%** |

Sample: 475 frames (every 5th frame of the match, ≥4 tracked players),
104 of which resolved to an eligible primary danger under the
hard-gate version — see `outputs/qa/current_attack_gate_fix/
candidate_eligibility_validation.csv` for the row-level data this table
is aggregated from.

**Why this table over a chart**: the claim is precise (three
percentages, one of which is a "0% by construction" structural
guarantee) — a table states this exactly; a bar chart would spend the
same visual budget showing less precision for a 3-category comparison
this small.

**Why this table over alternative Results candidates considered**:
- *Top-3 region-count distribution (4/23/21 frames)* — a real, verified
  number, but it demonstrates a design property (de-duplication works),
  not the paper's central research claim (attack-relevance gating
  changes what gets selected as dangerous at all). Kept as a Results
  sentence instead of a figure.
- *The single worked positive-benefit example* — originally frame 3300
  (later found, in the figures-revision round, to be non-reproducible
  under current source and replaced with frame 2233; see
  `CLAIM_EVIDENCE_TRACEABILITY.md` Claim 14 and
  `ABSTRACT_WITH_FIGURES_VERIFICATION.md`) — a real, verified number,
  but at the time this plan was written, ONE example seemed better
  stated as a sentence with exact figures than as a table with only one
  row. (Superseded: the figures-revision round's academic Figure 1
  *does* visualize this exact worked example directly — see that
  round's verification report for the updated rationale.)
- *A reduction-in-display-flicker / UI-stability metric* — explicitly
  excluded per this task's own instruction: engineering QA, not a
  research result.

**What it supports**: the Results claim that the hard eligibility gate
is a real behavioral correction with a measured before/after effect,
not merely a described design decision.

## What is NOT a figure

Per this task's own instruction, no figure was built purely because it
"looks good." Two additional candidates were considered and dropped:

- A full dashboard screenshot (Match Feed + Radar + Graphs 1/2/3) —
  dropped: mixes UI/engineering elements (LIVE tag, spotlight, panel
  titles) into what should read as a research figure; also would use
  the abstract's entire 2-visual budget on one item.
- A bucketed-bar graph screenshot (Graph 1 or Graph 2) — dropped: these
  visualize a display-layer aggregation (bucket means for a rolling
  coach-facing window), not a claim made anywhere in the abstract text
  itself; including it would introduce a visual the reader has no
  prose anchor for.
