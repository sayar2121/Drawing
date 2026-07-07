"""
Visual Effects Engine
=====================
Modern, gen-z aesthetic effects — neon glow, smooth cursor trails,
glassmorphism toasts, particle sparkles, animated cursor.
"""

import cv2
import numpy as np
import time
import random
import math


# ── Neon Glow ─────────────────────────────────────────────────────────────────

class NeonGlow:
    """Applies a bloom / glow post-process to the canvas drawing."""

    def __init__(self, intensity=0.6, blur_radius=21):
        self.intensity = intensity
        self.blur_radius = blur_radius
        self.enabled = False

    def toggle(self):
        self.enabled = not self.enabled

    def apply(self, canvas_img):
        if not self.enabled:
            return canvas_img
        blurred = cv2.GaussianBlur(canvas_img,
                                    (self.blur_radius, self.blur_radius), 0)
        blurred2 = cv2.GaussianBlur(canvas_img,
                                     (self.blur_radius * 2 + 1,
                                      self.blur_radius * 2 + 1), 0)
        glow = cv2.addWeighted(canvas_img, 1.0, blurred, self.intensity, 0)
        glow = cv2.addWeighted(glow, 1.0, blurred2, self.intensity * 0.35, 0)
        return np.clip(glow, 0, 255).astype(np.uint8)


# ── Cursor Trail ──────────────────────────────────────────────────────────────

class CursorTrail:
    """Smooth fading polyline trail behind the cursor."""

    def __init__(self, max_length=14):
        self.positions = []
        self.max_length = max_length

    def update(self, pos):
        if pos is not None:
            self.positions.append(pos)
        if len(self.positions) > self.max_length:
            self.positions = self.positions[-self.max_length:]

    def clear(self):
        self.positions.clear()

    def render(self, frame, color=(255, 255, 255)):
        if len(self.positions) < 2:
            return frame

        overlay = frame.copy()
        n = len(self.positions)
        for i in range(1, n):
            alpha = (i / n) ** 1.8
            thickness = max(1, int(4 * alpha))
            c = tuple(int(ch * alpha * 0.45) for ch in color)
            cv2.line(overlay, self.positions[i - 1], self.positions[i],
                     c, thickness, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        return frame


# ── Toast Notifications ──────────────────────────────────────────────────────

class ToastManager:
    """Modern floating toast notifications with blur-glass style."""

    def __init__(self):
        self.toasts = []

    def show(self, message, duration=1.8, color=(255, 255, 255)):
        self.toasts.append({
            "msg": message,
            "start": time.time(),
            "duration": duration,
            "color": color,
        })

    def render(self, frame):
        now = time.time()
        active = []
        y_offset = 70

        for t in self.toasts:
            elapsed = now - t["start"]
            if elapsed > t["duration"]:
                continue
            active.append(t)

            # Smooth fade in/out
            if elapsed < 0.25:
                alpha = elapsed / 0.25
            elif elapsed > t["duration"] - 0.4:
                alpha = (t["duration"] - elapsed) / 0.4
            else:
                alpha = 1.0

            msg = t["msg"]
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.6
            thickness = 1
            (tw, th), _ = cv2.getTextSize(msg, font, scale, thickness)

            cx = frame.shape[1] // 2
            tx = cx - tw // 2
            ty = y_offset

            # Glassmorphism pill background
            pad_x, pad_y = 18, 10
            x1 = tx - pad_x
            y1 = ty - th - pad_y
            x2 = tx + tw + pad_x
            y2 = ty + pad_y

            # Clip to frame bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

            overlay = frame.copy()
            # Dark glass background
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (18, 18, 25), -1)
            # Subtle border
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (60, 65, 80), 1,
                          cv2.LINE_AA)
            blend = alpha * 0.82
            cv2.addWeighted(overlay, blend, frame, 1 - blend, 0, frame)

            # Text with alpha
            color_a = tuple(int(c * alpha) for c in t["color"])
            cv2.putText(frame, msg, (tx, ty), font, scale, color_a,
                        thickness, cv2.LINE_AA)

            y_offset += th + pad_y * 2 + 12

        self.toasts = active
        return frame


