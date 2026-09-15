# Title Selection + Reviewer-Style Critique

## Title candidates (5, generated before writing the abstract body)

1. **"Closing the Gap: Attack-Gated Space Control and Bounded
   Counterfactual Repositioning in Soccer"** (12 words)
2. "Fix Without Breaking: Bounded Counterfactual Repositioning for
   Dangerous Space in Soccer" (12 words)
3. "Which Defender Should Move? Attack-Relevant Dangerous-Space
   Detection and Counterfactual Repositioning" (11 words)
4. "Right Space, Right Time: Attack-Phase-Gated Danger Detection and
   Counterfactual Repositioning in Soccer" (13 words)
5. "One Gap Closed, Another Checked: Counterfactual Defensive
   Repositioning from Tracking Data" (12 words)

**Style calibration** (from `sloan_past_winners_reference.md`): the
confirmed/finalist soccer titles all follow "[short, memorable
phrase]: [precise description naming the mechanism]" — e.g. "Wide Open
Gazes: Quantifying Visual Exploratory Behavior in Soccer with Pose
Enhanced Positional Data," "Valuing La Pausa: Quantifying Optimal Pass
Timing Beyond Speed." None of the confirmed winners use a question-mark
title as their PRIMARY hook (the 2025 winner's title is a question, but
it's the exception, not the pattern, and it's followed by a long,
explicit method clause after it). All 5 candidates were built to this
two-part pattern.

**Chosen: #1.** Reasoning:
- "Closing the Gap" is the coaching-language hook (matches the user's
  own suggested direction almost exactly) and reads as a real tactical
  phrase, not marketing language.
- "Attack-Gated Space Control" names the paper's actual first
  contribution (the hard eligibility gate) using a term a soccer-
  analytics reviewer will parse correctly, without saying "Voronoi" as
  if the tessellation itself were the novelty — directly satisfying
  this task's own instruction ("Voronoi is a tool, not the contribution
  by itself").
