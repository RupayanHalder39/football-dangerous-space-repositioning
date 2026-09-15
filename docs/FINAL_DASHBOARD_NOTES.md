# Final Dashboard Notes — Dangerous Space Repositioning

Preview-only render (`dashboard/render_dangerous_space_dashboard.py`).
No full 120s video has been rendered yet, per this round's own explicit
instruction — six representative PNG previews plus one contact sheet
only.

## Canvas layout

`2304 × 1204`, matching the exact canvas size already established by
`pressing_structure`/`offside_break`'s own final dashboards (so the
three projects' preview assets stay visually comparable in scale):

- Header: `52px` — title + `t = NN.Ns` readout.
- Top row: `606px` — Tactical Match Feed (`52%` width, `1198px`) |
  3D Tactical Radar (`48%` width, `1106px`).
- Gap: `8px`.
- Graph row: `538px` — 3 equal-ish panels (Dangerous Space Severity /
  Opponent Control of Dangerous Space / Spatial Balance-New-Gap Risk),
  both teams on every graph.

## Row 1 — LEFT: Tactical Match Feed

The REAL broadcast frame (`ExternalDownlaodVideo/testVideo1_120s.mp4`),
with Voronoi drawn DIRECTLY on it via the real per-frame homography
(`outputs/analytics/testVideo1_120s_v3/homography_transformers.pkl`,
inverted the same way `pressing_structure`'s own overlay code already
does: `np.linalg.inv(transformer.m)`). Overlay layers, in order:

1. Restrained team-colored Voronoi fills (alpha 0.13) + clear cell
   boundaries.
