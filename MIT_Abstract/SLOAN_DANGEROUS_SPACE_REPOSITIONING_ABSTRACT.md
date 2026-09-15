**Track: Soccer**

## Closing the Gap: Attack-Gated Space Control and Bounded Counterfactual Repositioning in Soccer

### Introduction

Coaches routinely ask which player should step into open space before an opponent exploits it, but this call is usually made on intuition, not measurement. Existing pitch-control and Voronoi models flag "dangerous" space geometrically, without checking whether the current attack can reach it, and rarely recommend a fix while checking whether that fix opens a new gap. We ask: can attack-relevant dangerous space be identified from tracking data, and can a bounded counterfactual search recommend which defender or midfielder should reposition to close it without creating a new structural gap?

### Methods

Using 120 seconds (3,600 frames, 30 fps) of player/ball tracking from a broadcast match, we compute a Voronoi tessellation per frame and score each opponent-owned cell as an area-gated weighted sum of five components (goal proximity 0.20, centrality 0.10, ball proximity 0.15, receiver support 0.20, coverage gap 0.35). A causal, tiered majority-vote estimator (current frame, then 4s/12s/30s windows) determines the attacking team. A hard eligibility gate restricts candidates to cells within 5m of the ball's longitudinal progress, or reachable within 30m or a 0.15 receiver-support threshold, excluding cells behind the live attack or arising when the defending team holds the ball. Up to three mutually distinct eligible regions per team are kept via centroid/radius de-duplication. Each region's fixer candidate is scored on proximity, feasibility, abandonment cost, and local support; a bounded (≤3m) local search then evaluates repositions against a benefit function trading danger removed against new-gap risk (a spatial-balance regression), structural damage, and movement cost.

### Results

Across a 475-frame sample, the eligibility gate eliminates strongly-behind-the-attack selections entirely (0% vs. 4.8% under an earlier soft-gate version), while ahead-of-ball/level selections rise from 53.3% to 64.4%; 21.9% of frames resolve an eligible primary danger, 64.8% are honestly reported possession-uncertain, and 13.3% have known context but no eligible candidate. In a 601-frame demo segment, 48 frames resolve a primary region: 21 (44%) contain three distinct dangerous regions, 23 (48%) contain two, and 4 (8%) contain one, with de-duplication merging overlapping candidates in 47 of 48 cases. Same-player fixer conflicts across two ranked regions arise in 4 of 48 frames, always resolved by reassigning the next-best real candidate. One verified positive-benefit case (a 3.0m move) reduces flagged-region severity by 0.00775 with zero new-gap penalty (net benefit +0.01326); most frames, however, report no improving bounded candidate, since the nearest real defender is often 20-40m from the flagged region.

### Conclusion

The system turns "where is the danger, and who should close it" into a reproducible, frame-level answer: it ranks up to three attack-relevant dangerous regions per team, assigns a non-duplicated fixer to each, and screens candidate moves for new gaps — supporting opposition scouting, training-ground rehearsal of defensive shape, and post-match review. It does not claim globally optimal repositioning, validated scoring probability, or a proven outcome effect: the bounded single-player search, one-match sample, and unvalidated severity/access proxies mean this is coach-facing decision support, not automated tactical truth, pending multi-match validation.

---

Word count: 494 words including title, excluding the 4 section-header words ("Introduction"/"Methods"/"Results"/"Conclusion"); 498 words if those headers are counted. Both figures are under the 500-word hard maximum and within the requested 490–495 target. See `ABSTRACT_RESEARCH_NOTES.md` for the exact counting method. This line, the horizontal rule above it, and the "Track: Soccer" line at the top are outside the counted abstract body (track is a submission-portal metadata field, not abstract prose).
