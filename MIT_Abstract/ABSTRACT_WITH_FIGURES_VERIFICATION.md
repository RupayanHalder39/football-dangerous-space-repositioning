# Verification Report — Abstract With Figures

Companion to `SLOAN_DANGEROUS_SPACE_REPOSITIONING_ABSTRACT_WITH_FIGURES.docx`
/ `.pdf`. This is the current, up-to-date report — it documents the
latest revision (Figure 2 only) at the top, with prior rounds
summarized below for history/traceability.

==================================================
## THIS ROUND: Figure 2 replaced with a 2-panel academic figure
==================================================

**Scope of this round**: Figure 2 only. Figure 1, the abstract body
text, and all project source code were explicitly out of scope and
were not touched.

### New Figure 2 file path

- **New**: `figures/figure2_multipanel_results.png` (2054×855 px)
- **Deleted** (after the new PDF/DOCX were generated and verified):
  `figures/figure2_eligibility_gate_correction.png` (the old
  single-panel grouped-bar chart from the previous round).

### What it shows and the exact numbers used

A clean 2-panel matplotlib figure, white background, restrained colors
(gray/blue/orange), no dashboard chrome, no gradients:

**Panel A — Attack-Gate Selection Quality, Before vs. After** (grouped
bar chart, soft gate vs. hard eligibility gate):
- Ahead / level: 53.3% → 64.4%
- Slightly behind (within tolerance): 41.9% → 35.6%
- Strongly behind (behind live attack): 4.8% → 0.0%

**Panel B — Eligibility Resolution Breakdown** (100%-stacked horizontal
bar, 475-frame sample):
- Eligible primary danger resolved: 21.9%
- Possession / ball uncertain: 64.8%
- Known context, no eligible candidate: 13.3%
(sums to 100.0%, as expected for an exhaustive breakdown)

**No new numbers were computed for this figure.** Every value is
identical to the previous round's Figure 2 and traces to the same
source: `HANDOFF.md` §6c, "11. Full-clip re-audit (475-frame broad
sample, every 5th frame)" — already independently verified in
`CLAIM_EVIDENCE_TRACEABILITY.md` (Claims 10 and 11). No uncertainty
intervals or significance tests were added or implied, per your
explicit instruction. No source code was read or modified to produce
this chart; it is a pure re-visualization of already-verified numbers.

### Caption used (DOCX/PDF)

> Figure 2. Effect and coverage of the Current-Attack Eligibility gate.
> (A) The hard gate increases ahead/level primary selections from
> 53.3% to 64.4% and eliminates strongly-behind selections from 4.8%
> to 0.0%, compared with the earlier soft-gate version. (B) Across the
> same 475-frame sample, 21.9% of frames resolve an eligible primary
> danger, while 64.8% remain possession/ball uncertain and 13.3% have
> known context but no eligible candidate.

This is your suggested caption, lightly tightened (removed one
redundant clause); no numbers were changed.

### Did the abstract body text change?

**No.** The narrative body is byte-for-byte identical to the previous
round: same 4 paragraphs, same 469-word count, same in-text figure
reference style ("(Figure 2)", not split into "(Figure 2A)"/
"(Figure 2B)", to avoid any body-text rewrite beyond what was strictly
necessary). Only the figure image itself and its caption changed.
Verified word count (recomputed programmatically this round):

```
title=12 para1=93 para2=161 para3=43 para4=160 -> TOTAL=469
```

**469 / 500 words** — unchanged from the previous round, well under the
Sloan limit.

### Page count

**2 pages**, unchanged. Page 1: title block, Track, Paper ID,
"Abstract." heading, paragraph 1, Figure 1 (unchanged: image + headline
stat + caption + disclaimer). Page 2: paragraph 2, paragraph 3, the new
Figure 2 (image + caption), paragraph 4, the open-source-repository
line. Verified by rendering and reading the full PDF directly — no
overflow to a 3rd page, no cramped spacing.

### Is Figure 1 unchanged?

**Yes, byte-for-byte.** `figures/figure1_academic_pitch.png` was not
regenerated, and its embedded headline stat, caption, and disclaimer
text in the DOCX are identical to the previous round's.

### Design notes / why this layout

- **Panel A** uses a grouped bar chart (not a dumbbell/slope plot):
  with only 2 time points per category, a grouped bar makes the
  before/after magnitude immediately readable and keeps exact
  percentage labels attached directly to each bar — a slope plot would
  need the same labels and add little for only 2 series.
- **Panel B** uses a 100%-stacked horizontal bar (one of the two
  part-to-whole options offered) because it makes the message —
  "the system is conservative: it rarely forces an answer" — visually
  immediate: the possession/ball-uncertain segment visibly dominates
  the bar, with the resolved and no-candidate segments as the two
  flanking, smaller shares.
- Panel labels "A" / "B" are placed at the top-left of each panel's own
  title (`loc="left"`), the standard journal-figure convention, rather
  than as separate floating annotations — this avoids the layout bugs
  from an earlier draft of this figure (title text drifting relative to
  its panel when placed via manual `transAxes` coordinates instead of
  `ax.set_title`).
