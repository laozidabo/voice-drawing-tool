import os
import math
import re
import time
import threading
import queue
import sys
from typing import Optional, List, Dict

os.environ.pop('WAYLAND_DISPLAY', None)
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'

try:
    import numpy as np
    import cv2
except ImportError:
    np = None
    cv2 = None

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# Find a Chinese-capable font
_ZH_FONT_PATH = None
for _fp in [
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Light.ttc",
    "/home/suki/.local/share/fonts/zhcn/SourceHanSerifSC-Regular.otf",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-DemiLight.ttc",
]:
    if os.path.exists(_fp):
        _ZH_FONT_PATH = _fp
        break


def _gui_available() -> bool:
    """Check if OpenCV GUI can actually open a window (vs headless/container)."""
    if cv2 is None:
        return False
    try:
        cv2.namedWindow('_gui_test')
        cv2.destroyAllWindows()
        return True
    except Exception:
        return False


_HAS_GUI = _gui_available()

from .commands import (
    CommandParser, Command,
)

_FONT_CACHE: dict = {}


def put_chinese_text(img, text, position, font_size=20, color=(255, 255, 255)):
    """Render Chinese text onto an OpenCV image using PIL.

    Args:
        img: numpy array (OpenCV image, BGR)
        text: string to render (supports Chinese)
        position: (x, y) top-left position
        font_size: font size in pixels
        color: (B, G, R) color tuple
    Returns:
        img with text rendered on it
    """
    if not _PIL_AVAILABLE or not _ZH_FONT_PATH:
        # Fallback: use cv2.putText (ASCII only)
        cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                    font_size / 30.0, color, 1, cv2.LINE_AA)
        return img

    # Convert BGR to RGB for PIL
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)

    try:
        key = (_ZH_FONT_PATH, font_size)
        if key not in _FONT_CACHE:
            _FONT_CACHE[key] = ImageFont.truetype(_ZH_FONT_PATH, font_size)
        font = _FONT_CACHE[key]
    except Exception:
        font = ImageFont.load_default()

    # PIL uses RGB, OpenCV uses BGR
    rgb_color = (color[2], color[1], color[0])
    draw.text(position, text, font=font, fill=rgb_color)

    # Convert back to BGR for OpenCV
    result = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    np.copyto(img, result)
    return img


