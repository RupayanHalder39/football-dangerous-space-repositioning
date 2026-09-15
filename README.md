# Football Dangerous Space Repositioning

A football tracking-data research prototype that identifies **attack-relevant dangerous space**, assigns the defender or midfielder best positioned to respond, and evaluates bounded player repositioning while explicitly checking whether the movement creates a new structural gap elsewhere.

## Coaching Question

> **Which player should move, and where should they move, to close dangerous space without opening another gap?**

This project combines spatial control, attack-phase relevance, player-responsibility scoring, and bounded counterfactual repositioning.

---

## Why This Matters

Traditional pitch-control or Voronoi visualisations can show where open space exists.

But a coach usually needs a much more actionable answer:

- Which open space is actually dangerous **right now**?
- Which player should respond?
- Where should that player move?
- Will that movement solve the problem?
- Will moving that player create another structural weakness elsewhere?

This project was designed to answer those questions.

---

## What the System Does

```text
Broadcast Match Video
        ↓
Player + Ball Tracking
        ↓
Possession / Attacking-Team Context
        ↓
Voronoi Spatial Control
        ↓
Dangerous-Space Severity
        ↓
Current-Attack Eligibility Gate
        ↓
Top Ranked Distinct Dangerous Regions
        ↓
Opponent Accessibility
        ↓
Candidate Fixer Assignment
        ↓
Bounded Counterfactual Repositioning
        ↓
New-Gap / Structural-Risk Check
        ↓
Coach-Facing Recommendation
```

---

## Dangerous Space Severity

Each opponent-controlled Voronoi region is scored using a weighted combination of:

```text
Goal proximity      0.20
Centrality          0.10
Ball proximity      0.15
Receiver support    0.20
Coverage gap        0.35
```

The resulting weighted score is multiplied by an area gate.

The severity score is bounded to `[0, 1]`.

---

## Current-Attack Eligibility Gate

A major part of this project is separating:

> **geometrically open space**

from:

> **space that actually matters to the current attacking phase**

A hard eligibility gate rejects regions when:

- possession / attacking direction cannot be resolved
- the defending team itself has possession
- the region lies more than approximately 5 metres behind the ball's attacking progress
- the region is not plausibly relevant to the next attacking action

This prevents the system from ranking visually open regions that are not realistically part of the current attack.

---

## Top Dangerous Regions

The system can retain up to **three spatially distinct dangerous regions**.

Candidate regions are ranked by severity and spatially de-duplicated so that nearby overlapping regions are not presented as separate tactical problems.

This produces:

- Danger #1 — highest priority
- Danger #2 — secondary priority
- Danger #3 — tertiary priority

where sufficient distinct evidence exists.

---

## Candidate Fixer Assignment

For each dangerous region, defending players are ranked using factors including:

- proximity
- movement feasibility
- abandonment cost
- local defensive support

If the same player is the natural best candidate for multiple dangerous regions:

- the higher-priority region keeps the player
- lower-priority regions fall back to the next-best valid defender

This avoids assigning the same player to solve two different tactical problems simultaneously.

---

## Counterfactual Repositioning

For each assigned fixer, the system evaluates small hypothetical alternative positions.

The bounded local search tests movements of up to approximately **3 metres**.

The benefit function considers:

```text
+ danger removed
- new-gap penalty
- structural-damage penalty
- movement-cost penalty
```

The purpose is not to claim a globally optimal position.

Instead, the system asks:

> **Is there a nearby position that improves this defensive situation without making the team's overall structure worse?**

---

## New-Gap / Spatial-Balance Risk

Every candidate movement is checked against the defending team's own structure.

The structural-risk model considers:

```text
Compactness risk         0.40
Isolation risk           0.35
Coverage variance risk   0.25
```

This directly addresses the second half of the coaching question:

> **Does closing this space create another problem somewhere else?**

---

## Opponent Accessibility

The system also estimates how realistically the attacking team can access a region using a time-to-reach based spatial model.

The purpose is to distinguish:

- open but difficult-to-use space
- open and realistically exploitable space

---

## Verified Results

### Current-Attack Eligibility Validation

Across a broad 475-frame validation sample:

