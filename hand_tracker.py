"""
Hand Tracker
============
MediaPipe hand detection with heavy EMA landmark smoothing for
buttery-smooth cursor movement, and improved thumb detection.
"""

import mediapipe as mp
import cv2
import numpy as np


class HandTracker:
    WRIST      = 0
    THUMB_TIP  = 4
    THUMB_IP   = 3
    THUMB_MCP  = 2
    INDEX_TIP  = 8
    INDEX_MCP  = 5
    MIDDLE_TIP = 12
    MIDDLE_MCP = 9
    RING_TIP   = 16
    RING_MCP   = 13
    PINKY_TIP  = 20
    PINKY_MCP  = 17

    def __init__(self, max_hands=1, detection_confidence=0.75,
                 tracking_confidence=0.75, smoothing=0.60):
        self.mp_hands  = mp.solutions.hands
        self.mp_draw   = mp.solutions.drawing_utils
        self.hands     = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

        # EMA smoothing — higher = smoother but laggier
        self._smoothing = smoothing
        self._prev_landmarks = None

        # Finger state smoothing — require N consistent frames to flip
        self._finger_history = []
        self._finger_frames = 3  # frames of consistency needed

    # ── Detection ─────────────────────────────────────────────────────────────

    def find_hands(self, frame, draw=True):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        if draw and results.multi_hand_landmarks:
            for hl in results.multi_hand_landmarks:
                # Minimal, modern hand skeleton — thin lines, small dots
                self.mp_draw.draw_landmarks(
                    frame, hl,
                    self.mp_hands.HAND_CONNECTIONS,
                    mp.solutions.drawing_utils.DrawingSpec(
                        color=(200, 230, 255), thickness=1, circle_radius=1),
                    mp.solutions.drawing_utils.DrawingSpec(
                        color=(100, 140, 180), thickness=1),
                )
        return frame, results

    # ── Landmarks with EMA smoothing ──────────────────────────────────────────

    def get_landmarks(self, results, frame_shape, hand_index=0):
        if not results.multi_hand_landmarks:
            self._prev_landmarks = None
            return None
        if hand_index >= len(results.multi_hand_landmarks):
            self._prev_landmarks = None
            return None

        h, w = frame_shape[:2]
        raw = {}
        for idx, lm in enumerate(results.multi_hand_landmarks[hand_index].landmark):
            raw[idx] = (int(lm.x * w), int(lm.y * h))

        # Apply EMA smoothing for buttery movement
        if self._prev_landmarks is not None and self._smoothing > 0:
            smoothed = {}
            s = self._smoothing
            for idx in raw:
                if idx in self._prev_landmarks:
                    px, py = self._prev_landmarks[idx]
                    rx, ry = raw[idx]
                    smoothed[idx] = (int(s * px + (1 - s) * rx),
                                     int(s * py + (1 - s) * ry))
                else:
                    smoothed[idx] = raw[idx]
            self._prev_landmarks = smoothed
            return smoothed

        self._prev_landmarks = raw
        return raw

    # ── Finger state with hysteresis ──────────────────────────────────────────

    def fingers_up(self, landmarks):
        """
        Returns [thumb, index, middle, ring, pinky] — True if finger is up.
        Uses x-axis for thumb. Includes frame-based hysteresis to prevent flicker.
        """
        if landmarks is None:
            self._finger_history.clear()
            return [False] * 5

        # ── Thumb: x-axis (lateral movement) ──────────────────────────────
        wrist_x = landmarks[self.WRIST][0]
        thumb_tip_x = landmarks[self.THUMB_TIP][0]
        thumb_ip_x = landmarks[self.THUMB_IP][0]
        mid_mcp_x = landmarks[self.MIDDLE_MCP][0]

        if wrist_x < mid_mcp_x:
            thumb_up = thumb_tip_x > thumb_ip_x + 8  # small dead zone
        else:
            thumb_up = thumb_tip_x < thumb_ip_x - 8

        # ── Other fingers: tip y < mcp y with dead zone ──────────────────
        tips = [self.INDEX_TIP, self.MIDDLE_TIP, self.RING_TIP, self.PINKY_TIP]
        mcps = [self.INDEX_MCP, self.MIDDLE_MCP, self.RING_MCP, self.PINKY_MCP]
        dead_zone = 12  # pixels — prevent flicker near threshold
        others = [landmarks[t][1] < landmarks[m][1] - dead_zone
                  for t, m in zip(tips, mcps)]

        raw_state = [thumb_up] + others

        # ── Hysteresis: require consistent state for N frames ─────────────
        self._finger_history.append(raw_state)
        if len(self._finger_history) > self._finger_frames:
            self._finger_history.pop(0)

        if len(self._finger_history) < self._finger_frames:
            return raw_state

        # For each finger, only report "up" if it was up in ALL recent frames
        # and "down" if it was down in ALL recent frames; otherwise keep previous
        stable = []
        for f_idx in range(5):
            states = [h[f_idx] for h in self._finger_history]
            if all(states):
                stable.append(True)
            elif not any(states):
                stable.append(False)
            else:
                # Mixed — keep the majority
                stable.append(sum(states) > len(states) // 2)

        return stable

    def distance(self, landmarks, id1, id2):
        x1, y1 = landmarks[id1]
        x2, y2 = landmarks[id2]
        return np.hypot(x2 - x1, y2 - y1)

    def count_fingers_up(self, fingers):
        return sum(fingers)
