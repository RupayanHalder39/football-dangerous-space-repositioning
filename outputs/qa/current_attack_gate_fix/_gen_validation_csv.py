import sys, csv
sys.path.insert(0, "/Users/rupayan/RupayanPHD/Problem1_2Papers")
from dangerous_space_repositioning.analytics.data_loader import load_match_data, frame_players, TEAM_A, TEAM_B
from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players
from dangerous_space_repositioning.analytics.dangerous_space import (
    dangerous_space_for_team, BACKWARD_TOLERANCE_CM,
    REASON_UNCERTAIN_CONTEXT, REASON_NO_ELIGIBLE_CANDIDATE,
)
from dangerous_space_repositioning.analytics.opponent_access import opponent_control_of_region

match = load_match_data()
STRIDE = 5
OUT_CSV = "/Users/rupayan/RupayanPHD/Problem1_2Papers/dangerous_space_repositioning/outputs/qa/current_attack_gate_fix/candidate_eligibility_validation.csv"
BEHIND_CSV = "/Users/rupayan/RupayanPHD/Problem1_2Papers/dangerous_space_repositioning/outputs/qa/current_attack_gate_fix/behind_tolerance_audit.csv"

rows = []
behind_rows = []
for f in range(0, match.n_frames, STRIDE):
    team_a, team_b = frame_players(match, f)
    if len(team_a) + len(team_b) < 4:
        continue
    ball = match.ball_at(f)
    attacking_team_actual, confidence = match.attacking_team_at(f)
    voronoi_result = voronoi_for_players(team_a, team_b)

    danger_a = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, match.pitch, voronoi_result,
                                         attacking_team_actual=attacking_team_actual)
    danger_b = dangerous_space_for_team(TEAM_B, team_a, team_b, ball, match.pitch, voronoi_result,
                                         attacking_team_actual=attacking_team_actual)
    sev_a = danger_a["top"].severity if danger_a["top"] else None
    sev_b = danger_b["top"].severity if danger_b["top"] else None

    if sev_a is None and sev_b is None:
        defending_team, top = None, None
        if danger_a.get("reason") == REASON_UNCERTAIN_CONTEXT or danger_b.get("reason") == REASON_UNCERTAIN_CONTEXT:
            uncertainty_state = "possession_or_ball_unknown"
        elif danger_a.get("reason") == REASON_NO_ELIGIBLE_CANDIDATE or danger_b.get("reason") == REASON_NO_ELIGIBLE_CANDIDATE:
            uncertainty_state = "no_eligible_candidate"
        else:
            uncertainty_state = "insufficient_tracking"
    else:
        defending_team, top = (TEAM_A, danger_a["top"]) if (sev_a or 0) >= (sev_b or 0) else (TEAM_B, danger_b["top"])
        uncertainty_state = "resolved"

    row = {
        "frame": f, "time_sec": round(f / match.fps, 2),
        "attacking_team": attacking_team_actual, "possession_confidence": confidence,
        "ball_x": round(ball["x_pitch"], 1) if ball else None,
        "ball_y": round(ball["y_pitch"], 1) if ball else None,
        "selected_defending_team": defending_team,
        "region_x": round(top.x, 1) if top else None,
        "region_y": round(top.y, 1) if top else None,
        "severity": round(top.severity, 4) if top else None,
        "opponent_access": None,
        "progress_cm": round(top.components["progress_cm"], 1)
            if (top is not None and top.components.get("progress_cm") is not None) else None,
        "category": top.components["category"] if top else None,
        "eligible": top.components["eligible"] if top else False,
        "uncertainty_state": uncertainty_state,
    }
    if top is not None and ball is not None and defending_team is not None:
        row["opponent_access"] = round(opponent_control_of_region(defending_team, (top.x, top.y), team_a, team_b), 4)
    rows.append(row)

    if top is not None and row["progress_cm"] is not None and row["progress_cm"] < 0:
        goal_x = match.pitch.own_goal(defending_team)
        goal_dist = ((top.x - goal_x) ** 2 + (top.y - match.pitch.width_cm / 2) ** 2) ** 0.5
        behind_rows.append({
            **row,
            "goal_proximity": round(top.components["goal_proximity"], 4),
            "centrality": round(top.components["centrality"], 4),
            "goal_dist_cm": round(goal_dist, 1),
        })

with open(OUT_CSV, "w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {OUT_CSV} ({len(rows)} rows)")

if behind_rows:
    with open(BEHIND_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(behind_rows[0].keys()))
        writer.writeheader()
        writer.writerows(behind_rows)
print(f"wrote {BEHIND_CSV} ({len(behind_rows)} rows)")

from collections import Counter
total = len(rows)
resolved = [r for r in rows if r["uncertainty_state"] == "resolved"]
print(f"\ntotal sampled frames (>=4 players): {total}")
unc = Counter(r["uncertainty_state"] for r in rows)
for k, v in unc.most_common():
    print(f"  {k}: {v} ({v/total:.1%})")

print(f"\nresolved (eligible primary danger selected) frames: {len(resolved)} ({len(resolved)/total:.1%})")
dc = Counter(r["category"] for r in resolved)
for k, v in dc.most_common():
    print(f"  category={k}: {v}")

# Direction breakdown among resolved (all should be CURRENT_DANGEROUS_SPACE by construction)
ahead_or_level = sum(1 for r in resolved if r["progress_cm"] is not None and r["progress_cm"] >= -BACKWARD_TOLERANCE_CM)
strongly_behind = sum(1 for r in resolved if r["progress_cm"] is not None and r["progress_cm"] < -BACKWARD_TOLERANCE_CM)
print(f"\nAmong resolved primary selections ({len(resolved)}):")
print(f"  progress_cm >= 0 (ahead): {sum(1 for r in resolved if r['progress_cm'] is not None and r['progress_cm']>=0)} "
      f"({sum(1 for r in resolved if r['progress_cm'] is not None and r['progress_cm']>=0)/max(len(resolved),1):.1%})")
print(f"  0 > progress_cm >= -{BACKWARD_TOLERANCE_CM:.0f}cm (within tolerance): "
      f"{sum(1 for r in resolved if r['progress_cm'] is not None and -BACKWARD_TOLERANCE_CM<=r['progress_cm']<0)} "
      f"({sum(1 for r in resolved if r['progress_cm'] is not None and -BACKWARD_TOLERANCE_CM<=r['progress_cm']<0)/max(len(resolved),1):.1%})")
print(f"  progress_cm < -{BACKWARD_TOLERANCE_CM:.0f}cm (strongly behind -- SHOULD BE ZERO): {strongly_behind} ({strongly_behind/max(len(resolved),1):.1%})")
