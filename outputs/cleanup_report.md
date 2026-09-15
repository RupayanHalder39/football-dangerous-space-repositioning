# Cleanup Report — `dangerous_space_repositioning/outputs/`

Performed only after: the grouped-region-bar graph redesign was
implemented, previews/contact sheet/comparisons were visually verified,
the 20-second demo clip passed QA (smooth bucket-to-bucket evolution,
no flicker, no rank-swap, colors consistent), and all tests passed. See
`HANDOFF.md` §16/§17 for the full round writeup.

Full per-file reasoning and sizes: `outputs/cleanup_manifest_before_delete.txt`
(written and reviewed BEFORE any deletion, per the round's own safety
process).

## Files deleted: 17

| Group | Count | Bytes freed |
|---|---|---|
| Obsolete duplicate 20-second demo clips (5 older rounds' renders) | 6 | 298,176,185 |
| Obsolete 30s-vs-16s / 16s-vs-20s graph-window comparison PNGs | 8 | 4,871,181 |
| Obsolete graph chart-type comparison PNGs (line vs. stacked; 20s-vs-24s line-chart) | 3 | 1,465,536 |
| **Total** | **17** | **304,512,902 bytes (290.41 MB)** |

`outputs/` measured 331 MB before cleanup, 79 MB after (`du -sh`,
block-size-rounded — the exact byte-sum above is the precise figure).

## Documentation updated BEFORE deletion (not after)

Every deleted file that was still cited by path in `HANDOFF.md` or
`docs/` was updated to note its removal and point to the current
retained successor, per the round's own safety process ("if a file is
still referenced, either keep it or update the documentation... BEFORE
deletion"):

- `HANDOFF.md` §10 ("Preview & contact sheet paths") — `compare_*.png`,
  `compare16v20_*.png`, and the old
  `outputs/qa/dangerous_space_repositioning_20s_demo.mp4` path all
  marked removed, with the current demo clip's path given.
- `HANDOFF.md` §14g, §15j, §16g — each round's own now-deleted demo
  clip / comparison image reference struck through and annotated with
  its successor.
- `docs/DISPLAY_STABILITY.md` (QA section) — its own now-deleted demo
  clip reference annotated the same way.

Files that were still referenced and did NOT need a documentation
change (kept as-is, untouched): `outputs/previews/*.png`,
`outputs/contact_sheet/contact_sheet.png`,
`outputs/qa/current_attack_gate_fix/candidate_eligibility_validation.csv`,
`outputs/qa/current_attack_gate_fix/behind_tolerance_audit.csv`,
`outputs/qa/attack_relevance_fix/validation_broad_sample.csv`,
`outputs/qa/attack_relevance_fix/old_vs_new_t34p7.png`,
`outputs/qa/multi_region_24s_window/multi_region_qa_log.csv`,
`outputs/qa/display_stability_old_vs_new_contact_sheet.png`,
`outputs/qa/graph2_alpha_comparison.png`.

## Files deliberately RETAINED (not deleted, and not merely "not yet
gotten to")

1. **Current final preview set**: `outputs/previews/01-06_*.png` (6 files) —
   **later regenerated again** under the final round's own polish (§ADDENDUM below).
2. **Current final contact sheet**: `outputs/contact_sheet/contact_sheet.png` —
   **later regenerated again** under the final round's own polish.
3. ~~**Current corrected 20-second demo video**:
   `outputs/qa/grouped_region_bars_redesign/dangerous_space_repositioning_20s_demo.mp4`~~
   — **superseded and removed in the final round's own cleanup addendum**
   below; the truly final 20s clip is
   `outputs/final_demo/dangerous_space_repositioning_20s_final.mp4`.
4. **Grouped-bar comparison images** (RETAINED — useful design-decision
   documentation): `outputs/qa/grouped_region_bars_redesign/
   graph1_stacked_vs_grouped_comparison.png` and `graph2_tick_vs_grouped_comparison.png`.
5. **This report** and the manifest that preceded it.
6. **Validation CSVs still referenced by docs** (see list above) —
   `candidate_eligibility_validation.csv`, `behind_tolerance_audit.csv`,
   `validation_broad_sample.csv`, `multi_region_qa_log.csv`.
7. **Current source code** — nothing under `dangerous_space_repositioning/
   analytics/`, `dashboard/`, or elsewhere was touched by this cleanup.
8. **Tests** — `dangerous_space_repositioning/tests/` untouched.
9. **`HANDOFF.md`** — updated (references only), never deleted.
10. **Documentation** (`docs/*.md`) — updated where a deleted file was
    referenced (`DISPLAY_STABILITY.md` only); otherwise untouched.
11. **Every artifact HANDOFF.md's own deliverables lists still name as
    current** — cross-checked against §14g/§15j/§16g/§17 before
    deleting anything (see the manifest for the exact grep-verified
    reference check).

### Deliberately NOT scanned this round (disclosed, not an oversight)

`outputs/qa/attack_relevance_fix/` and `outputs/qa/current_attack_gate_fix/`
each still contain several smaller, round-specific validation artifacts
(helper scripts, markdown reports, montage/contact-sheet images, and a
handful of case-illustration PNGs) beyond the specific files directly
cited by path in the docs. A full per-file audit of every one of these
was intentionally left out of this pass — the much larger, safer win
in the 6 duplicate demo-clip videos and the obsolete graph-comparison
images was taken instead, rather than risk removing something from
those two folders that still carries standalone validation value
without a more careful review. Nothing in either folder was deleted,
moved, or modified.

## Structure note: `outputs/final_demo/` and `outputs/graphs/` (superseded by the final round)

At the time of THIS section's original writing, `outputs/final_demo/`
was still empty and reserved for the eventual 120-second full video,
so the 20-second demo clip was deliberately kept in its own
`outputs/qa/<round-name>/` location instead of moving it there
prematurely. **The final round has since rendered the 120-second
video**, so `outputs/final_demo/` now correctly holds: the 120-second
final video, the final 20-second QA clip (re-rendered under the same
final design), the 13-checkpoint + 4-scenario QA frames, and the final
120s QA contact sheet — see the ADDENDUM below for the complete,
current list. `outputs/graphs/` remains empty (still reserved for
standalone, non-dashboard-embedded graph exports — never populated by
name in any round).

## ADDENDUM — Final round (presentation polish + full 120s render)

Performed only after: the D1-width/LIVE-tag/y-axis-audit graph polish
was implemented and visually verified in the 6 standard previews, the
re-rendered 20-second clip passed both programmatic QA (601 frames,
30fps, 2304x1204, 20.03s) and visual QA at every required checkpoint,
the full 120-second video was rendered and passed its own programmatic
QA (3600 frames, 30fps, 2304x1204, 120.00s, 233.28 MB, decodes cleanly,
36 frames sampled every 100th all non-blank) and visual QA (13 timeline
checkpoints + 4 scenario examples, all confirmed correct), and all
tests passed. See `HANDOFF.md` §18/§19 for the full round writeup.

One additional file deleted this round (full detail in
`cleanup_manifest_before_delete.txt`'s own addendum):

| File | Bytes freed |
|---|---|
| `outputs/qa/grouped_region_bars_redesign/dangerous_space_repositioning_20s_demo.mp4` (the immediately-prior round's own 20s clip, before this round's final polish) | 41,536,340 |

**Documentation updated BEFORE this deletion**: every "CURRENT demo
clip lives at `outputs/qa/grouped_region_bars_redesign/...`" pointer
left over from earlier rounds (`HANDOFF.md` §10, §14g, §15j, §16g, and
`docs/DISPLAY_STABILITY.md`'s own QA section) was updated to point at
the new, truly final `outputs/final_demo/dangerous_space_repositioning_20s_final.mp4`
instead, each annotated to note that this intermediate file was itself
later superseded.

**Combined cleanup total across both rounds**: 18 files deleted,
346,049,242 bytes (330.02 MB) freed.

**Final `outputs/` size**: ~346 MB (`du -sh`), dominated by the two
final videos themselves (120s: 233 MB, 20s: 40 MB) plus their QA
frames/contact sheet (~30 MB combined) — these are genuine final
deliverables, not clutter.

## Confirmation

- **Scope**: only `dangerous_space_repositioning/outputs/` was touched.
  No file outside this directory was created, modified, or deleted.
- **`pressing_structure/`**: untouched — not scanned, not referenced,
  not modified.
- **`offside_break/`**: untouched — not scanned, not referenced, not
  modified.
- **Canonical tracking/analytics data**
  (`outputs/analytics/testVideo1_120s_v3/`, `ExternalDownlaodVideo/`):
  untouched.
- **Source code, tests, docs, `HANDOFF.md`**: none deleted; only
  `HANDOFF.md` and `docs/DISPLAY_STABILITY.md` had references *updated*
  (not removed) to reflect the cleanup.

## Final retained deliverable paths (current as of the final round)

- `dangerous_space_repositioning/outputs/final_demo/dangerous_space_repositioning_120s_final.mp4` (THE final 120-second video)
- `dangerous_space_repositioning/outputs/final_demo/dangerous_space_repositioning_20s_final.mp4` (the final 20-second QA clip)
- `dangerous_space_repositioning/outputs/final_demo/final_120s_contact_sheet.png`
- `dangerous_space_repositioning/outputs/final_demo/qa_frames/` (17 frames: 13 timeline checkpoints + 4 scenario examples)
- `dangerous_space_repositioning/outputs/previews/01_ordinary_low_risk_moment.png`
- `dangerous_space_repositioning/outputs/previews/02_team_a_danger.png`
- `dangerous_space_repositioning/outputs/previews/03_team_b_danger.png`
- `dangerous_space_repositioning/outputs/previews/04_strong_reposition_recommendation.png`
- `dangerous_space_repositioning/outputs/previews/05_high_new_gap_risk_case.png`
- `dangerous_space_repositioning/outputs/previews/06_missing_uncertain_data.png`
- `dangerous_space_repositioning/outputs/contact_sheet/contact_sheet.png`
- `dangerous_space_repositioning/outputs/qa/grouped_region_bars_redesign/graph1_stacked_vs_grouped_comparison.png`
- `dangerous_space_repositioning/outputs/qa/grouped_region_bars_redesign/graph2_tick_vs_grouped_comparison.png`
- `dangerous_space_repositioning/outputs/cleanup_manifest_before_delete.txt`
- `dangerous_space_repositioning/outputs/cleanup_report.md`