- ahead / level primary selections increased from **53.3% to 64.4%**
- strongly-behind-the-attack selections decreased from **4.8% to 0.0%**
- **21.9%** of frames resolved an eligible primary danger
- **64.8%** were reported as possession / ball uncertain
- **13.3%** had known context but no eligible candidate

The system therefore deliberately abstains when the tactical context is not strong enough.

### Multi-Region Validation

Within a 601-frame demo segment, 48 frames resolved a primary dangerous region.

Of those:

- **21 frames** contained 3 distinct dangerous regions
- **23 frames** contained 2
- **4 frames** contained 1

Spatial de-duplication suppressed at least one overlapping raw candidate in **47 of 48** resolved frames.

### Fixer Conflicts

Same-player fixer conflicts occurred in **4 of 48** resolved frames.

In all four observed cases, the system successfully reassigned the lower-priority region to the next-best real candidate.

---

## Verified Counterfactual Example

An exhaustive read-only scan of the full match found only a small number of genuinely improving bounded repositioning cases.

One verified example used in the research abstract produced:

```text
Movement distance: 3.0 m
Danger reduction: 0.00775
New-gap penalty: 0.0
Net modeled benefit: +0.01326
```

This is presented as:

> **a candidate improvement within the tested local search**

and not as a globally optimal tactical solution.

An important finding is that most dangerous situations cannot be repaired simply by moving one nearby player by three metres.

That is useful tactically because it helps distinguish:

- local positioning errors

from:

- larger team-structure problems

---

## Coach-Facing Outputs

The system can visualise:

- Voronoi spatial control
- attack-relevant dangerous regions
- ranked Danger #1 / #2 / #3 regions
- assigned fixer for each region
- candidate movement arrows
- opponent accessibility
- dangerous-space severity
- spatial-balance / new-gap risk

Potential uses include:

- post-match review
- opposition analysis
- defensive-shape training
- tactical rehearsal

---

## Repository Structure

```text
analytics/
├── data_loader.py
├── voronoi_control.py
├── dangerous_space.py
├── multi_region.py
├── opponent_access.py
├── player_responsibility.py
├── counterfactual_repositioning.py
├── spatial_balance.py
└── coach_signals.py

dashboard/
├── live_graphs.py
├── voronoi_broadcast_overlay.py
├── voronoi_radar.py
├── display_stability.py
└── render_dangerous_space_dashboard.py

docs/
├── METHODOLOGY.md
├── METRIC_DEFINITIONS.md
├── REPOSITIONING_LOGIC.md
├── DISPLAY_STABILITY.md
└── FINAL_DASHBOARD_NOTES.md

tests/
└── tactical analytics and no-future-leakage tests

outputs/
├── validation outputs
├── QA figures
├── tactical previews
└── final visualisations
```

---

## Tech Stack

- Python
- NumPy
- Pandas
- OpenCV
- Matplotlib
- Voronoi geometry
- player / ball tracking
- spatial-temporal analysis
- bounded counterfactual search

---

## Research Principles

This project follows strict scientific and tactical wording rules:

- Voronoi is treated as a spatial-analysis primitive, not the research contribution itself
- attack relevance is separated from geometric severity
- uncertainty is explicitly reported
- counterfactual search is bounded
- no global-optimum claim
- no scoring-probability claim
- no proven causal match-outcome claim
- no-future-leakage principles are enforced in frame-level analysis

---

## Limitations

Current limitations include:

- one short match sample
- broadcast-video tracking noise
- unvalidated severity / accessibility proxies
- bounded single-player local search
- no multi-match tactical validation yet

The system should therefore be viewed as:

> **coach-facing decision support, not automated tactical truth**

---

## Future Work

Potential extensions include:

- multi-match validation
- expert-coach annotation
- richer opponent-access models
- multi-player counterfactual repositioning
- event-data integration
- longer-horizon defensive-shape optimisation
- opponent-specific tactical recommendations
- identifying whether a dangerous space requires a local fix or complete structural reorganisation

---

## Research Context

> **AI-Driven Tactical Intelligence in Football**

The research aims to convert raw tracking and video data into explainable tactical recommendations for coaches and analysts.

---

## Author

**Rupayan Halder**  
Ph.D. Researcher — AI-Driven Tactical Intelligence in Football  
Jadavpur University  

Football Analytics Research Collaborator  

GitHub: [RupayanHalder39](https://github.com/RupayanHalder39)
