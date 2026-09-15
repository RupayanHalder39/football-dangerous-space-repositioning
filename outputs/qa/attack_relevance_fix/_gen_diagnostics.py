"""Generates OLD-vs-NEW top-down diagnostic images for specific frames,
using the OLD (pre-correction) dangerous-space formula reimplemented
here standalone for reproducible comparison (the real, shipped
`dangerous_space.py` now contains the FIXED formula only)."""
import sys, math
sys.path.insert(0, "/Users/rupayan/RupayanPHD/Problem1_2Papers")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from dangerous_space_repositioning.analytics.data_loader import load_match_data, frame_players, TEAM_A, TEAM_B
from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players
from dangerous_space_repositioning.analytics.dangerous_space import dangerous_space_for_team
from tactical_shared.coordinates import DEFAULT_PITCH

# ---- OLD formula, reimplemented standalone (matches the pre-fix dangerous_space.py exactly) ----
from dangerous_space_repositioning.analytics.dangerous_space import (
    goal_proximity_score, centrality_score, ball_proximity_score,
    receiver_support_score, coverage_gap_score, area_gate, cell_centroid,
)
from dangerous_space_repositioning.analytics.voronoi_control import opponent_owned_cells

OLD_WEIGHTS = {"goal_proximity": 0.20, "centrality": 0.10, "ball_proximity": 0.10,
               "receiver_support": 0.15, "coverage_gap": 0.35, "progression_value": 0.10}


def old_progression_value_score(attacking_team, x, ball, pitch=DEFAULT_PITCH):
    if ball is None:
        return 0.5
    cell_depth = pitch.depth(attacking_team, x)
    ball_depth = pitch.depth(attacking_team, ball["x_pitch"])
    span = pitch.length_cm * 0.5
    return max(0.0, min(1.0, 0.5 + (cell_depth - ball_depth) / span * 0.5))


def old_dangerous_space_for_team(defending_team, team_a, team_b, ball, pitch, voronoi_result):
    if not voronoi_result.get("valid"):
        return None
    defending_players = team_a if defending_team == 0 else team_b
    attacking_players = team_b if defending_team == 0 else team_a
    attacking_team = 1 - defending_team
    cells = opponent_owned_cells(voronoi_result, defending_team)
    if not cells:
        return None
    best = None
    for cell in cells:
        x, y = cell_centroid(cell)
        g = goal_proximity_score(defending_team, x, y, pitch)
        c = centrality_score(y, pitch)
        b, _ = ball_proximity_score(ball, x, y)
        r, _ = receiver_support_score(x, y, attacking_players)
        cov, _ = coverage_gap_score(x, y, defending_players)
        prog = old_progression_value_score(attacking_team, x, ball, pitch)
        raw = (OLD_WEIGHTS["goal_proximity"] * g + OLD_WEIGHTS["centrality"] * c +
               OLD_WEIGHTS["ball_proximity"] * b + OLD_WEIGHTS["receiver_support"] * r +
               OLD_WEIGHTS["coverage_gap"] * cov + OLD_WEIGHTS["progression_value"] * prog)
        severity = raw * area_gate(cell["area_cm2"])
        if best is None or severity > best[2]:
            best = (x, y, severity)
    return best


def old_selection(team_a, team_b, ball, pitch, voronoi_result):
    a = old_dangerous_space_for_team(TEAM_A, team_a, team_b, ball, pitch, voronoi_result)
    b = old_dangerous_space_for_team(TEAM_B, team_a, team_b, ball, pitch, voronoi_result)
    sev_a = a[2] if a else None
    sev_b = b[2] if b else None
    if (sev_a or 0) >= (sev_b or 0):
        return TEAM_A, a
    return TEAM_B, b


def new_selection(match, frame, team_a, team_b, ball, voronoi_result):
    attacking_team_actual, confidence = match.attacking_team_at(frame)
    da = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, match.pitch, voronoi_result,
                                   attacking_team_actual=attacking_team_actual)
    db = dangerous_space_for_team(TEAM_B, team_a, team_b, ball, match.pitch, voronoi_result,
                                   attacking_team_actual=attacking_team_actual)
    sev_a = da["top"].severity if da["valid"] and da["top"] else None
    sev_b = db["top"].severity if db["valid"] and db["top"] else None
    if sev_a is None and sev_b is None:
        return None, None, attacking_team_actual, confidence
    team, top = (TEAM_A, da["top"]) if (sev_a or 0) >= (sev_b or 0) else (TEAM_B, db["top"])
    return team, top, attacking_team_actual, confidence


PITCH_L, PITCH_W = DEFAULT_PITCH.length_cm, DEFAULT_PITCH.width_cm


def draw_pitch(ax):
    ax.set_xlim(-300, PITCH_L + 300)
    ax.set_ylim(-300, PITCH_W + 300)
    ax.set_aspect("equal")
    ax.set_facecolor("#0d2b12")
    ax.add_patch(mpatches.Rectangle((0, 0), PITCH_L, PITCH_W, fill=False, edgecolor="white", linewidth=1.5))
    ax.axvline(PITCH_L / 2, color="white", linewidth=1, alpha=0.6)
    ax.add_patch(mpatches.Circle((PITCH_L / 2, PITCH_W / 2), 900, fill=False, edgecolor="white", linewidth=1, alpha=0.6))
    ax.set_xticks([])
    ax.set_yticks([])


