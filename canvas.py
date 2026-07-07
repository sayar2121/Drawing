"""
Canvas Engine
=============
Rich drawing canvas with undo/redo, shape tools, mirror mode,
and a modern floating palette with glassmorphism styling.
"""

import cv2
import numpy as np
from datetime import datetime
import math


# ── Color Palette — curated vibrant palette ───────────────────────────────────
COLORS = {
    "Rose":       (90,  60,  235),
    "Coral":      (80,  120, 255),
    "Tangerine":  (40,  160, 255),
    "Gold":       (50,  215, 255),
    "Lime":       (100, 230, 160),
    "Mint":       (180, 220, 120),
    "Aqua":       (210, 210, 60),
    "Sky":        (230, 175, 80),
    "Lavender":   (220, 130, 200),
    "Magenta":    (180, 50,  230),
    "White":      (235, 235, 235),
    "Silver":     (150, 150, 150),
}
COLOR_NAMES = list(COLORS.keys())
ERASER_COLOR = (0, 0, 0)
ERASER_RADIUS = 28

# Shape tool constants
SHAPE_FREEHAND  = 0
SHAPE_LINE      = 1
SHAPE_RECTANGLE = 2
SHAPE_CIRCLE    = 3
SHAPE_NAMES     = {0: "Freehand", 1: "Line", 2: "Rect", 3: "Circle"}


