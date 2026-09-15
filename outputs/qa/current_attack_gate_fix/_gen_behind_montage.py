import sys
sys.path.insert(0, "/Users/rupayan/RupayanPHD/Problem1_2Papers")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from dangerous_space_repositioning.analytics.data_loader import load_match_data, frame_players, TEAM_A, TEAM_B
from dangerous_space_repositioning.analytics.voronoi_control import voronoi_for_players
from dangerous_space_repositioning.analytics.dangerous_space import dangerous_space_for_team
from tactical_shared.coordinates import DEFAULT_PITCH

PITCH_L, PITCH_W = DEFAULT_PITCH.length_cm, DEFAULT_PITCH.width_cm
FRAMES = [265, 2225, 1410, 1815, 3425, 1040]  # representative spread of behind-tolerance "support pocket"/"cutback" cases


def draw_pitch(ax):
    ax.set_xlim(-300, PITCH_L + 300)
    ax.set_ylim(-300, PITCH_W + 300)
    ax.set_aspect("equal")
    ax.set_facecolor("#0d2b12")
    ax.add_patch(mpatches.Rectangle((0, 0), PITCH_L, PITCH_W, fill=False, edgecolor="white", linewidth=1.2))
    ax.axvline(PITCH_L / 2, color="white", linewidth=0.8, alpha=0.5)
    ax.add_patch(mpatches.Circle((PITCH_L / 2, PITCH_W / 2), 900, fill=False, edgecolor="white", linewidth=0.8, alpha=0.5))
    ax.set_xticks([])
    ax.set_yticks([])


def render_case(ax, match, frame):
    team_a, team_b = frame_players(match, frame)
    ball = match.ball_at(frame)
    at, conf = match.attacking_team_at(frame)
    voronoi_result = voronoi_for_players(team_a, team_b)
    da = dangerous_space_for_team(TEAM_A, team_a, team_b, ball, match.pitch, voronoi_result, attacking_team_actual=at)
    db = dangerous_space_for_team(TEAM_B, team_a, team_b, ball, match.pitch, voronoi_result, attacking_team_actual=at)
    sev_a = da["top"].severity if da["top"] else None
    sev_b = db["top"].severity if db["top"] else None
    team, top = (TEAM_A, da["top"]) if (sev_a or 0) >= (sev_b or 0) else (TEAM_B, db["top"])

    draw_pitch(ax)
    for p in team_a:
        ax.plot(p["x_pitch"], p["y_pitch"], "o", color="#3f8ef0", markersize=5, markeredgecolor="black", markeredgewidth=0.4)
    for p in team_b:
        ax.plot(p["x_pitch"], p["y_pitch"], "o", color="#e64545", markersize=5, markeredgecolor="black", markeredgewidth=0.4)
    if ball is not None:
        ax.plot(ball["x_pitch"], ball["y_pitch"], "*", color="white", markersize=13, markeredgecolor="black", markeredgewidth=0.6, zorder=5)
        if at is not None:
            sign = DEFAULT_PITCH.attacking_sign(at)
            ax.annotate("", xy=(ball["x_pitch"] + sign * 1500, ball["y_pitch"]), xytext=(ball["x_pitch"], ball["y_pitch"]),
                        arrowprops=dict(arrowstyle="-|>", color="yellow", lw=2.2), zorder=6)
    if top is not None:
        ax.add_patch(mpatches.Circle((top.x, top.y), 600, fill=True, facecolor="#00e5ff", alpha=0.4, edgecolor="#00e5ff", linewidth=2, zorder=4))
        ax.plot(top.x, top.y, "+", color="#00e5ff", markersize=11, markeredgewidth=2.5, zorder=7)

    prog = top.components["progress_cm"] if top else None
    title = (f"frame {frame}  t={frame/match.fps:.1f}s\n"
             f"team={'A' if team==TEAM_A else 'B'}  attacking={'A' if at==TEAM_A else 'B' if at==TEAM_B else '?'} "
             f"({conf})\nprogress={prog:.0f}cm  severity={top.severity:.3f}" if top else f"frame {frame}: no eligible region")
    ax.set_title(title, color="white", fontsize=8.5)


match = load_match_data()
fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
fig.patch.set_facecolor("#111111")
for ax, frame in zip(axes.flat, FRAMES):
    render_case(ax, match, frame)
fig.suptitle("Representative BEHIND-TOLERANCE (support-pocket/cutback) CURRENT_DANGEROUS_SPACE selections\n"
             "(all within the -500cm backward tolerance -- yellow arrow = real attacking direction, cyan = selected region)",
             color="white", fontsize=11)
plt.tight_layout(rect=[0, 0, 1, 0.92])
out = "/Users/rupayan/RupayanPHD/Problem1_2Papers/dangerous_space_repositioning/outputs/qa/current_attack_gate_fix/behind_tolerance_montage.png"
plt.savefig(out, dpi=140, facecolor=fig.get_facecolor())
print("wrote", out)