2. The flagged PRIMARY dangerous region (Danger #1) — a soft orange
   disc, radius derived from the REAL cell area (`sqrt(area/pi)`),
   never a fixed decorative size. As of the Current-Attack Eligibility
   gate (see `HANDOFF.md` §6c), this region is drawn ONLY when a real
   cell passed the HARD eligibility filter this frame — it represents
   "space the CURRENT attacking team can plausibly exploit in the
   current/next attacking action," never simply the most structurally
   exposed cell anywhere on the pitch. When nothing is eligible, NO
   region is drawn at all (the status badge reads UNCERTAIN instead) —
   this now happens on the large majority of frames (~78%, see §6c's
   full audit), by design.
2b. Up to TWO additional distinct regions (Danger #2 / #3, this round —
   see `HANDOFF.md` §15 and `docs/METRIC_DEFINITIONS.md` §2c), drawn
   strictly fainter/smaller than Danger #1 with a small numbered
   "#2"/"#3" marker — never fabricated when fewer than 3 real distinct
   regions exist.
3. Real player dots (small, team-colored) + the ball (white).
4. "Opponent control NN%" pill label at the PRIMARY region.
5. If a candidate reposition exists for Danger #1: a cyan ring on the
   recommended player, a dashed connector + arrow, a ring at the
   suggested destination, and a faint cyan cylindrical spotlight
   beam rising from the recommended player (added in the radar-
   alignment-fix round — see `HANDOFF.md` §14e) — labeled "Best player
   to fix" / "Suggested move", matching the attached reference
   mockup's own callout language. Danger #2/#3 get the same "fixer +
   target + subtle spotlight" treatment at reduced size/opacity, with a
   "(reassigned)" suffix on the label when that region's own natural
   best fixer was already claimed by a higher-priority region (see
   `HANDOFF.md` §15's conflict-resolution write-up).
6. A status badge (top-left): `LOW RISK` / `MODERATE RISK` / `HIGH
   RISK` / `RECOMMENDATION FOUND` / `UNCERTAIN`, colored accordingly,
   with a `Team A: x.xx   Team B: x.xx` subtitle, or one of three
   honest UNCERTAIN subtitles: "Insufficient tracking evidence this
   frame" (structurally invalid Voronoi), "Possession/attacking
   direction unknown this frame" (§6c), or "No current attacking danger
   identified this frame" (context known, nothing eligible -- §6c). The
   status badge always refers to Danger #1 only — secondary/tertiary
   threats are represented purely visually, never via a competing
   status banner.

## Row 1 — RIGHT: 3D Tactical Radar

**ONE mode only** — Voronoi view. No Player View, no Heatmap, no mode
selector, per this project's own explicit instruction.

Reuses `tactical_shared.perspective_radar`'s already-shared pinhole-
camera projection (the SAME camera model `pressing_structure`/
`offside_break` already use for their own perspective radars) and
`offside_break`'s own human-footballer glyph primitives
(`_draw_player_shadow`, `_draw_player_body_human`, `_heading_cue`),
imported directly rather than re-implemented. Every object on this
panel — pitch markings, Voronoi polygons, the danger region(s), player
glyphs, the ball, the recommendation arrow(s) — is projected through
the SAME homography matrix, and the SAME up-to-3-region ranking as the
Match Feed panel (see above) is drawn here too, at the same
fainter/smaller visual weight for Danger #2/#3.

Every DYNAMIC object's pitch-width (y) coordinate is mirrored before
projection (`voronoi_radar._mirror_y`/`_mirror_*`) — a documented
coordinate-convention correction for a measured Y-axis mismatch between
this radar's own virtual camera and the real broadcast camera's
per-frame homography, NOT a cosmetic flip; see `HANDOFF.md` §14a/§14b
for the full root-cause audit and fix. The camera model itself and the
static pitch markings are unchanged.

Analytics are computed upstream in real pitch centimetres; this panel
never performs a tactical calculation of its own, only projection.

## Row 2 — Three graphs, both teams on every one

**Graphs 1/2 are BUCKETED BAR CHARTS** (redesigned for coach-facing
readability — see `HANDOFF.md` §16), not line charts — Graph 3 is still
a line chart, unchanged:

1. **Dangerous Space Severity by Region** (Graph 1, FINAL design —
   §17/§18) — for each fixed 4s bucket, SIX independent, GROUPED bars
   (never stacked, never summed): Team A's Danger #1/#2/#3 and Team B's
   Danger #1/#2/#3, each bar showing only that SPECIFIC region's own
   real mean severity. Danger #1 is drawn ~15% wider than #2/#3 (a
   subtle emphasis — it is the primary tactical problem — never
   dominant; see `HANDOFF.md` §18a) and all three ranks are shaded from
   full team color (#1) to faint (#3). A coach reads, per team, per
   region, exactly how severe each individual dangerous pocket was.
2. **Exploitable Danger by Region** (Graph 2, FINAL design — §17/§18)
   — identical grouped-bar layout to Graph 1, plotting each region's
   own real opponent-access probability instead of severity. Also never
   stacked/summed (access probabilities across different physical
   regions have no meaningful combined value; see `HANDOFF.md` §16d).
3. **Spatial Balance / New-Gap Risk** (Graph 3, UNCHANGED) — still a
   line chart, "higher = greater risk of an exposed structural gap."
   Already a whole-team structural metric, unrelated to how many
   distinct danger regions are flagged.

**LIVE tag** (§18b): the current, rightmost, still-accumulating 4s
bucket carries a small "LIVE" tag in the dashboard's own established
cyan (the same color as the spotlight/recommendation ring) — never
shown on a historical (fully-elapsed) bucket, and it moves with the
rolling window automatically.

Honest missing-data rule for Graphs 1/2 (see `HANDOFF.md` §16b/§17d): a
bucket where a team genuinely faced no eligible danger renders as a
real, confident, zero-height bar; a bucket where NOTHING is known
(possession/tracking entirely uncertain the whole 4s span) renders as a
visibly distinct hatched placeholder — never a fabricated zero. A
bucket resting on fewer than 10 real samples gets a small dashed
baseline tick as an honest "thin evidence" signal.

Same rendering convention as every other dashboard in this repo: fixed
y-range `[0,1]` for BOTH Graph 1 and Graph 2 (never auto-scaled frame
to frame — audited and confirmed mathematically bounded to `[0,1]`,
see `HANDOFF.md` §18c), a rolling `24s` window (`COACH_WINDOW_SEC`,
widened from 20s in an earlier round — formulas/smoothing unchanged)
divided into `4s` buckets for Graphs 1/2 (`COACH_TICK_SEC`, unchanged)
or `4s` ticks for Graph 3's own continuous line — see `HANDOFF.md`
§8b/§8c for the original graph-display polish pass detail, §15 for the
24s-window round, §16/§17 for the bucketed-bar and grouped-bar
redesigns, and §18 for this final round's small presentation polish.

## Preview frames generated (`outputs/previews/`)

**Note (post §6c, Current-Attack Eligibility gate)**: the table below
describes what these 6 frame numbers showed under EARLIER rounds'
formulas. Since only ~22% of frames now resolve to an eligible primary
danger (§6c), several of these specific, individually-chosen instants
now honestly render "UNCERTAIN" instead of their original story (e.g.
`02_team_a_danger.png`/`03_team_b_danger.png` at their exact original
frame numbers) — this is the correct, disclosed behavior of the
stricter gate, NOT a bug, and the frame numbers were deliberately NOT
changed to force a nicer-looking screenshot (explicitly against this
round's own instruction). The original table is kept for historical
reference; `outputs/qa/current_attack_gate_fix/` is the authoritative,
currently-accurate validation set for the eligibility gate.

| File | Frame | t | What it originally showed (pre-§6c) |
|---|---|---|---|
| `01_ordinary_low_risk_moment.png` | 1920 | 64.0s | The lowest max-severity frame found in a 180-frame scan (Team A 0.36 / Team B 0.35) — the calmest real moment available, honestly still "MODERATE" rather than a fabricated "LOW" example, since no sampled frame in this clip actually dropped below 0.35 for both teams |
| `02_team_a_danger.png` | 2020 | 67.3s | Team A clearly worse (0.66 vs 0.37) — HIGH RISK badge, danger region right at the edge of the box |
| `03_team_b_danger.png` | 840 | 28.0s | Team B clearly worse (0.75 vs 0.27), Opponent control 99% — an almost totally uncovered pocket right in front of goal |
| `04_strong_reposition_recommendation.png` | 1040 | 34.7s | The one real, positive-benefit case found this round (Team B, track 42, 300cm move, `benefit=+0.00509`) — "RECOMMENDATION FOUND" badge |
| `05_high_new_gap_risk_case.png` | 1170 | 39.0s | A DELIBERATELY forced illustration (`force_team=TEAM_A, force_player=55`) showing the highest-`new_gap_penalty` candidate (0.13) that player actually tested — not the auto-recommended move (whose own benefit is negative), chosen specifically to show what an elevated new-gap reading looks like |
| `06_missing_uncertain_data.png` | 220 | 7.3s | A real frame with fewer than 4 total tracked players — "UNCERTAIN / Insufficient tracking evidence this frame," empty radar, a real gap visible in the graph history |

Contact sheet: `outputs/contact_sheet/contact_sheet.png` (2×3 grid of
the above, each with its own caption banner) — regenerated under the
current formula each round; its content now reflects §6c's stricter
gate, which may differ from the table above.

## Known cosmetic limitations (disclosed, not hidden)

- **Only ~22% of frames now resolve to an eligible primary Current
  Dangerous Space** (see `HANDOFF.md` §6c's full audit) — the dashboard
  shows UNCERTAIN far more often than earlier rounds, by explicit
  design ("no recommendation beats a nonsensical one"). ~65% of frames
  are UNCERTAIN specifically because possession and/or real-time ball
  position is unknown (possession alone is unknown ~21% of the time
  even with this project's own extended 30s causal fallback; ball
  position is separately unavailable at points even when possession IS
  known); a further ~13% have known context but no real candidate
  passes the eligibility gate that instant.
- **Strongly-behind-the-ball primary selections are 0% by
  construction** — the Current-Attack Eligibility gate (§6c) is a HARD
  filter, not the earlier round's soft penalty, so this is a structural
  guarantee, verified against a 475-frame broad sample (see
  `outputs/qa/current_attack_gate_fix/candidate_eligibility_validation.csv`).
  A small share (35.6% of resolved selections) legitimately sit within
  a ~5m backward tolerance for genuine cutback/support-pocket cases —
  individually inspected (`behind_tolerance_audit.csv` and its
  montage) and confirmed to sit immediately adjacent to the ball, never
  far-flung exposure.
- The Tactical Match Feed's danger-region circle can extend past the
  visible camera frame edge when the flagged region sits near the
  boundary of what the broadcast camera currently shows — expected,
  not a bug (the real broadcast camera doesn't always frame the whole
  pitch).
- The "Opponent Control of Dangerous Space" graph is visibly noisier
  than the other two (the underlying logistic access model can swing
  quickly between two evenly-matched responders) — a real property of
  the reused reachability model, not a rendering artifact.
- DOCX/dashboard-style visual polish (rounded cards, gradient headers)
  used by `pressing_structure`'s OLDER `dashboard_style.py` was
  deliberately NOT copied here; this project's `dashboard_style.py`
  instead matches the flatter, panel-accent-stripe look actually used
  by the CURRENT `*_v4_simple.py` dashboards in both sibling projects,
  which is also closer to the attached reference mockup's own visual
  language.