# ── Particle System ───────────────────────────────────────────────────────────

class Particle:
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size']

    def __init__(self, x, y, color):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.0, 3.5)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.max_life = random.uniform(0.25, 0.6)
        self.life = self.max_life
        self.color = color
        self.size = random.randint(1, 3)


class ParticleEmitter:
    """Lightweight sparkle particles at the drawing cursor."""

    def __init__(self, max_particles=30):
        self.particles = []
        self.max_particles = max_particles
        self._last_time = time.time()

    def emit(self, x, y, color, count=2):
        for _ in range(count):
            if len(self.particles) < self.max_particles:
                self.particles.append(Particle(x, y, color))

    def update_and_render(self, frame):
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx
            p.y += p.vy
            p.vy += 8 * dt  # gentle gravity

            alpha = max(0.0, p.life / p.max_life)
            radius = max(1, int(p.size * alpha))
            c = tuple(int(ch * alpha * 0.8) for ch in p.color)
            px, py = int(p.x), int(p.y)
            if 0 <= px < frame.shape[1] and 0 <= py < frame.shape[0]:
                cv2.circle(frame, (px, py), radius, c, -1, cv2.LINE_AA)
            alive.append(p)

        self.particles = alive
        return frame


# ── Animated Cursor ───────────────────────────────────────────────────────────

class AnimatedCursor:
    """Smooth pulsing ring cursor — modern aesthetic."""

    def __init__(self):
        self._pulse_phase = 0.0

    def render(self, frame, pos, color, brush_size=6, eraser=False):
        if pos is None:
            return frame

        self._pulse_phase += 0.12
        pulse = 1.0 + 0.18 * math.sin(self._pulse_phase)

        if eraser:
            radius = int(28 * pulse)
            # Soft eraser ring
            overlay = frame.copy()
            cv2.circle(overlay, pos, radius, (140, 140, 150), 2, cv2.LINE_AA)
            cv2.circle(overlay, pos, 3, (200, 200, 200), -1, cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        else:
            outer_r = int((brush_size + 10) * pulse)
            # Outer ring
            overlay = frame.copy()
            cv2.circle(overlay, pos, outer_r, color, 2, cv2.LINE_AA)
            # Inner bright dot
            bright = tuple(min(255, int(ch * 0.4 + 160)) for ch in color)
            cv2.circle(overlay, pos, max(2, brush_size // 2 + 1),
                       bright, -1, cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        return frame


# ── FPS Counter ───────────────────────────────────────────────────────────────

class FPSCounter:
    """Smoothed FPS display — minimal and modern."""

    def __init__(self, smoothing=0.92):
        self._prev_time = time.time()
        self._fps = 0.0
        self._smoothing = smoothing

    def tick(self):
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now
        if dt > 0:
            instant = 1.0 / dt
            self._fps = self._smoothing * self._fps + (1 - self._smoothing) * instant

    def render(self, frame):
        text = f"{int(self._fps)} fps"
        w = frame.shape[1]
        # Small, subtle text in top-right
        cv2.putText(frame, text, (w - 70, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 200, 160), 1,
                    cv2.LINE_AA)
        return frame


# ── Vignette Effect ───────────────────────────────────────────────────────────

class Vignette:
    """Pre-computed vignette overlay for cinematic look."""

    def __init__(self, width, height, strength=0.45):
        # Create radial gradient mask
        Y, X = np.ogrid[:height, :width]
        cx, cy = width / 2, height / 2
        r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        r_max = np.sqrt(cx ** 2 + cy ** 2)
        self._mask = np.clip(1.0 - strength * (r / r_max) ** 1.8, 0, 1)
        self._mask = self._mask.astype(np.float32)
        # Expand to 3 channels
        self._mask_3ch = np.stack([self._mask] * 3, axis=-1)

    def apply(self, frame):
        return (frame.astype(np.float32) * self._mask_3ch).astype(np.uint8)
