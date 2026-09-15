import sys, csv
sys.path.insert(0, "/Users/rupayan/RupayanPHD/Problem1_2Papers")
from dangerous_space_repositioning.analytics.data_loader import load_match_data, frame_players, TEAM_A, TEAM_B
from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players
from dangerous_space_repositioning.analytics.dangerous_space import (
    dangerous_space_for_team, LEVEL_WITH_BALL_TOLERANCE_CM,
)
from dangerous_space_repositioning.analytics.opponent_access import opponent_control_of_region

match = load_match_data()
STRIDE = 5
OUT_CSV = "/Users/rupayan/RupayanPHD/Problem1_2Papers/dangerous_space_repositioning/outputs/qa/attack_relevance_fix/validation_broad_sample.csv"

rows = []
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
    sev_a = danger_a["top"].severity if danger_a["valid"] and danger_a["top"] else None
    sev_b = danger_b["top"].severity if danger_b["valid"] and danger_b["top"] else None
    if sev_a is None and sev_b is None:
        defending_team, top = None, None
    else:
        defending_team, top = (TEAM_A, danger_a["top"]) if (sev_a or 0) >= (sev_b or 0) else (TEAM_B, danger_b["top"])

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
        "attack_progress_cm": round(top.components["attack_progress_cm"], 1)
            if (top is not None and top.components.get("attack_progress_cm") is not None) else None,
        "attack_phase_active": top.components.get("attack_phase_active") if top else None,
        "direction_class": None,
        "uncertainty_state": confidence,
    }
    if top is not None and ball is not None and defending_team is not None:
        row["opponent_access"] = round(opponent_control_of_region(defending_team, (top.x, top.y), team_a, team_b), 4)
    ap = row["attack_progress_cm"]
    if row["attack_phase_active"] is True:
        if ap is not None and ap >= -LEVEL_WITH_BALL_TOLERANCE_CM:
            row["direction_class"] = "ahead_or_level"
        elif ap is not None and ap >= -2500:
            row["direction_class"] = "slightly_behind"
        else:
            row["direction_class"] = "strongly_behind"
    elif row["attack_phase_active"] is False:
        row["direction_class"] = "counterattack_exposure_only"
    elif attacking_team_actual is None:
        row["direction_class"] = "possession_uncertain"
    elif ball is None:
        row["direction_class"] = "ball_unavailable_this_frame"
    else:
        row["direction_class"] = "other_unknown"
    rows.append(row)

with open(OUT_CSV, "w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"wrote {OUT_CSV} ({len(rows)} rows)")

# Summary stats
from collections import Counter
dc = Counter(r["direction_class"] for r in rows)
total = len(rows)
print("\nDirection-class breakdown (selected primary danger region):")
for k, v in dc.most_common():
    print(f"  {k}: {v} ({v/total:.1%})")

conf = Counter(r["possession_confidence"] for r in rows)
print("\npossession confidence breakdown:")
for k, v in conf.most_common():
    print(f"  {k}: {v} ({v/total:.1%})")

att = Counter(r["attacking_team"] for r in rows)
print("\nattacking_team breakdown:")
for k, v in att.most_common():
    print(f"  {k}: {v} ({v/total:.1%})")
