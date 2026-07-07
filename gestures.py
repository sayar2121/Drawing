"""
Gesture Detector
================
Interprets hand landmarks as drawing gestures.
Stable detection with debouncing — no accidental mode switches.

Modes:
  DRAW    — Index up only → draw at index tip
  HOVER   — Index + Middle up → move without drawing
  SELECT  — Pinch (thumb+index close) in palette zone → pick color
  ERASE   — Fist (0 fingers) → erase at index MCP
  CLEAR   — Open hand (5 fingers up) held for 1.2 s → clear canvas
  UNDO    — Ring + Pinky up only → undo last stroke (time-gated)
"""

import time
import numpy as np
from hand_tracker import HandTracker


class DrawingGesture:

    PINCH_THRESHOLD  = 50    # px — generous pinch distance
    CLEAR_HOLD_SEC   = 1.2   # seconds to hold open hand to clear
    UNDO_COOLDOWN    = 0.8   # seconds between undo triggers
    MODE_DEBOUNCE    = 0.08  # seconds — ignore rapid mode flickers

    MODE_DRAW   = "draw"
    MODE_HOVER  = "hover"
    MODE_SELECT = "select"
    MODE_ERASE  = "erase"
    MODE_CLEAR  = "clear"
    MODE_UNDO   = "undo"
    MODE_NONE   = "none"

    def __init__(self):
        self._open_hand_start = None
        self._clear_triggered = False
        self._last_undo_time  = 0.0
        self._last_mode       = self.MODE_NONE
        self._last_mode_time  = 0.0

    def _debounced_mode(self, new_mode, tip):
        """Prevent rapid mode flickering by requiring a mode to persist."""
        now = time.time()
        if new_mode != self._last_mode:
            if now - self._last_mode_time < self.MODE_DEBOUNCE:
                return self._last_mode, tip  # keep previous mode
            self._last_mode = new_mode
            self._last_mode_time = now
        return new_mode, tip

    def detect(self, landmarks, fingers):
        """
        Returns (mode, tip_position).
        tip_position is the index finger tip (x, y) in pixels.
        """
        if landmarks is None:
            self._open_hand_start = None
            self._last_mode = self.MODE_NONE
            return self.MODE_NONE, None

        thumb_up, index_up, middle_up, ring_up, pinky_up = fingers
        index_tip = landmarks[HandTracker.INDEX_TIP]
        thumb_tip = landmarks[HandTracker.THUMB_TIP]
        total_up  = sum(fingers)

        # ── CLEAR: all 5 fingers up, held ────────────────────────────────
        if total_up == 5:
            if self._open_hand_start is None:
                self._open_hand_start = time.time()
                self._clear_triggered = False
            elif (not self._clear_triggered and
                  time.time() - self._open_hand_start >= self.CLEAR_HOLD_SEC):
                self._clear_triggered = True
                return self.MODE_CLEAR, index_tip
            return self._debounced_mode(self.MODE_HOVER, index_tip)
        else:
            self._open_hand_start = None
            self._clear_triggered = False

        # ── UNDO: only ring + pinky up ───────────────────────────────────
        if (not thumb_up and not index_up and not middle_up
                and ring_up and pinky_up):
            now = time.time()
            if now - self._last_undo_time > self.UNDO_COOLDOWN:
                self._last_undo_time = now
                return self.MODE_UNDO, None
            return self.MODE_NONE, None

        # ── ERASE: fist (0 fingers up) ───────────────────────────────────
        if total_up == 0:
            return self._debounced_mode(self.MODE_ERASE,
                                        landmarks[HandTracker.INDEX_MCP])

        # ── SELECT: pinch inside palette zone (y < 80, generous) ─────────
        pinch_dist = np.hypot(thumb_tip[0] - index_tip[0],
                              thumb_tip[1] - index_tip[1])
        if pinch_dist < self.PINCH_THRESHOLD and index_tip[1] < 80:
            return self._debounced_mode(self.MODE_SELECT, index_tip)

        # ── HOVER: index + middle up ─────────────────────────────────────
        if index_up and middle_up:
            return self._debounced_mode(self.MODE_HOVER, index_tip)

        # ── DRAW: only index up ──────────────────────────────────────────
        if index_up and not middle_up:
            return self._debounced_mode(self.MODE_DRAW, index_tip)

        return self._debounced_mode(self.MODE_NONE, index_tip)
