"""
Shared rendering primitives for the Dangerous Space Repositioning
dashboard. Visual language only -- no analytics logic lives here.

Team color convention for THIS project (deliberately matches the
user-attached reference mockup, NOT `pressing_structure`/`offside_break`'s
own green/gold convention -- the two projects are visually independent):
  Team A (team_id 0) = BLUE
  Team B (team_id 1) = RED
"""
import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX

# BGR throughout (OpenCV convention), matching every other dashboard in this repo.
BG = (28, 22, 18)                 # near-black navy canvas background
PANEL_BG = (40, 32, 26)
HEADER_BG = (24, 18, 14)
BORDER_SOFT = (70, 58, 48)
GRID = (58, 48, 40)
TEXT_WHITE = (238, 238, 238)
TEXT_DIM = (160, 150, 140)

TEAM_COLOR = {0: (232, 158, 74), 1: (72, 72, 235)}   # BGR: Team A = blue-ish, Team B = red
# (0,1 -> BGR tuples: (232,158,74) reads as a strong sky-blue on screen;
# (72,72,235) reads as a strong red -- picked for contrast against the
# dark green pitch and dark navy panel background alike.)
TEAM_LETTER = {0: "A", 1: "B"}

DANGER_COLOR = (40, 140, 255)       # orange -- the flagged dangerous region
RECOMMEND_COLOR = (235, 220, 70)    # cyan -- recommended player / target marker
GHOST_COLOR = (150, 150, 150)
BALL_COLOR = (255, 255, 255)
ACCENT_RED = (60, 60, 220)          # header/panel accent stripe


def panel_frame(w, h, bg=PANEL_BG):
    img = np.full((h, w, 3), bg, dtype=np.uint8)
    cv2.rectangle(img, (0, 0), (w - 1, h - 1), BORDER_SOFT, 1)
    return img


def panel_title(img, title, sub=None, accent=ACCENT_RED):
    cv2.rectangle(img, (12, 8), (15, 24), accent, -1)
    cv2.putText(img, title, (22, 20), FONT, 0.46, TEXT_WHITE, 2, cv2.LINE_AA)
    if sub:
        cv2.putText(img, sub, (22, 36), FONT, 0.30, TEXT_DIM, 1, cv2.LINE_AA)


def draw_header(width, height, title, right_text, accent=ACCENT_RED):
    img = np.full((height, width, 3), HEADER_BG, dtype=np.uint8)
    cv2.putText(img, title, (24, int(height * 0.65)), FONT, height / 46.0, TEXT_WHITE, 2, cv2.LINE_AA)
    text, color = right_text
    tw = cv2.getTextSize(text, FONT, height / 60.0, 1)[0][0]
    cv2.putText(img, text, (width - 24 - tw, int(height * 0.62)), FONT, height / 60.0, color, 1, cv2.LINE_AA)
    cv2.line(img, (0, height - 2), (width, height - 2), accent, 2)
    return img


def composite_badge(img, x, y, title, color, subtitle, w=420):
    h = 58
    overlay = img.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (18, 14, 12), -1)
    cv2.addWeighted(overlay, 0.72, img, 0.28, 0, dst=img)
    cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
    cv2.putText(img, title, (x + 10, y + 24), FONT, 0.55, TEXT_WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, subtitle, (x + 10, y + 44), FONT, 0.32, TEXT_DIM, 1, cv2.LINE_AA)
    return img


def draw_pill_label(img, x, y, text, color, text_color=(15, 15, 15)):
    """A small filled rounded pill with dark text -- used for the "1
    Dangerous space" / "2 Opponent control" / "3 Best player to fix" /
    "4 Suggested move" callouts, matching the attached reference
    mockup's own label style."""
    (tw, th), _ = cv2.getTextSize(text, FONT, 0.42, 1)
    pad_x, pad_y = 8, 5
    x0, y0 = x, y - th - pad_y
    x1, y1 = x + tw + 2 * pad_x, y + pad_y
    cv2.rectangle(img, (x0, y0), (x1, y1), color, -1, cv2.LINE_AA)
    cv2.rectangle(img, (x0, y0), (x1, y1), (15, 15, 15), 1, cv2.LINE_AA)
    cv2.putText(img, text, (x0 + pad_x, y1 - pad_y), FONT, 0.42, text_color, 1, cv2.LINE_AA)
    return (x1 - x0, y1 - y0)


def numbered_pill(img, x, y, number, text, color):
    return draw_pill_label(img, x, y, f"{number}  {text}", color)