- "Bounded Counterfactual Repositioning" names the second contribution
  and signals a defensible, named method (matching the winners'
  pattern of naming an actual technique, not "we analyzed player
  positions").
- "in Soccer" states the track directly in the title, which several
  past finalists also do explicitly.
- #2 was close but "Fix Without Breaking" undersells the attack-
  relevance gating (arguably the stronger of the two contributions,
  since it is the one with a clean before/after number). #3's question
  format reads more like a blog headline than the two winners' own
  titles. #4's "Right Space, Right Time" is catchy but vaguer about the
  mechanism than #1. #5 leads with the new-gap check, which is real but
  secondary to the eligibility gate as the paper's strongest empirical
  claim (0% vs. 4.8%).

## Reviewer-style critique (performed before finalizing; one revision pass applied)

**Is the research question immediately clear?**
Yes — Introduction ends with an explicit, two-part, falsifiable
question. First-pass draft buried this after too much throat-clearing
about existing pitch-control work; revised to keep the existing-work
critique to one sentence before stating the question.

**Is Voronoi used as a tool rather than sold as novelty?**
Yes. Methods opens with "we compute a Voronoi tessellation" as step one
of a longer pipeline and never returns to it as a claimed contribution.
The word "Voronoi" appears exactly twice in the whole abstract (once in
Introduction describing EXISTING work, once in Methods as one step) —
checked directly by re-reading the final text.

**Are methods concrete enough?**
Yes — every threshold named has a unit and a value (5m, 30m, 0.15,
<=3m, 0.20/0.10/0.15/0.20/0.35). This is denser than the "name your
method" bar the past-winners reference sets (e.g. "polynomial
regression + gradient boosting" — a method NAME with no parameters).
We go further by giving the actual weights, which a reviewer can spot-
check against the (to-be-linked) GitHub repo.

**Are results numerical enough?**
Yes — every sentence in Results carries a specific number; no sentence
says only "we found a relationship" or "the gate improves selection
quality" without also giving the before/after percentages.

**Are claims defensible?**
Yes, per `CLAIM_EVIDENCE_TRACEABILITY.md` — every number traces to a
specific file/section, cross-checked against current source code (not
just the first matching HANDOFF.md passage, which mattered: one
formula section there was stale, see that file's Claim 3).

**Does it answer "so what for coaches"?**
Yes — Conclusion names three concrete uses (opposition scouting,
training-ground rehearsal, post-match review) rather than one vague
"could help coaches" line.

**Is the limitation honest?**
Yes, and specific: names THREE distinct limitations in one sentence
(bounded single-player search, one-match sample, unvalidated proxies)
rather than a single generic hedge, and explicitly states the current
system is "decision support... not automated tactical truth."

**Does it sound like Sloan rather than a software demo?**
Yes — checked explicitly for leakage of engineering/UI language
(spotlight, radar, LIVE tag, dashboard, panel, graph) — NONE appear in
the abstract text. First draft was already clean on this front because
Methods/Results were written directly from the analytics layer's own
verified numbers, never from the dashboard/rendering layer.

**Would a reviewer understand why this differs from generic pitch-control
analysis?**
This is the one place a reviewer could reasonably push back, and the
weakest link in the abstract as written: the distinction ("most models
flag geometric exposure regardless of the current attacking phase; we
gate on it, with a measured effect") is stated once, compactly, in the
Introduction's second sentence and reinforced by the Results' first
number (0% vs. 4.8%). A reviewer skimming quickly could still miss it
if they don't connect "eligibility gate" back to that Introduction
sentence. **Revision made**: Results was reworded to open with "the
eligibility gate eliminates strongly-behind-the-attack selections
entirely" (naming the mechanism again) rather than a bare percentage,
so the Introduction's claim and the Results' evidence are linked by a
repeated, exact phrase ("eligibility gate") a skimming reviewer can
pattern-match on.

## One revision applied after this critique

Original Results opening (pre-critique) led with the bare statistic:
*"0% vs. 4.8% strongly-behind-the-attack selections..."* — technically
correct but required the reader to already remember what "strongly-
behind-the-attack" referred to from three sentences of Introduction
earlier. Revised to open by re-naming the mechanism ("the eligibility
gate eliminates...") before the number, at a cost of a few words,
recovered from Methods by tightening phrasing elsewhere (see the
word-count trimming pass, which needed a matching cut regardless to
land in the 490-495 target).

## Compliance checklist (against `sloan_abstract_writing_guide.md`)

- [x] Word count <=500 (title included) — 494/498 depending on whether
      section-header words are counted; both under the hard limit.
- [x] All 4 sections present and clearly labeled (Introduction,
      Methods, Results, Conclusion).
- [x] Track selected: Soccer (stated explicitly at the top).
- [x] Concrete numbers in Results (11 distinct numeric claims).
- [x] Named method in Methods (Voronoi tessellation, hard eligibility
      gate, bounded local counterfactual search, spatial-balance
      regression for new-gap risk).
- [ ] **GitHub repo — NOT YET SATISFIED.** The guide requires a public,
      anonymized GitHub repo link before submission. This project
      currently lives only in this local working directory
      (`/Users/rupayan/RupayanPHD/Problem1_2Papers/
      dangerous_space_repositioning/`) with no confirmed public repo.
      **Action item, not resolved by this task**: a public (or
      anonymized-for-review) GitHub repo must be created and linked
      before the actual Sloan submission — flagged explicitly in the
      final report rather than silently assumed or fabricated.
- [x] One honest limitation in Conclusion (three, actually: bounded
      single-player search, one-match sample, unvalidated proxies).
- [x] No more than 2 tables/figures total (exactly 2 planned: 1 figure,
      1 table — see `FIGURE_PLAN.md`; neither has been generated as an
      image file yet, since this task's own scope was the abstract
      TEXT and the figure PLAN, not final camera-ready assets).
- [x] Title is specific, names the mechanism, avoids a generic label.