- Font sizes (7.4–9.2 pt in the source figure, rendered at 220 dpi) were
  chosen so that after embedding at the DOCX's ~4.8-inch figure width,
  axis labels, data labels, and legend text all remain clearly legible
  at print resolution — confirmed by direct visual inspection of the
  rendered PDF page.

### Cleanup performed this round

- **Deleted**: `figures/figure2_eligibility_gate_correction.png` — only
  after the new DOCX/PDF were generated, rendered, and visually
  verified to contain the new figure correctly.
- **Deleted**: the temporary matplotlib build script for this figure
  (session scratchpad only, not a project file) and a debug zoom image
  used to inspect it before finalizing.
- **Deleted**: `node_modules/`, `package.json`, `package-lock.json`
  (npm install artifacts needed only to run the DOCX build script) and
  the build script itself (`build_docx_with_figures_v3.js`) — build
  tooling, not a deliverable; the DOCX/PDF it produced are retained.
- **Not touched**: Figure 1, the abstract body text, `ABSTRACT_
  RESEARCH_NOTES.md`, `CLAIM_EVIDENCE_TRACEABILITY.md`,
  `FIGURE_PLAN.md`, `ABSTRACT_REVIEW_CRITIQUE.md`, or any project
  source code under `analytics/`, `dashboard/`, `outputs/`, or
  `tests/` — confirmed via `find ... -newer` mtime check against a
  file untouched since before this round began: no source file changed.

### Visual/structural verification (rendering + reading the PDF directly)

- [x] Figure 2 embedded correctly, full resolution, no broken image
      link or placeholder box.
- [x] Figure 2 reads as an academic result figure: white background,
      simple axes, restrained colors, no dashboard chrome, no
      gradients, no decorative UI.
- [x] Panel A and Panel B are both clearly labeled and legible; every
      percentage in both panels is printed on the figure itself.
- [x] New caption present, correctly formatted (italic, "Figure 2."
      prefix), matching your suggested wording almost verbatim.
- [x] No text clipping anywhere on either page.
- [x] Figure 1 (image, headline stat, caption, disclaimer) unchanged.
- [x] Abstract body word count unchanged (469/500).
- [x] Page count unchanged (2 pages).
- [x] PDF renders correctly end-to-end (verified via direct
      PDF-to-image rendering and reading both pages).
- [x] DOCX converts cleanly via LibreOffice with no conversion errors.
- [x] All Figure 2 numbers cross-checked against
      `CLAIM_EVIDENCE_TRACEABILITY.md` Claims 10–11 — no new claims,
      no invented uncertainty/significance values.
- [x] No project source code modified (verified via file-mtime check).

==================================================
## PRIOR ROUNDS (summary, for history — see file headers below for full detail)
==================================================

- **Round 1** (text-only abstract): established the Sloan-compliant
  labeled-section abstract (`SLOAN_DANGEROUS_SPACE_REPOSITIONING_
  ABSTRACT.md`/`.docx`/`.pdf`), `ABSTRACT_RESEARCH_NOTES.md`,
  `FIGURE_PLAN.md`, `CLAIM_EVIDENCE_TRACEABILITY.md`,
  `ABSTRACT_REVIEW_CRITIQUE.md`.
- **Round 2** (sample-paper-style figures, first pass): reflowed the
  abstract into continuous narrative with 2 embedded figures; Figure 1
  was a cropped dashboard-UI screenshot at that point, Figure 2 was a
  single-panel grouped bar chart.
- **Round 3** (academic Figure 1 + worked-example correction): replaced
  the dashboard-crop Figure 1 with a purpose-built academic pitch
  diagram (players, ball, real Voronoi tessellation lines, the flagged
  region, fixer + repositioning arrow). Also discovered, during
  re-verification, that the abstract's previously-cited worked example
  (frame 3300, benefit +0.00544) was **non-reproducible** under current
  source, and replaced it throughout the project (abstract text, both
  DOCX/PDF pairs, `ABSTRACT_RESEARCH_NOTES.md`, `FIGURE_PLAN.md`,
  `CLAIM_EVIDENCE_TRACEABILITY.md` Claim 14) with a freshly re-verified
  example (frame 2233, benefit +0.01326) — full computation trail in
  `CLAIM_EVIDENCE_TRACEABILITY.md`. This was a scientific-integrity
  correction, not a style change.
- **Round 4 (this round)**: Figure 2 only, as detailed above.

## Is the project still ready for the 120-second video step?

**Yes, unaffected.** This round touched only
`dangerous_space_repositioning/MIT_Abstract/figures/
figure2_multipanel_results.png` and the two `SLOAN_DANGEROUS_SPACE_
REPOSITIONING_ABSTRACT_WITH_FIGURES.*` output files. Zero changes to
`analytics/`, `dashboard/`, `outputs/`, or `tests/`. The
`pressing_structure`/`offside_break` project areas were not touched.

## Caveats (carried over, still open)

1. **GitHub repository link is still a placeholder** — unresolved
   action item before actual submission, unchanged across all rounds.
2. Figure 2's Panel A intentionally shows only the 3 verified categories
   from the 475-frame sample (no additional category exists in project
   documentation to add), and Panel B intentionally shows no
   uncertainty bands or error bars, per your explicit "do not invent"
   instruction.
