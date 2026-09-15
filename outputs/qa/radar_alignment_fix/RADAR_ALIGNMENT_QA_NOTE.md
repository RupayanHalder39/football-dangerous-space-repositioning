# Radar/Match-Feed Alignment Fix — QA Note

Full technical detail: `HANDOFF.md` §14. This is the short summary.

## What was wrong

The 3D Tactical Radar's virtual camera and the real broadcast camera
disagreed on which way the pitch-**width** (Y) axis runs. Both agreed
on X (left/right, along the pitch length). The real camera's per-frame
homography has X matching the radar's own convention but Y inverted —
present in every frame checked, a constant/structural mismatch, not an
intermittent glitch. It only became visually obvious when the danger
region and the recommended player/ball were separated substantially
along that axis (near a touchline), which is why it looked like it
happened only "in some moments."

## What was ruled out first

- A real-camera cut mid-clip changing orientation — checked directly
  across 405 frames, found zero orientation flips. Not the cause.
- Rotating the radar's virtual camera 180° (`yaw_deg=180`) — this DOES
  fix Y, but a camera-yaw rotation necessarily flips X and Y together
  (real 3D geometry: "forward" and "right" are coupled), so it breaks
  X instead. Rejected — this would have been exactly the kind of blind
  cosmetic flip we were told not to apply, and it's provably wrong on
  one axis.

## The actual fix

Since X already agreed and only Y was inverted (an axis-independent
pattern no camera rotation can produce), this is a coordinate-
**convention** mismatch, not a camera-pose problem — the same category
of quirk this project already documents for `DEFAULT_PITCH.own_goal()`
(Team A's goal sits at `x = length_cm`, not `x = 0`). The fix mirrors
only the Y (pitch-width) coordinate of every dynamic object — players
(position + velocity), ball, Voronoi cells, danger point, recommended
player and target — once, at the top of `compose_radar_panel`, before
projection. The camera model and static pitch markings are untouched.

**No analytics formula was changed.** This is a rendering-only fix in
`dashboard/voronoi_radar.py`.

## Spatial QA result

Checked at 5 required timestamps (start, ~5s, ~10s, ~15s, end/strong-
recommendation) — match feed and radar agree at all 5 on which side
the danger region, ball, and recommended player sit. See
`radar_alignment_qa_contact_sheet.png`. One checkpoint (~5s, frame 590)
initially looked ambiguous in a raw pixel comparison, but the real
pitch-space separation driving that comparison is under 2 metres —
below where "left" vs "right" is a meaningful claim in either camera's
projection; the dominant real separation (~11.7m, the other axis)
agreed correctly, and the rendered frame visually confirms both panels
show the same tactical picture.

## Graphs — no changes needed

The three graph panels are computed and drawn through a completely
separate code path from the radar panel (different function, different
input data, no shared import). The radar fix cannot reach them, and
they were reprinted at every QA checkpoint anyway: labels, team
colors, real broken gaps, and the fixed 20-second window are all as
before and consistent with the corrected radar/match-feed picture at
each instant.

## Cyan spotlight — added

A faint, translucent cyan cylindrical beam (with a soft glow at its
base) now rises from the recommended player's position in the Match
Feed panel. It reuses the same stabilized recommendation state that
already drives the "Best player to fix" ring, so it needed no new
tracking logic: it shows only when a valid recommendation exists,
switches when the recommendation changes, and disappears immediately
during UNCERTAIN frames — confirmed by rendering both a resolved frame
(1040) and an UNCERTAIN one (220).

## What was NOT done (by design)

- The 120-second full video was **not** rendered — only the corrected
  20-second clip, per this round's stop condition.
- `pressing_structure` and `offside_break` were **not** touched, even
  though they likely share this same latent Y-axis mismatch (same
  source video, same homography file, same shared camera module) —
  flagged for a future round, out of scope here.
- No matching radar-side cyan halo was added (explicitly optional in
  the brief) — the Match Feed spotlight alone was judged sufficient.