def render_case(match, frame, name, title_suffix=""):
    team_a, team_b = frame_players(match, frame)
    ball = match.ball_at(frame)
    voronoi_result = voronoi_for_players(team_a, team_b)
    attacking_team_actual, confidence = match.attacking_team_at(frame)

    old_team, old_res = old_selection(team_a, team_b, ball, match.pitch, voronoi_result)
    new_team, new_top, _, _ = new_selection(match, frame, team_a, team_b, ball, voronoi_result)

    fig, ax = plt.subplots(figsize=(11, 7.2))
    draw_pitch(ax)

    for p in team_a:
        ax.plot(p["x_pitch"], p["y_pitch"], "o", color="#3f8ef0", markersize=7, markeredgecolor="black", markeredgewidth=0.5)
    for p in team_b:
        ax.plot(p["x_pitch"], p["y_pitch"], "o", color="#e64545", markersize=7, markeredgecolor="black", markeredgewidth=0.5)

    if ball is not None:
        ax.plot(ball["x_pitch"], ball["y_pitch"], "*", color="white", markersize=18, markeredgecolor="black", markeredgewidth=0.8, zorder=5)
        if attacking_team_actual is not None:
            sign = DEFAULT_PITCH.attacking_sign(attacking_team_actual)
            arrow_len = 1800
            ax.annotate("", xy=(ball["x_pitch"] + sign * arrow_len, ball["y_pitch"]), xytext=(ball["x_pitch"], ball["y_pitch"]),
                        arrowprops=dict(arrowstyle="-|>", color="yellow", lw=3), zorder=6)

    if old_res is not None:
        ox, oy, osev = old_res
        ax.add_patch(mpatches.Circle((ox, oy), 700, fill=True, facecolor="orange", alpha=0.35, edgecolor="orange", linewidth=2.5, zorder=4))
        ax.plot(ox, oy, "x", color="orange", markersize=12, markeredgewidth=3, zorder=7)
        ax.annotate(f"OLD region\nseverity={osev:.3f}", (ox, oy), xytext=(ox, oy - 900),
                    ha="center", color="orange", fontsize=10, fontweight="bold")

    if new_top is not None:
        ax.add_patch(mpatches.Circle((new_top.x, new_top.y), 700, fill=True, facecolor="#00e5ff", alpha=0.35, edgecolor="#00e5ff", linewidth=2.5, zorder=4))
        ax.plot(new_top.x, new_top.y, "+", color="#00e5ff", markersize=14, markeredgewidth=3, zorder=7)
        ax.annotate(f"NEW region\nseverity={new_top.severity:.3f}", (new_top.x, new_top.y), xytext=(new_top.x, new_top.y + 900),
                    ha="center", color="#00e5ff", fontsize=10, fontweight="bold")

    at_str = {0: "Team A", 1: "Team B", None: "UNKNOWN"}[attacking_team_actual]
    old_team_str = {0: "Team A", 1: "Team B"}[old_team]
    new_team_str = {0: "Team A", 1: "Team B", None: "n/a"}[new_team]
    title = (f"{name}  --  frame {frame}, t={frame/match.fps:.1f}s{title_suffix}\n"
             f"Attacking team (possession, {confidence}): {at_str}   |   "
             f"OLD selected defending: {old_team_str}   |   NEW selected defending: {new_team_str}")
    ax.set_title(title, color="white", fontsize=10.5)
    fig.patch.set_facecolor("#111111")
    legend_handles = [
        mpatches.Patch(facecolor="#3f8ef0", label="Team A"),
        mpatches.Patch(facecolor="#e64545", label="Team B"),
        mpatches.Patch(facecolor="orange", alpha=0.5, label="OLD dangerous region"),
        mpatches.Patch(facecolor="#00e5ff", alpha=0.5, label="NEW dangerous region"),
    ]
    ax.legend(handles=legend_handles, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=4, fontsize=9, facecolor="#222222", labelcolor="white")
    plt.tight_layout()
    out = f"/Users/rupayan/RupayanPHD/Problem1_2Papers/dangerous_space_repositioning/outputs/qa/attack_relevance_fix/{name}.png"
    plt.savefig(out, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    match = load_match_data()
    cases = [
        ("old_vs_new_t34p7", 1040, "  (the flagship reported bad frame)"),
        ("team_a_attacking_case1", 150, ""),
        ("team_a_attacking_case2", 1020, ""),
        ("team_b_attacking_case1", 135, ""),
        ("team_b_attacking_case2", 2400, ""),
        ("possession_change_case", 147, "  (possession just flipped Team B -> Team A; frame 144 was still Team B)"),
        ("uncertain_possession_case", 60, "  (genuinely uncertain possession, with real ball evidence)"),
    ]
    for name, frame, suffix in cases:
        render_case(match, frame, name, suffix)