class Canvas:
    """Transparent drawing canvas with undo/redo, shapes, mirror mode."""

    # Palette layout — bigger, easier to hit
    PALETTE_TOP      = 8
    PALETTE_SWATCH_W = 38
    PALETTE_SWATCH_H = 38
    PALETTE_MARGIN   = 5
    PALETTE_PADDING  = 8  # extra padding around the palette bar

    MAX_UNDO = 25

    def __init__(self, width, height):
        self.w = width
        self.h = height
        self._canvas     = np.zeros((height, width, 3), dtype=np.uint8)
        self.color       = COLORS["Aqua"]
        self.color_name  = "Aqua"
        self.brush_size  = 5
        self.eraser_mode = False
        self.mirror_mode = False
        self.shape_tool  = SHAPE_FREEHAND
        self._prev_point = None

        # Undo / redo
        self._undo_stack = []
        self._redo_stack = []
        self._stroke_active = False

        # Shape state
        self._shape_start    = None
        self._shape_canvas   = None
        self._shape_dragging = False

        # Pre-compute palette bounds for hit testing
        self._palette_bounds = []
        for i, name in enumerate(COLOR_NAMES):
            sx = self.PALETTE_PADDING + i * (self.PALETTE_SWATCH_W + self.PALETTE_MARGIN)
            ex = sx + self.PALETTE_SWATCH_W
            self._palette_bounds.append((sx, self.PALETTE_TOP,
                                         ex, self.PALETTE_TOP + self.PALETTE_SWATCH_H))
        # Eraser swatch bounds
        er_x = self.PALETTE_PADDING + len(COLOR_NAMES) * (self.PALETTE_SWATCH_W + self.PALETTE_MARGIN)
        self._eraser_bounds = (er_x, self.PALETTE_TOP,
                               er_x + self.PALETTE_SWATCH_W,
                               self.PALETTE_TOP + self.PALETTE_SWATCH_H)

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    def _push_undo(self):
        self._undo_stack.append(self._canvas.copy())
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._canvas.copy())
        self._canvas = self._undo_stack.pop()
        self._prev_point = None
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._canvas.copy())
        self._canvas = self._redo_stack.pop()
        self._prev_point = None
        return True

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self, point):
        if point is None:
            self._end_stroke()
            return

        color  = ERASER_COLOR if self.eraser_mode else self.color
        radius = ERASER_RADIUS if self.eraser_mode else self.brush_size

        if not self._stroke_active:
            self._push_undo()
            self._stroke_active = True

        # Shape tools
        if self.shape_tool != SHAPE_FREEHAND and not self.eraser_mode:
            self._draw_shape(point, color, radius)
            return

        # Freehand — smooth curve
        if self._prev_point:
            # Interpolate for smooth stroke at any speed
            cv2.line(self._canvas, self._prev_point, point, color,
                     radius * 2, lineType=cv2.LINE_AA)
            if self.mirror_mode and not self.eraser_mode:
                mp1 = (self.w - self._prev_point[0], self._prev_point[1])
                mp2 = (self.w - point[0], point[1])
                cv2.line(self._canvas, mp1, mp2, color, radius * 2,
                         lineType=cv2.LINE_AA)
        else:
            cv2.circle(self._canvas, point, radius, color, -1, cv2.LINE_AA)
            if self.mirror_mode and not self.eraser_mode:
                cv2.circle(self._canvas, (self.w - point[0], point[1]),
                           radius, color, -1, cv2.LINE_AA)

        self._prev_point = point

    def _draw_shape(self, point, color, radius):
        if self._shape_start is None:
            self._shape_start = point
            self._shape_canvas = self._canvas.copy()
            self._shape_dragging = True
            return

        if self._shape_dragging:
            self._canvas = self._shape_canvas.copy()
            thickness = max(2, radius)
            sx, sy = self._shape_start
            ex, ey = point

            if self.shape_tool == SHAPE_LINE:
                cv2.line(self._canvas, (sx, sy), (ex, ey), color,
                         thickness, cv2.LINE_AA)
                if self.mirror_mode:
                    cv2.line(self._canvas, (self.w - sx, sy),
                             (self.w - ex, ey), color, thickness, cv2.LINE_AA)

            elif self.shape_tool == SHAPE_RECTANGLE:
                cv2.rectangle(self._canvas, (sx, sy), (ex, ey), color,
                              thickness, cv2.LINE_AA)
                if self.mirror_mode:
                    cv2.rectangle(self._canvas, (self.w - sx, sy),
                                  (self.w - ex, ey), color, thickness,
                                  cv2.LINE_AA)

            elif self.shape_tool == SHAPE_CIRCLE:
                r = int(np.hypot(ex - sx, ey - sy))
                cv2.circle(self._canvas, (sx, sy), r, color,
                           thickness, cv2.LINE_AA)
                if self.mirror_mode:
                    cv2.circle(self._canvas, (self.w - sx, sy), r, color,
                               thickness, cv2.LINE_AA)

    def _end_stroke(self):
        self._prev_point = None
        self._stroke_active = False
        self._shape_start = None
        self._shape_canvas = None
        self._shape_dragging = False

    def lift_pen(self):
        self._end_stroke()

    def clear(self):
        self._push_undo()
        self._canvas[:] = 0
        self._prev_point = None
        self._stroke_active = False

    def save(self):
        filename = f"air_drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(filename, self._canvas)
        print(f"💾 Saved: {filename}")
        return filename

    # ── Brush size ────────────────────────────────────────────────────────────

    def increase_brush(self, amount=2):
        self.brush_size = min(30, self.brush_size + amount)

    def decrease_brush(self, amount=2):
        self.brush_size = max(2, self.brush_size - amount)

    # ── Shape tool ────────────────────────────────────────────────────────────

    def set_shape_tool(self, tool):
        self.shape_tool = tool

    def get_shape_name(self):
        return SHAPE_NAMES.get(self.shape_tool, "Freehand")

    # ── Mirror ────────────────────────────────────────────────────────────────

    def toggle_mirror(self):
        self.mirror_mode = not self.mirror_mode

    # ── Color selection ───────────────────────────────────────────────────────

    def set_color_by_name(self, name):
        if name in COLORS:
            self.color      = COLORS[name]
            self.color_name = name
            self.eraser_mode = False

    def select_color_from_palette(self, x, y):
        """Check if (x, y) is inside any swatch. Returns True if selected."""
        # Generous hit zone — expand by 8px each direction
        pad = 8
        for i, name in enumerate(COLOR_NAMES):
            sx, sy, ex, ey = self._palette_bounds[i]
            if sx - pad <= x <= ex + pad and sy - pad <= y <= ey + pad:
                self.set_color_by_name(name)
                return True

        # Eraser swatch
        sx, sy, ex, ey = self._eraser_bounds
        if sx - pad <= x <= ex + pad and sy - pad <= y <= ey + pad:
            self.eraser_mode = True
            return True

        return False

    # ── Overlay ───────────────────────────────────────────────────────────────

    def overlay_on_frame(self, frame, glow_engine=None):
        canvas = self._canvas
        if glow_engine and glow_engine.enabled:
            canvas = glow_engine.apply(canvas)
        mask = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        bg = cv2.bitwise_and(frame, frame, mask=mask_inv)
        fg = cv2.bitwise_and(canvas, canvas, mask=mask)
        return cv2.add(bg, fg)

    # ── Palette rendering — modern floating toolbar ───────────────────────────

    def draw_palette(self, frame):
        """Render a modern floating palette toolbar."""
        total_swatches = len(COLOR_NAMES) + 1  # +1 for eraser
        total_w = (self.PALETTE_PADDING * 2 +
                   total_swatches * self.PALETTE_SWATCH_W +
                   (total_swatches - 1) * self.PALETTE_MARGIN)
        bar_h = self.PALETTE_SWATCH_H + self.PALETTE_PADDING * 2

        # Center the palette bar
        bar_x = (self.w - total_w) // 2
        bar_y = 0

        # ── Glass background panel ───────────────────────────────────────
        overlay = frame.copy()
        cv2.rectangle(overlay, (bar_x, bar_y),
                      (bar_x + total_w, bar_y + bar_h + 6),
                      (12, 12, 18), -1)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

        # Bottom edge glow
        cv2.line(frame, (bar_x + 10, bar_y + bar_h + 5),
                 (bar_x + total_w - 10, bar_y + bar_h + 5),
                 (40, 45, 55), 1, cv2.LINE_AA)

        # ── Draw swatches ────────────────────────────────────────────────
        for i, name in enumerate(COLOR_NAMES):
            sx = bar_x + self.PALETTE_PADDING + i * (self.PALETTE_SWATCH_W + self.PALETTE_MARGIN)
            sy = bar_y + self.PALETTE_PADDING
            ex = sx + self.PALETTE_SWATCH_W
            ey = sy + self.PALETTE_SWATCH_H
            bgr = COLORS[name]

            # Update hit-test bounds to match rendered position
            self._palette_bounds[i] = (sx, sy, ex, ey)

            # Color fill with slight rounding
            cv2.rectangle(frame, (sx + 1, sy + 1), (ex - 1, ey - 1),
                          bgr, -1, cv2.LINE_AA)

            # Selection highlight
            if name == self.color_name and not self.eraser_mode:
                # White border + subtle glow
                cv2.rectangle(frame, (sx - 2, sy - 2), (ex + 2, ey + 2),
                              (255, 255, 255), 2, cv2.LINE_AA)
                # Small triangle indicator below
                mid_x = (sx + ex) // 2
                pts = np.array([[mid_x - 4, ey + 5],
                                [mid_x + 4, ey + 5],
                                [mid_x, ey + 1]], np.int32)
                cv2.fillPoly(frame, [pts], (255, 255, 255), cv2.LINE_AA)
            else:
                # Subtle dark border
                cv2.rectangle(frame, (sx, sy), (ex, ey),
                              (35, 35, 45), 1, cv2.LINE_AA)

        # ── Eraser swatch ────────────────────────────────────────────────
        er_idx = len(COLOR_NAMES)
        er_sx = bar_x + self.PALETTE_PADDING + er_idx * (self.PALETTE_SWATCH_W + self.PALETTE_MARGIN)
        er_sy = bar_y + self.PALETTE_PADDING
        er_ex = er_sx + self.PALETTE_SWATCH_W
        er_ey = er_sy + self.PALETTE_SWATCH_H
        self._eraser_bounds = (er_sx, er_sy, er_ex, er_ey)

        # Eraser fill
        cv2.rectangle(frame, (er_sx + 1, er_sy + 1), (er_ex - 1, er_ey - 1),
                      (55, 55, 60), -1, cv2.LINE_AA)
        # X icon
        cx = (er_sx + er_ex) // 2
        cy = (er_sy + er_ey) // 2
        d = 7
        cv2.line(frame, (cx - d, cy - d), (cx + d, cy + d),
                 (180, 180, 190), 2, cv2.LINE_AA)
        cv2.line(frame, (cx + d, cy - d), (cx - d, cy + d),
                 (180, 180, 190), 2, cv2.LINE_AA)

        if self.eraser_mode:
            cv2.rectangle(frame, (er_sx - 2, er_sy - 2), (er_ex + 2, er_ey + 2),
                          (255, 255, 255), 2, cv2.LINE_AA)
            mid_x = (er_sx + er_ex) // 2
            pts = np.array([[mid_x - 4, er_ey + 5],
                            [mid_x + 4, er_ey + 5],
                            [mid_x, er_ey + 1]], np.int32)
            cv2.fillPoly(frame, [pts], (255, 255, 255), cv2.LINE_AA)

        return frame

    # ── Mirror guide line ─────────────────────────────────────────────────────

    def draw_mirror_line(self, frame):
        if not self.mirror_mode:
            return frame
        cx = self.w // 2
        # Subtle dashed line
        for y in range(0, self.h, 14):
            cv2.line(frame, (cx, y), (cx, min(y + 7, self.h)),
                     (50, 55, 65), 1, cv2.LINE_AA)
        return frame