class DrawingCanvas:
    WIDTH = 800
    HEIGHT = 600
    BG_COLOR = (245, 248, 250)  # warm off-white (BGR of RGB 250,248,245)

    def __init__(self):
        self.image = np.full((self.HEIGHT, self.WIDTH, 3), self.BG_COLOR, dtype=np.uint8)
        self.overlay = self.image.copy()
        self.pen_color = (0, 0, 255)
        self.pen_color_name = '红'
        self.pen_width = 2
        self.history: List[np.ndarray] = []
        self.redo_stack: List[np.ndarray] = []
        self.max_history = 100
        self.last_command_type: Optional[type] = None
        self.last_command_params: Dict[str, str] = {}
        self.cursor_x = self.WIDTH // 2
        self.cursor_y = self.HEIGHT // 2
        self._freehand_mode = False
        self._freehand_points = []
        self._shape_count = 0
        self._cached_top_bar: Optional[np.ndarray] = None
        self._cached_bottom_bar: Optional[np.ndarray] = None
        self._cached_grid: Optional[np.ndarray] = None
        self._cached_glow: Optional[np.ndarray] = None

    def _cache_static_ui(self):
        if self._cached_top_bar is not None:
            return
        BAR_H = 34
        total_w = self.WIDTH
        total_h = self.HEIGHT + BAR_H * 2
        BAR_BG = (30, 25, 25)
        ACCENT_LINE = (50, 45, 45)

        self._cached_top_bar = np.full((BAR_H, total_w, 3), BAR_BG, dtype=np.uint8)
        cv2.line(self._cached_top_bar, (0, BAR_H - 1), (total_w, BAR_H - 1), ACCENT_LINE, 1)
        put_chinese_text(self._cached_top_bar, "语音绘图", (14, 14), 16, (245, 240, 240))
        for sep_x in (130, 380, 480, total_w - 200):
            cv2.line(self._cached_top_bar, (sep_x, 8), (sep_x, BAR_H - 8), ACCENT_LINE, 1)

        self._cached_bottom_bar = np.full((BAR_H, total_w, 3), BAR_BG, dtype=np.uint8)
        cv2.line(self._cached_bottom_bar, (0, 0), (total_w, 0), ACCENT_LINE, 1)
        stats_x = total_w - 310
        cv2.line(self._cached_bottom_bar, (stats_x - 8, 6), (stats_x - 8, BAR_H - 6), ACCENT_LINE, 1)
        hint_x = total_w - 160
        cv2.line(self._cached_bottom_bar, (hint_x - 8, 6), (hint_x - 8, BAR_H - 6), ACCENT_LINE, 1)
        put_chinese_text(self._cached_bottom_bar, "输入指令", (hint_x + 4, 14), 11, (135, 125, 120))

        grid = np.zeros((self.HEIGHT, total_w, 3), dtype=np.uint8)
        grid_col = (237, 240, 242)
        for row in range(1, 6):
            gy = row * (self.HEIGHT // 5)
            cv2.line(grid, (0, gy), (total_w, gy), grid_col, 1)
        for col in range(1, 6):
            gx = col * (self.WIDTH // 5)
            cv2.line(grid, (gx, 0), (gx, self.HEIGHT), grid_col, 1)
        dot_col = (220, 222, 225)
        for row in range(1, 6):
            gy = row * (self.HEIGHT // 5)
            for col in range(1, 6):
                gx = col * (self.WIDTH // 5)
                cv2.circle(grid, (gx, gy), 2, dot_col, -1, cv2.LINE_AA)
        label_col = (180, 180, 185)
        for x_val in range(0, self.WIDTH + 1, 200):
            put_chinese_text(grid, str(x_val), (x_val + 2, self.HEIGHT - 4), 9, label_col)
        for y_val in range(0, self.HEIGHT + 1, 100):
            if y_val == 0:
                continue
            put_chinese_text(grid, str(y_val), (2, y_val + 10), 9, label_col)
        zone_col = (200, 200, 205)
        for (px, py), label in {
            (0, 0): "左上", (total_w // 2, 0): "上中", (total_w - 40, 0): "右上",
            (0, self.HEIGHT // 2): "左中", (total_w // 2 - 10, self.HEIGHT // 2): "正中",
            (total_w - 40, self.HEIGHT // 2): "右中",
            (0, self.HEIGHT - 20): "左下", (total_w // 2 - 10, self.HEIGHT - 20): "下中",
            (total_w - 40, self.HEIGHT - 20): "右下",
        }.items():
            put_chinese_text(grid, label, (px + 5, py + 5), 11, zone_col)
        cv2.rectangle(grid, (1, 1), (total_w - 2, self.HEIGHT - 2), (215, 218, 222), 1)
        self._cached_grid = grid

    def _save_state(self):
        self.history.append(self.image.copy())
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.redo_stack.clear()

    def draw_circle(self, x, y, radius, color=None, width=2):
        self._save_state()
        cv2.circle(self.image, (int(x), int(y)), int(radius),
                    color or self.pen_color, int(width), lineType=cv2.LINE_AA)

    def draw_ellipse(self, x, y, rx, ry, color=None, width=2):
        self._save_state()
        center = (int(x), int(y))
        axes = (int(rx), int(ry))
        cv2.ellipse(self.image, center, axes, 0, 0, 360,
                     color or self.pen_color, int(width), lineType=cv2.LINE_AA)

    def draw_line(self, x1, y1, x2, y2, color=None, width=2):
        self._save_state()
        cv2.line(self.image, (int(x1), int(y1)), (int(x2), int(y2)),
                  color or self.pen_color, int(width), lineType=cv2.LINE_AA)

    def draw_rectangle(self, x1, y1, x2, y2, color=None, width=2, filled=False):
        self._save_state()
        thickness = -1 if filled else int(width)
        color_val = color or self.pen_color
        if filled and color_val == self.BG_COLOR:
            color_val = (200, 200, 200)
        cv2.rectangle(self.image, (int(x1), int(y1)), (int(x2), int(y2)),
                       color_val, thickness, lineType=cv2.LINE_AA)

    def draw_polygon(self, pts: List[int], color=None, width=2, filled=False):
        if len(pts) < 4 or len(pts) % 2 != 0:
            return
        self._save_state()
        self._draw_polygon_impl(pts, color=color, width=width, filled=filled)

    def draw_star(self, cx, cy, r, points=5, color=None, width=2):
        self._save_state()
        pts = []
        for i in range(points * 2):
            angle = math.pi / 2 + math.pi * i / points
            radius = r if i % 2 == 0 else r * 0.4
            pts.append(int(cx + radius * math.cos(angle)))
            pts.append(int(cy - radius * math.sin(angle)))
        self._draw_polygon_impl(pts, color=color, width=width)

    def _draw_polygon_impl(self, pts, color=None, width=2, filled=False):
        if len(pts) < 4 or len(pts) % 2 != 0:
            return
        points = np.array([[pts[i], pts[i + 1]] for i in range(0, len(pts), 2)], np.int32)
        points = points.reshape((-1, 1, 2))
        thickness = -1 if filled else int(width)
        cv2.polylines(self.image, [points], True,
                       color or self.pen_color, abs(thickness), lineType=cv2.LINE_AA)
        if filled:
            cv2.fillPoly(self.image, [points], color or self.pen_color, lineType=cv2.LINE_AA)

    def draw_text(self, x, y, text, size=1, color=None):
        self._save_state()
        color_val = color or self.pen_color
        font_size = max(16, int(float(size) * 20))
        put_chinese_text(self.image, text, (int(x), int(y)), font_size, color_val)

    def draw_regular_polygon(self, cx, cy, r, sides, color=None, width=2, filled=False, rotation=0):
        self._save_state()
        pts = []
        for i in range(sides):
            angle = rotation + 2 * math.pi * i / sides
            pts.append(int(cx + r * math.cos(angle)))
            pts.append(int(cy + r * math.sin(angle)))
        self._draw_polygon_impl(pts, color=color, width=width, filled=filled)

    def draw_ring(self, cx, cy, r_outer, r_inner, color=None, width=2):
        self._save_state()
        color_val = color or self.pen_color
        cv2.circle(self.image, (int(cx), int(cy)), int(r_outer), color_val, int(width), cv2.LINE_AA)
        cv2.circle(self.image, (int(cx), int(cy)), int(r_inner), color_val, int(width), cv2.LINE_AA)

    def draw_arc(self, cx, cy, r, start_angle, end_angle, color=None, width=2):
        self._save_state()
        color_val = color or self.pen_color
        cv2.ellipse(self.image, (int(cx), int(cy)), (int(r), int(r)),
                     0, int(start_angle), int(end_angle), color_val, int(width), cv2.LINE_AA)

    def draw_freehand(self, points, color=None, width=2):
        """Draw connected lines through a list of (x, y) points."""
        if len(points) < 2:
            return
        self._save_state()
        color_val = color or self.pen_color
        width_val = int(width)
        for i in range(1, len(points)):
            cv2.line(self.image,
                     (int(points[i-1][0]), int(points[i-1][1])),
                     (int(points[i][0]), int(points[i][1])),
                     color_val, width_val, cv2.LINE_AA)

    def draw_arrow_line(self, x1, y1, x2, y2, color=None, width=2):
        self._save_state()
        color_val = color or self.pen_color
        cv2.line(self.image, (int(x1), int(y1)), (int(x2), int(y2)),
                  color_val, int(width), lineType=cv2.LINE_AA)
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = max(10, int(width) * 5)
        for sign in (1, -1):
            px = int(x2 - arrow_len * math.cos(angle + sign * math.pi / 6))
            py = int(y2 - arrow_len * math.sin(angle + sign * math.pi / 6))
            cv2.line(self.image, (int(x2), int(y2)), (px, py),
                      color_val, int(width), lineType=cv2.LINE_AA)

    def draw_rounded_rect(self, x1, y1, x2, y2, r=20, color=None, width=2, filled=False):
        self._save_state()
        color_val = color or self.pen_color
        ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
        r = int(r)
        # Clamp radius to half the shorter side
        r = min(r, (ix2 - ix1) // 2, (iy2 - iy1) // 2)
        if r < 1:
            cv2.rectangle(self.image, (ix1, iy1), (ix2, iy2),
                           color_val, -1 if filled else int(width), lineType=cv2.LINE_AA)
            return
        if filled:
            pts = np.array([
                [ix1 + r, iy1], [ix2 - r, iy1],
                [ix2, iy1], [ix2, iy1 + r],
                [ix2, iy2 - r], [ix2, iy2],
                [ix2 - r, iy2], [ix1 + r, iy2],
                [ix1, iy2], [ix1, iy2 - r],
                [ix1, iy1 + r], [ix1, iy1],
            ], dtype=np.int32)
            cv2.fillPoly(self.image, [pts], color_val, lineType=cv2.LINE_AA)
            # Fill corner arcs
            cv2.ellipse(self.image, (ix1 + r, iy1 + r), (r, r), 0, 180, 270, color_val, -1, cv2.LINE_AA)
            cv2.ellipse(self.image, (ix2 - r, iy1 + r), (r, r), 0, 270, 360, color_val, -1, cv2.LINE_AA)
            cv2.ellipse(self.image, (ix1 + r, iy2 - r), (r, r), 0, 90, 180, color_val, -1, cv2.LINE_AA)
            cv2.ellipse(self.image, (ix2 - r, iy2 - r), (r, r), 0, 0, 90, color_val, -1, cv2.LINE_AA)
        else:
            thickness = int(width)
            # Top, bottom, left, right lines (between corner arcs)
            cv2.line(self.image, (ix1 + r, iy1), (ix2 - r, iy1), color_val, thickness, lineType=cv2.LINE_AA)
            cv2.line(self.image, (ix1 + r, iy2), (ix2 - r, iy2), color_val, thickness, lineType=cv2.LINE_AA)
            cv2.line(self.image, (ix1, iy1 + r), (ix1, iy2 - r), color_val, thickness, lineType=cv2.LINE_AA)
            cv2.line(self.image, (ix2, iy1 + r), (ix2, iy2 - r), color_val, thickness, lineType=cv2.LINE_AA)
            # Four corner arcs
            cv2.ellipse(self.image, (ix1 + r, iy1 + r), (r, r), 0, 180, 270, color_val, thickness, cv2.LINE_AA)
            cv2.ellipse(self.image, (ix2 - r, iy1 + r), (r, r), 0, 270, 360, color_val, thickness, cv2.LINE_AA)
            cv2.ellipse(self.image, (ix1 + r, iy2 - r), (r, r), 0, 90, 180, color_val, thickness, cv2.LINE_AA)
            cv2.ellipse(self.image, (ix2 - r, iy2 - r), (r, r), 0, 0, 90, color_val, thickness, cv2.LINE_AA)

    def set_background(self, color):
        self._save_state()
        self.image[:] = color

    def clear(self):
        self._save_state()
        self.image[:] = self.BG_COLOR
        self._shape_count = 0

    def undo(self) -> bool:
        if not self.history:
            return False
        self.redo_stack.append(self.image.copy())
        self.image = self.history.pop()
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.history.append(self.image.copy())
        self.image = self.redo_stack.pop()
        return True

    def save(self, filename: str):
        cv2.imwrite(filename, self.image)

    def _get_cursor_glow(self):
        if self._cached_glow is not None:
            return self._cached_glow
        w, h = 49, 49
        glow = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.circle(glow, (24, 24), 24, (255, 190, 130), -1, cv2.LINE_AA)
        self._cached_glow = glow
        return glow

    def get_preview(self, feedback_text: str = "", is_listening: bool = False,
                    cmd_count: int = 0, session_duration: float = 0.0) -> np.ndarray:
        self._cache_static_ui()
        BAR_H = 34
        total_h = self.HEIGHT + BAR_H * 2
        total_w = self.WIDTH
        BAR_TEXT = (245, 240, 240)
        BAR_TEXT_DIM = (135, 125, 120)
        ACCENT_BLUE = (255, 130, 60)
        v = np.full((total_h, total_w, 3), (240, 240, 240), dtype=np.uint8)

        v[:BAR_H, :] = self._cached_top_bar
        v[BAR_H:BAR_H + self.HEIGHT, :] = self.image
        v[-BAR_H:, :] = self._cached_bottom_bar

        if self._cached_grid is not None:
            canvas_roi = v[BAR_H:BAR_H + self.HEIGHT, :]
            mask = np.any(self._cached_grid > 0, axis=2)
            canvas_roi[mask] = self._cached_grid[mask]

        if is_listening:
            status_col = (50, 200, 80)
        elif feedback_text.startswith('⚠'):
            status_col = (60, 60, 220)
        else:
            status_col = ACCENT_BLUE
        cv2.rectangle(v, (0, 0), (total_w, 3), status_col, -1)

        y = 0
        last_speech = getattr(self, '_last_speech_text', '')
        if last_speech:
            put_chinese_text(v, f"🎤 {last_speech}"[:30], (138, 14), 13, (120, 200, 255))

        put_chinese_text(v, f"({int(self.cursor_x)},{int(self.cursor_y)})",
                        (388, 16), 12, BAR_TEXT_DIM)
        put_chinese_text(v, f"形状:{self._shape_count}", (488, 16), 12, BAR_TEXT_DIM)

        csx = total_w - 200
        sx = csx + 12
        cv2.rectangle(v, (sx, 8), (sx + 20, 26), self.pen_color, -1)
        cv2.rectangle(v, (sx, 8), (sx + 20, 26), (180, 180, 190), 1)
        if any('一' <= ch <= '鿿' for ch in str(self.pen_color_name)):
            put_chinese_text(v, self.pen_color_name, (sx + 28, 13), 14, BAR_TEXT)
        else:
            cv2.putText(v, self.pen_color_name, (sx + 28, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BAR_TEXT, 1, cv2.LINE_AA)
        cv2.putText(v, f"w:{self.pen_width}", (sx + 78, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BAR_TEXT_DIM, 1, cv2.LINE_AA)

        by = total_h - BAR_H
        dot_x, dot_cy = 18, by + BAR_H // 2
        if is_listening:
            cv2.circle(v, (dot_x, dot_cy), 7, (40, 180, 80), -1, cv2.LINE_AA)
            cv2.circle(v, (dot_x, dot_cy), 7, (80, 220, 110), 2, cv2.LINE_AA)
            put_chinese_text(v, "聆听中", (dot_x + 14, by + 14), 13, (100, 220, 130))
        else:
            cv2.circle(v, (dot_x, dot_cy), 4, BAR_TEXT_DIM, -1, cv2.LINE_AA)
            put_chinese_text(v, "待命", (dot_x + 14, by + 14), 13, BAR_TEXT_DIM)

        if feedback_text:
            fb = feedback_text[:60]
            fb_w = 8 + sum(18 if '一' <= ch <= '鿿' else 9 for ch in fb)
            if fb_w > total_w - 200:
                fb_w = total_w - 200
            fb_x, fb_y, fb_h = 100, by + 6, BAR_H - 12
            cv2.rectangle(v, (fb_x, fb_y), (fb_x + fb_w, fb_y + fb_h), (40, 35, 35), -1)
            cv2.rectangle(v, (fb_x, fb_y), (fb_x + fb_w, fb_y + fb_h), (50, 45, 45), 1)
            if feedback_text.startswith('⚠'):
                fb_col = (255, 140, 100); border_col = (200, 100, 80)
            elif feedback_text.startswith('↩'):
                fb_col = (140, 180, 255); border_col = (100, 140, 220)
            elif feedback_text.startswith('🎤'):
                fb_col = (80, 210, 110); border_col = (60, 180, 90)
            elif feedback_text.startswith('💡'):
                fb_col = (180, 220, 255); border_col = (140, 180, 220)
            else:
                fb_col = (230, 200, 100); border_col = (200, 170, 80)
            cv2.rectangle(v, (fb_x, fb_y), (fb_x + fb_w, fb_y + fb_h), border_col, 1)
            put_chinese_text(v, fb, (fb_x + 8, by + 14), 13, fb_col)

        dur = int(session_duration)
        mm, ss = divmod(dur, 60)
        hh, mm = divmod(mm, 60)
        dur_str = f"{hh}:{mm:02d}:{ss:02d}" if hh > 0 else f"{mm:02d}:{ss:02d}"
        stats_x = total_w - 310
        put_chinese_text(v, f"指令:{cmd_count}", (stats_x + 2, by + 14), 11, BAR_TEXT_DIM)
        put_chinese_text(v, f"时长:{dur_str}", (stats_x + 80, by + 14), 11, BAR_TEXT_DIM)

        cx, cy_ = int(self.cursor_x), int(self.cursor_y)
        canvas_cy = cy_ + BAR_H
        cur_col = (50, 45, 45)
        glow_r = 24
        glow = self._get_cursor_glow()
        x1g = max(0, cx - glow_r)
        y1g = max(0, canvas_cy - glow_r)
        x2g = min(total_w, cx + glow_r + 1)
        y2g = min(total_h, canvas_cy + glow_r + 1)
        if x2g > x1g and y2g > y1g:
            roi = v[y1g:y2g, x1g:x2g].copy()
            gx1 = cx - x1g
            gy1 = canvas_cy - y1g
            gx2 = gx1 + glow.shape[1]
            gy2 = gy1 + glow.shape[0]
            glow_roi = glow[max(0, -gx1):min(glow.shape[0], total_h - y1g),
                            max(0, -gy1):min(glow.shape[1], total_w - x1g)]
            mask_g = np.any(glow_roi > 0, axis=2)
            if mask_g.any():
                blended = cv2.addWeighted(roi, 0.75, 0, 0.25, 0)
                np.copyto(roi, blended, where=mask_g[..., None])
            v[y1g:y2g, x1g:x2g] = roi

        cur_len, gap = 25, 7
        sh_col = (210, 213, 218)
        cv2.line(v, (cx - cur_len + 1, canvas_cy + 1), (cx - gap + 1, canvas_cy + 1), sh_col, 1)
        cv2.line(v, (cx + gap + 1, canvas_cy + 1), (cx + cur_len + 1, canvas_cy + 1), sh_col, 1)
        cv2.line(v, (cx + 1, canvas_cy - cur_len + 1), (cx + 1, canvas_cy - gap + 1), sh_col, 1)
        cv2.line(v, (cx + 1, canvas_cy + gap + 1), (cx + 1, canvas_cy + cur_len + 1), sh_col, 1)
        cv2.line(v, (cx - cur_len, canvas_cy), (cx - gap, canvas_cy), cur_col, 2, cv2.LINE_AA)
        cv2.line(v, (cx + gap, canvas_cy), (cx + cur_len, canvas_cy), cur_col, 2, cv2.LINE_AA)
        cv2.line(v, (cx, canvas_cy - cur_len), (cx, canvas_cy - gap), cur_col, 2, cv2.LINE_AA)
        cv2.line(v, (cx, canvas_cy + gap), (cx, canvas_cy + cur_len), cur_col, 2, cv2.LINE_AA)
        cv2.circle(v, (cx, canvas_cy), 3, cur_col, -1, cv2.LINE_AA)
        cv2.circle(v, (cx, canvas_cy), 10, self.pen_color, 2, cv2.LINE_AA)
        put_chinese_text(v, f"({cx},{cy_})", (cx + 14, canvas_cy - 8), 10, cur_col)

        return v


_NOISE_PAT = re.compile(
    r'^(你[先好]|我[先不]|好[的吧]|嗯?[啊哦呃]?|哈[哈哈]?|[啊哦呃嗯]$|[你我来他她它]$|'
    r'一[个个]?|两[个个]?|这[个个]?|那[个个]?|什[么么]?|怎[么么]?|'
    r'哪[里儿]?|那[里儿]?|这[里儿]?|在[哪那]?|是[的吧]?|'
    r'然[后后]?|和[和和]?|还[有有]?|但[是是]?|就[是是]?)$'
)

# 绘图领域词汇提示（Whisper initial_prompt，引导模型偏向正确识别）
_DRAWING_PROMPT = (
    "画圆 画方形 画三角形 画五角星 画椭圆 画六边形 画菱形 画线 画圆环 "
    "画一个红色的圆 画一个蓝色的方 画一个绿色的三角 画一个黄色的星 "
    "在左上角 在正中间 在右下角 在上面 在下面 在左边 在右边 "
    "光标左移 光标右移 光标上移 光标下移 光标移到 撤销 重做 清空 保存 "
    "画房子 画树 画车 画太阳 画花 画笑脸 画流程图 "
    "填充 空心 粗一点 细一点 红色 蓝色 绿色 黄色 紫色 黑色 白色"
)


class SpeechRecognizer:
    """语音识别器，优先使用 faster-whisper（本地离线），备选 Google API。"""

    debug = '--debug' in sys.argv

    def __init__(self, language: str = "zh-CN"):
        self.language = language
        # speech_recognition (Google fallback)
        self._recognizer = None
        self._mic = None
        self._sr = None
        # faster-whisper (primary)
        self._whisper_model = None
        self._whisper_available = False
        # state
        self._use_real = False
        self._listen_count = 0
        self._base_energy = 200
        self._cooldown_until = 0.0
        # init engines
        self._init_whisper()
        self._init_google()

    # ------------------------------------------------------------------
    # Whisper 初始化
    # ------------------------------------------------------------------
    def _init_whisper(self):
        """初始化 faster-whisper 模型（本地离线，首次运行会自动下载模型）。"""
        try:
            from faster_whisper import WhisperModel
            # small 模型：~460MB，中文精度高，CPU 上约 2-5 秒
            self._whisper_model = WhisperModel(
                "small", device="auto", compute_type="int8"
            )
            self._whisper_available = True
            print("[语音] Whisper 引擎已加载 (small, 离线模式)")
        except Exception as e:
            print(f"[语音] Whisper 不可用: {e}")
            self._whisper_available = False

    # ------------------------------------------------------------------
    # Google 初始化（备选）
    # ------------------------------------------------------------------
    def _init_google(self):
        """初始化 Google Speech Recognition（需要网络，作为备选）。"""
        try:
            devnull = os.open(os.devnull, os.O_RDWR)
            old_stderr = os.dup(2)
            os.dup2(devnull, 2)
            try:
                import speech_recognition as sr
                self._sr = sr
                self._recognizer = sr.Recognizer()
                self._recognizer.pause_threshold = 0.8
                self._recognizer.energy_threshold = self._base_energy
                self._recognizer.dynamic_energy_threshold = True
                self._mic = sr.Microphone()
                with self._mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self._use_real = True
                if not self._whisper_available:
                    print("[语音] Google 引擎已加载 (需要网络)")
                else:
                    print("[语音] Google 引擎已加载 (备选)")
            except Exception:
                pass
            finally:
                os.dup2(old_stderr, 2)
                os.close(devnull)
                os.close(old_stderr)
        except Exception:
            pass

    def _recalibrate(self):
        if not self._use_real:
            return
        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
        except Exception:
            pass

    @staticmethod
    def _is_garbage(text: str) -> bool:
        if len(text) < 2:
            return True
        if len(text) <= 2 and _NOISE_PAT.match(text):
            return True
        if len(text) <= 3 and len(set(text)) == 1:
            return True
        if len(text) >= 4 and len(set(text)) <= 2:
            return True
        return False

    # ------------------------------------------------------------------
    # Whisper 文本后处理
    # ------------------------------------------------------------------
    @staticmethod
    def _dedup_whisper_text(text: str) -> str:
        """去重 Whisper 幻觉产生的重复短语。

        例: "画一角形 画一角形 画一角形 画一角形" → "画三角形"
        """
        import re

        # 1. 去除连续重复的子串（如 "画一个圆 画一个圆 画一个圆" → "画一个圆"）
        #    按空格分割，去除连续重复的 token 序列
        tokens = text.split()
        if len(tokens) > 3:
            # 尝试找到重复模式：前半部分重复
            half = len(tokens) // 2
            for size in range(1, half + 1):
                pattern = tokens[:size]
                repeats = len(tokens) // size
                if repeats >= 2 and tokens[:size * repeats] == pattern * repeats:
                    tokens = pattern
                    break
            text = ' '.join(tokens)

        # 2. 去除句内重复短语（不依赖空格，如 "画一角形画一角形"）
        #    尝试从长到短匹配重复子串
        for length in range(len(text) // 2, 2, -1):
            substr = text[:length]
            if substr * 2 in text:
                text = substr
                break

        # 3. Whisper 常见错误修正
        WHISPER_FIXES = {
            '再正中': '在正中', '再上中': '在上中', '再左上': '在左上',
            '再右上': '在右上', '再左下': '在左下', '再右下': '在右下',
            '再中间': '在中间', '再左边': '在左边', '再右边': '在右边',
            '画一角形': '画三角形', '画三角行': '画三角形',
            '画一个 画': '画一个圆', '画一 个圆': '画一个圆',
            '画一个圆': '画一个圆',  # 保持不变
        }
        for wrong, right in WHISPER_FIXES.items():
            text = text.replace(wrong, right)

        return text.strip()

    # ------------------------------------------------------------------
    # Whisper 转写
    # ------------------------------------------------------------------
    def _transcribe_whisper(self, audio_data: bytes, sample_rate: int) -> List[dict]:
        """用 Whisper 转写音频，返回 [{text, avg_logprob}, ...]。"""
        if not self._whisper_available or self._whisper_model is None:
            return []
        tmp_path = "/tmp/whisper_audio.wav"
        try:
            import wave
            import locale

            # 写入固定 ASCII 路径的临时文件
            with wave.open(tmp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)

            # 临时切换 locale 为 C，修复 PyAV 的 os.strerror() ASCII 解码 bug
            old_locale = locale.getlocale()
            try:
                locale.setlocale(locale.LC_ALL, 'C')
            except locale.Error:
                pass

            try:
                # Whisper 转写（small 模型，平衡精度和速度）
                segments, info = self._whisper_model.transcribe(
                    tmp_path,
                    language="zh",
                    initial_prompt=_DRAWING_PROMPT,
                    beam_size=5,           # 多 beam 提高精度
                    best_of=3,             # 生成 3 个候选取最佳
                    condition_on_previous_text=False,  # 防止幻觉级联
                    repetition_penalty=1.3,  # 抑制重复短语
                    no_repeat_ngram_size=3,  # 禁止 3-gram 重复
                    vad_filter=True,
                    vad_parameters=dict(
                        min_silence_duration_ms=200,
                        speech_pad_ms=100,
                    ),
                )
            finally:
                # 恢复原 locale
                try:
                    locale.setlocale(locale.LC_ALL, old_locale)
                except locale.Error:
                    pass

            results = []
            for seg in segments:
                text = seg.text.strip()
                if text:
                    # 后处理：去重重复短语（Whisper 幻觉修复）
                    text = self._dedup_whisper_text(text)
                    if text:
                        results.append({
                            "text": text,
                            "avg_logprob": seg.avg_logprob,
                            "no_speech_prob": seg.no_speech_prob,
                        })

            return results
        except Exception as e:
            import traceback
            if self.debug:
                print(f"[DEBUG Whisper] 错误: {e}")
                traceback.print_exc()
            return []
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Google 转写
    # ------------------------------------------------------------------
    def _get_transcripts_google(self, audio) -> List[str]:
        if self._sr is None:
            return []
        try:
            result = self._recognizer.recognize_google(
                audio, language=self.language, show_all=True
            )
        except self._sr.UnknownValueError:
            return []
        except self._sr.RequestError:
            return []
        except Exception:
            return []

        texts: List[str] = []
        if isinstance(result, dict) and 'alternative' in result:
            for i, alt in enumerate(result['alternative']):
                transcript = alt.get('transcript', '').strip()
                if transcript:
                    texts.append(transcript)
        elif isinstance(result, str) and result.strip():
            texts.append(result.strip())
        return texts

    # ------------------------------------------------------------------
    # 录音 + 识别主流程
    # ------------------------------------------------------------------
    def listen_with_alternatives(self) -> Optional[List[str]]:
        if not self._use_real or cv2 is None:
            return None

        now = time.time()
        if now < self._cooldown_until:
            time.sleep(self._cooldown_until - now)

        self._listen_count += 1

        devnull = os.open(os.devnull, os.O_RDWR)
        old_stderr = os.dup(2)
        os.dup2(devnull, 2)
        try:
            if self._listen_count % 3 == 0:
                self._recalibrate()
            self._recognizer.energy_threshold = max(
                self._recognizer.energy_threshold, self._base_energy
            )
            try:
                with self._mic as source:
                    audio = self._recognizer.listen(
                        source, timeout=5, phrase_time_limit=6
                    )
            except self._sr.WaitTimeoutError:
                return None
            except self._sr.UnknownValueError:
                return None
            except Exception:
                return None
        finally:
            os.dup2(old_stderr, 2)
            os.close(devnull)
            os.close(old_stderr)

        audio_len = len(audio.frame_data) / audio.sample_rate if hasattr(audio, 'frame_data') and hasattr(audio, 'sample_rate') else 0

        # 优先使用 Whisper
        if self._whisper_available:
            whisper_results = self._transcribe_whisper(
                audio.frame_data, audio.sample_rate
            )
            if whisper_results:
                # 置信度过滤：avg_logprob 越接近 0 越好，< -1.0 通常不可靠
                CONFIDENCE_THRESHOLD = -1.0
                texts = []
                for r in whisper_results:
                    logprob = r["avg_logprob"]
                    text = r["text"].strip()
                    if logprob < CONFIDENCE_THRESHOLD:
                        if self.debug:
                            print(f"  [低置信度] \"{text}\" (logprob={logprob:.2f})")
                        continue
                    texts.append(text)

                if texts:
                    clean = [t for t in texts if not self._is_garbage(t)]
                    if self.debug:
                        probs = [f"{r['avg_logprob']:.2f}" for r in whisper_results]
                        print(f"\n[DEBUG Whisper] logprobs={probs} /{audio_len:.1f}s")
                        for i, r in enumerate(whisper_results[:3]):
                            lp = r['avg_logprob']
                            print(f"  [{i}] \"{r['text']}\" (logprob={lp:.2f})")
                    if clean:
                        return clean
                    # 如果全被过滤为垃圾，继续尝试 Google

        # 备选：Google API
        texts = self._get_transcripts_google(audio)
        if texts:
            garbage = [t for t in texts if self._is_garbage(t)]
            clean = [t for t in texts if not self._is_garbage(t)]
            if self.debug:
                print(f"\n[DEBUG Google] energy={int(self._recognizer.energy_threshold)} "
                      f"alternatives={len(texts)} /{audio_len:.1f}s")
                for i, t in enumerate(texts[:5]):
                    tag = " GARBAGE" if t in garbage else ""
                    print(f"  [{i}] \"{t}\"{tag}")
            if not clean:
                return None
            return clean
        return None

    def listen(self) -> Optional[str]:
        texts = self.listen_with_alternatives()
        if not texts:
            return None
        best = texts[0].strip().rstrip('。，！？；：,.!?;:')
        return best if len(best) >= 1 else None


HELP_TEXT = """🎤 语音绘图快速指南

【基础形状】
  画圆 / 画正方形 / 画长方形 / 画三角形 / 画五角星
  画椭圆 / 画六边形 / 画菱形 / 画线 / 画圆环

【指定颜色】
  红圆 / 蓝方 / 绿三角 / 黄星 / 紫圆环

【指定位置】(直接说在形状指令里)
  左上角 / 上中 / 右上角 / 左中 / 正中间 / 右中
  左下角 / 下中 / 右下角

【网格定位】
  A1~E5 (如 "画红圆在B3")

【方向偏移】
  画红圆往右 / 往上画蓝圆 / 右上角偏下画黄圆

【多个图形】
  红圆和蓝方 / 画红圆然后画绿圆在左边

【场景模板】
  画房子 / 画树 / 画车 / 画太阳 / 画小花

【⭐ 场景描述】(一次性画完)
  画一幅画：左边一棵树，右边一座山，上面有太阳
  场景：中间一个红圆，左边一个蓝方
  画一幅画：大圆，小方，三角

【样式】
  填充 / 空心 / 粗一点 / 细一点

【操作】
  撤销 / 重做 / 清空 / 保存 / 退出

💡 提示: 直接说 "帮助" 随时查看此指南"""


class VoiceDrawingApp:
    WINDOW_NAME = "Voice Drawing Tool"

    def __init__(self, use_speech: bool = False, gui: Optional[bool] = None):
        self.canvas = DrawingCanvas()
        self.parser = CommandParser()
        self.recognizer = SpeechRecognizer() if use_speech else None
        self.use_speech = use_speech
        self.gui = _HAS_GUI if gui is None else (gui and _HAS_GUI)
        self.feedback_text = ""
        self.feedback_expire = 0
        self.cmd_queue: queue.Queue = queue.Queue()
        self.running = False
        self._idle_count = 0
        self._unrecognized_count = 0
        self._is_listening = False
        self._last_speech_text = ""
        self._last_command_text = ""
        self._feedback_history: List[str] = []
        self._show_welcome = True
        self._welcome_expire = time.time() + 15.0  # Show welcome for 15 seconds
        self._show_help = False
        self._pending_confirm = None
        self._pending_confirm_time = 0.0
        self._pending_speech_cmd = None  # 待确认的语音命令
        self._cmd_count = 0
        self._session_start = time.time()
        self.debug = '--debug' in sys.argv

    def run(self):
        if self.use_speech:
            threading.Thread(target=self._speech_loop, daemon=True).start()
        threading.Thread(target=self._stdin_loop, daemon=True).start()
        print("[输入] 键盘输入已启用，可直接在终端输入指令")

        if self.gui:
            cv2.namedWindow(self.WINDOW_NAME)
            cv2.setMouseCallback(self.WINDOW_NAME, self._on_mouse)
            print("[GUI] 绘图窗口已创建")
            print("\n" + "="*60)
            print("  🎤 语音绘图工具已启动!")
            print("="*60)
            print("  📝 直接在终端输入指令（回车执行）")
            print("  🎤 说完指令后，按回车确认或输入修正")
            print("  ❓ 输入 '帮助' 查看所有指令")
            print("  🚪 输入 '退出' 结束程序")
            print("="*60)
            print("  示例: 画一个红圆 / 画房子 / 画一幅画：左边树右边山")
            print("="*60 + "\n")

        while self.running:
            # Reset pending confirmation on timeout
            if self._pending_confirm and time.time() - self._pending_confirm_time >= 5.0:
                self._pending_confirm = None
                self._pending_confirm_time = 0.0
            self._process_queue()
            if self.gui:
                img = self.canvas.get_preview(
                    self._get_feedback(),
                    is_listening=self._is_listening,
                    cmd_count=self._cmd_count,
                    session_duration=time.time() - self._session_start,
                )
                
                # Show welcome overlay for first 15 seconds
                if self._show_welcome:
                    if time.time() < self._welcome_expire:
                        self._draw_welcome_overlay(img)
                    else:
                        self._show_welcome = False

                # Show help overlay when requested
                if self._show_help:
                    self._draw_help_overlay(img)

                # Show clear confirmation overlay
                if self._pending_confirm == "清空" and time.time() - self._pending_confirm_time < 5.0:
                    self._draw_clear_confirm_overlay(img)
                elif self._pending_confirm == "清空":
                    self._pending_confirm = None
                    self._set_feedback("⚠ 清空已取消")

                cv2.imshow(self.WINDOW_NAME, img)
                key = cv2.waitKey(100)
                if key != -1:
                    self._show_welcome = False
                    self._show_help = False
            else:
                time.sleep(0.1)

        if self.gui:
            cv2.destroyAllWindows()

    def _draw_welcome_overlay(self, img):
        """Draw welcome guide overlay on the canvas."""
        h, w = img.shape[:2]

        # Semi-transparent overlay
        overlay = img.copy()
        cv2.rectangle(overlay, (50, 100), (w-50, h-100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)

        # Welcome text
        y = 150
        put_chinese_text(img, "🎤 语音绘图快速指南", (100, y), 28, (255, 255, 255))

        y += 50
        guides = [
            "直接说出指令即可绘图",
            "",
            "基础形状: 画圆 / 画方 / 画三角形 / 画五角星",
            "指定颜色: 红圆 / 蓝方 / 绿三角",
            "指定位置: 左上角 / 正中间 / 右下角",
            "网格定位: 画红圆在B3",
            "场景: 画房子 / 画树 / 画车 / 画小花",
            "操作: 撤销 / 重做 / 清空 / 保存",
            "",
            "说 '帮助' 查看所有指令",
            "说 '退出' 结束程序",
        ]

        for line in guides:
            if line == "":
                y += 20
                continue
            put_chinese_text(img, line, (120, y), 18, (200, 200, 200))
            y += 30

        # Countdown
        remaining = int(self._welcome_expire - time.time())
        if remaining > 0:
            put_chinese_text(img, f"此指南将在 {remaining} 秒后消失...",
                           (w//2 - 150, h - 120), 14, (150, 150, 150))

        put_chinese_text(img, "按任意键或说出指令关闭此指南",
                        (w//2 - 180, h - 90), 14, (150, 150, 150))

    def _draw_help_overlay(self, img):
        """Draw help overlay on the canvas."""
        h, w = img.shape[:2]

        # Semi-transparent overlay
        overlay = img.copy()
        cv2.rectangle(overlay, (30, 50), (w - 30, h - 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

        y = 80
        for line in HELP_TEXT.splitlines():
            if line == "":
                y += 16
                continue
            # Headers in brighter color
            if line.startswith("【") or line.startswith("🎤"):
                put_chinese_text(img, line, (60, y), 20, (255, 255, 255))
            elif line.startswith("💡"):
                put_chinese_text(img, line, (60, y), 16, (180, 220, 255))
            else:
                put_chinese_text(img, line, (60, y), 16, (190, 190, 195))
            y += 26
            if y > h - 80:
                break

        put_chinese_text(img, "按任意键或说出指令关闭帮助",
                        (w // 2 - 170, h - 70), 14, (150, 150, 150))

    def _draw_clear_confirm_overlay(self, img):
        """Draw clear confirmation overlay on the canvas."""
        h, w = img.shape[:2]
        overlay = img.copy()
        cv2.rectangle(overlay, (w // 2 - 220, h // 2 - 50), (w // 2 + 220, h // 2 + 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
        remaining = int(5.0 - (time.time() - self._pending_confirm_time))
        put_chinese_text(img, f"说'确认'清空画布 ({remaining}秒)",
                        (w // 2 - 200, h // 2 + 5), 22, (100, 180, 255))

    def _on_mouse(self, event, x, y, flags, param):
        """Handle mouse events for freehand drawing mode."""
        if not self.canvas._freehand_mode:
            return
        BAR_H = 34
        canvas_x = x
        canvas_y = y - BAR_H
        if canvas_x < 0 or canvas_x >= self.canvas.WIDTH or canvas_y < 0 or canvas_y >= self.canvas.HEIGHT:
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            self.canvas._save_state()
            self.canvas._freehand_points = [(canvas_x, canvas_y)]
        elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):
            if self.canvas._freehand_points:
                self.canvas._freehand_points.append((canvas_x, canvas_y))
                prev = self.canvas._freehand_points[-2]
                cv2.line(self.canvas.image, prev, (canvas_x, canvas_y),
                         self.canvas.pen_color, self.canvas.pen_width, cv2.LINE_AA)
        elif event == cv2.EVENT_LBUTTONUP:
            if self.canvas._freehand_points:
                self.canvas._shape_count += 1
            self.canvas._freehand_points = []

    def _speech_loop(self):
        while self.running:
            if not self.recognizer:
                time.sleep(0.1)
                continue

            self._is_listening = True
            texts = self.recognizer.listen_with_alternatives()
            self._is_listening = False
            if texts:
                if self._idle_count > 0:
                    print()
                    self._idle_count = 0
                best = texts[0].strip().rstrip('。，！？；：,.!?;:')
                self._last_speech_text = best
                print(f"\n[语音识别] \"{best}\"", end="")
                if len(texts) > 1:
                    shown = [t for t in texts[1:4] if t != best][:2]
                    if shown:
                        print(f" (备选: {' | '.join(shown)})", end="")
                print()
                chosen = self._pick_best_transcript(texts)
                if chosen:
                    # 语音识别后等待确认，用户可以直接回车确认或输入修正
                    print(f"[预览] 将执行: \"{chosen}\"")
                    print(f"[预览] 按回车确认，或输入修正指令：", end="", flush=True)
                    # 不直接放入队列，等待用户确认
                    self._pending_speech_cmd = chosen
                    self.recognizer._cooldown_until = time.time() + 0.4
            else:
                self._idle_count += 1
                if self._idle_count == 1:
                    print("[等待语音指令...]", end="", flush=True)
                elif self._idle_count % 5 == 0:
                    print(".", end="", flush=True)
                if self._idle_count >= 20:
                    print("\n[提示: 说话前无需按键，直接说出指令即可]", flush=True)
                    self._idle_count = 0
                time.sleep(0.5)

    def _stdin_loop(self):
        """Read lines from stdin and put them into the command queue."""
        self._pending_speech_cmd = None
        while self.running:
            try:
                line = sys.stdin.readline()
                if line:
                    stripped = line.strip()
                    if stripped:
                        # 如果有待确认的语音命令
                        if self._pending_speech_cmd:
                            if stripped == '' or stripped == '确认' or stripped == 'y':
                                # 确认执行
                                self.cmd_queue.put(self._pending_speech_cmd)
                                print(f"[确认] 执行: \"{self._pending_speech_cmd}\"")
                            else:
                                # 用用户输入的修正指令
                                self.cmd_queue.put(stripped)
                                print(f"[修正] 执行: \"{stripped}\"")
                            self._pending_speech_cmd = None
                        else:
                            self.cmd_queue.put(stripped)
                    else:
                        # 空行 = 确认待执行的语音命令
                        if self._pending_speech_cmd:
                            self.cmd_queue.put(self._pending_speech_cmd)
                            print(f"[确认] 执行: \"{self._pending_speech_cmd}\"")
                            self._pending_speech_cmd = None
            except (EOFError, OSError):
                break

    def _pick_best_transcript(self, texts: List[str]) -> Optional[str]:
        for t in texts:
            cleaned = t.strip().rstrip('。，！？；：,.!?;:')
            if not cleaned:
                continue
            cmd = self.parser.parse_command(cleaned,
                                            self.canvas.cursor_x,
                                            self.canvas.cursor_y)
            if cmd is not None:
                return cleaned
        return None

    _REPEAT_PAT = re.compile(r'再[画来][一一个]个?|再来[一一个]?遍?|重复[一一个]?[下遍次]?|同样的|再来')

    def _check_confirm(self, action: str) -> bool:
        """Check if a destructive action is confirmed. Returns True if should proceed."""
        now = time.time()
        if self._pending_confirm == action and now - self._pending_confirm_time < 5.0:
            self._pending_confirm = None
            self._pending_confirm_time = 0.0
            return True
        self._pending_confirm = action
        self._pending_confirm_time = now
        self._set_feedback(f"⚠ 再说一次'{action}'确认 (5秒内)")
        return False

    def _process_queue(self):
        import queue as q
        while True:
            try:
                text = self.cmd_queue.get_nowait()
            except q.Empty:
                break
            if text.lower() in ("exit", "quit", "退出"):
                if self._check_confirm("退出"):
                    print("[语音] 退出")
                    self.running = False
                    break
                continue
            if text.lower() in ("help", "帮助"):
                self._show_help = True
                self._set_feedback("🎤 帮助指南已显示")
                continue
            if text.strip().rstrip('。，！？；：,.!?;:') in ("不对", "不是", "错了", "取消", "不要", "不"):
                print("[取消] 撤销上一步")
                self.canvas.undo()
                self._set_feedback("↩ 已撤销")
                continue
            self._last_speech_text = text
            # Close overlays on any command
            self._show_welcome = False
            self._show_help = False
            self.execute_command(text)

    def execute_command(self, text: str):
        if self._REPEAT_PAT.match(text) and self._last_command_text:
            print(f"[重复] \"{self._last_command_text}\"")
            text = self._last_command_text
        cmd = self.parser.parse_command(text, self.canvas.cursor_x, self.canvas.cursor_y)
        if cmd is None:
            from .commands import zh_to_en, fix_speech_text
            fixed = fix_speech_text(text)
            en = zh_to_en(fixed)
            print(f"[未识别] \"{text}\"")
            if fixed != text:
                print(f"  → 纠错: {fixed}")
            print(f"  → 翻译: {en}")
            
            # Provide helpful suggestions based on common mistakes
            suggestion = self._get_suggestion(text)
            if suggestion:
                self._set_feedback(f"⚠ {text[:40]} → 未识别. {suggestion}", is_error=True)
            else:
                self._set_feedback(f"⚠ {text[:32]} → 未识别", is_error=True)
            
            self._unrecognized_count += 1
            if self._unrecognized_count >= 3:
                msg = "试试简单指令: 红圆 / 画房子 / 撤销 / 帮助"
                print(f"  → 提示: {msg}")
                self._set_feedback(f"💡 {msg}", is_error=True)
            return
        self._unrecognized_count = 0
        self._last_command_text = text
        # Confirmation for destructive commands
        from .commands import ClearCanvasCommand, UndoCommand, ConfirmCommand, DrawFreehandCommand, RepeatLastWithVariationCommand
        if isinstance(cmd, ClearCanvasCommand):
            now = time.time()
            if self._pending_confirm == "清空" and now - self._pending_confirm_time < 5.0:
                self._pending_confirm = None
                self._pending_confirm_time = 0.0
            else:
                self._pending_confirm = "清空"
                self._pending_confirm_time = now
                self._set_feedback("⚠ 说'确认'清空画布 (5秒内)")
                return
        elif isinstance(cmd, UndoCommand):
            if not self._check_confirm("撤销"):
                return
        elif isinstance(cmd, ConfirmCommand):
            if self._pending_confirm == "清空" and time.time() - self._pending_confirm_time < 5.0:
                self._pending_confirm = None
                self._pending_confirm_time = 0.0
                self.canvas.clear()
                self._cmd_count += 1
                cv2.imwrite('/tmp/voice_drawing_autosave.png', self.canvas.image)
                self._set_feedback("🎤 确认 → 画布已清空")
                return
        result = cmd.execute(self.canvas)
        self._cmd_count += 1
        print(f"[执行] {result}")
        cv2.imwrite('/tmp/voice_drawing_autosave.png', self.canvas.image)
        self._set_feedback(f"🎤 {self._last_speech_text[:40]} → {result}")
        from .commands import (MoveLastCommand, ScaleLastCommand, ConfirmCommand,
                               ClearCanvasCommand, UndoCommand, RedoCommand,
                               SetColorCommand, SetWidthCommand, SetBackgroundCommand,
                               CompositeCommand, MoveCursorCommand, SetCursorCommand,
                               DrawFreehandCommand, RepeatLastWithVariationCommand)
        if isinstance(cmd, CompositeCommand):
            self.canvas.last_command_type = CompositeCommand
            self.canvas.last_command_params = {
                'sub_commands': [(type(sub), getattr(sub, 'params', {})) for sub in cmd.commands],
            }
            # Update cursor to center of last sub-command
            if cmd.commands:
                last = cmd.commands[-1]
                for attr in ('x', 'cx', 'x1'):
                    if hasattr(last, attr):
                        self.canvas.cursor_x = getattr(last, attr)
                        break
                for attr in ('y', 'cy', 'y1'):
                    if hasattr(last, attr):
                        self.canvas.cursor_y = getattr(last, attr)
                        break
        elif isinstance(cmd, MoveCursorCommand):
            self.canvas.cursor_x += cmd.dx
            self.canvas.cursor_y += cmd.dy
            self.canvas.cursor_x = max(0, min(799, self.canvas.cursor_x))
            self.canvas.cursor_y = max(0, min(599, self.canvas.cursor_y))
        elif isinstance(cmd, SetCursorCommand):
            self.canvas.cursor_x = max(0, min(799, cmd.x))
            self.canvas.cursor_y = max(0, min(599, cmd.y))
        elif not isinstance(cmd, (MoveLastCommand, ScaleLastCommand, ConfirmCommand,
                                  ClearCanvasCommand, UndoCommand, RedoCommand,
                                  SetColorCommand, SetWidthCommand, SetBackgroundCommand,
                                  MoveCursorCommand, SetCursorCommand,
                                  DrawFreehandCommand, RepeatLastWithVariationCommand)):
            self.canvas.last_command_type = type(cmd)
            self.canvas.last_command_params = getattr(cmd, 'params', {})
            self.canvas._shape_count += 1
            # Update cursor to where the shape was drawn
            for attr in ('x', 'cx', 'x1'):
                if hasattr(cmd, attr):
                    self.canvas.cursor_x = getattr(cmd, attr)
                    break
            for attr in ('y', 'cy', 'y1'):
                if hasattr(cmd, attr):
                    self.canvas.cursor_y = getattr(cmd, attr)
                    break

    def feed_command(self, text: str):
        self.cmd_queue.put(text)

    def _set_feedback(self, text: str, is_error: bool = False):
        self.feedback_text = text
        self.feedback_expire = time.time() + 6.0
        self._feedback_history.append(('!' if is_error else ' ', text[:60]))
        if len(self._feedback_history) > 5:
            self._feedback_history.pop(0)

    def _get_feedback(self) -> str:
        if self.feedback_text and time.time() < self.feedback_expire:
            return self.feedback_text
        if self._feedback_history:
            return self._feedback_history[-1][1]
        return ""

    def _get_suggestion(self, text: str) -> str:
        """Provide helpful suggestions for unrecognized commands."""
        text_lower = text.lower().strip()
        
        # Common shape keywords and their suggestions
        shape_suggestions = {
            '圆': '试试: 画圆 / 红圆 / 画一个圆',
            '圈': '试试: 画圆 / 画圆环',
            '方': '试试: 画正方形 / 画长方形',
            '正方': '试试: 画正方形',
            '长方': '试试: 画长方形',
            '矩': '试试: 画长方形 / 画矩形',
            '三': '试试: 画三角形',
            '星': '试试: 画五角星 / 画星',
            '五角': '试试: 画五角星',
            '线': '试试: 画线 / 画直线',
            '直': '试试: 画直线',
            '椭': '试试: 画椭圆',
            '菱': '试试: 画菱形',
            '六': '试试: 画六边形',
            '环': '试试: 画圆环',
            '房': '试试: 画房子',
            '屋': '试试: 画房子',
            '树': '试试: 画树',
            '车': '试试: 画车',
            '花': '试试: 画小花',
            '太阳': '试试: 画太阳',
            '山': '试试: 画山',
            '红': '试试: 红圆 / 红方',
            '蓝': '试试: 蓝圆 / 蓝方',
            '绿': '试试: 绿圆 / 绿方',
            '黄': '试试: 黄圆 / 黄方',
            '紫': '试试: 紫圆 / 紫方',
            '上': '试试: 往上画圆 / 上面画圆',
            '下': '试试: 往下画圆 / 下面画圆',
            '左': '试试: 往左画圆 / 左边画圆',
            '右': '试试: 往右画圆 / 右边画圆',
            '中间': '试试: 正中间画圆 / 中间画圆',
            '撤销': '试试: 撤销',
            '回退': '试试: 撤销',
            '重做': '试试: 重做',
            '清空': '试试: 清空',
            '清除': '试试: 清空',
            '保存': '试试: 保存',
            '帮助': '试试: 帮助',
            '退出': '试试: 退出',
        }
        
        # Check for common keywords
        for keyword, suggestion in shape_suggestions.items():
            if keyword in text:
                return suggestion
        
        # Check for common prefixes
        if text_lower.startswith('画'):
            return '试试: 画圆 / 画方 / 画三角形 / 画房子'
        
        return ""
