"""
Air Drawing
===========
Draw in mid-air using hand gestures via webcam.
Modern, clean UI with glassmorphism aesthetic.

Gestures:
  ☝️  Index finger only       → Draw
  ✌️  Index + Middle up       → Hover (move without drawing)
  🤏  Pinch over palette      → Select color
  ✊  Fist                    → Erase
  🖐️  Open hand (hold 1.2 s)  → Clear entire canvas
  🤟  Ring + Pinky up          → Undo

Keyboard:
  Q  Quit     S  Save     Z  Undo     Y  Redo
  G  Glow     M  Mirror   E  Eraser   H  Help
  +/-  Brush  1-4  Shape tool
"""

import cv2
import numpy as np
import time

from hand_tracker import HandTracker
from gestures import DrawingGesture
from canvas import Canvas, COLORS, COLOR_NAMES, SHAPE_NAMES
from canvas import SHAPE_FREEHAND, SHAPE_LINE, SHAPE_RECTANGLE, SHAPE_CIRCLE
from effects import (NeonGlow, CursorTrail, ToastManager,
                     ParticleEmitter, AnimatedCursor, FPSCounter, Vignette)


# ── Config ────────────────────────────────────────────────────────────────────
WEBCAM_ID        = 0
FRAME_W, FRAME_H = 640, 480
ALPHA            = 0.50   # webcam brightness — lower = darker background


# ── HUD ───────────────────────────────────────────────────────────────────────

def draw_hud(frame, mode, canvas, clear_progress, glow, show_help):
    """Render modern bottom HUD bar."""
    h, w = frame.shape[:2]
    panel_h = 52

    # ── Glass panel ───────────────────────────────────────────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - panel_h), (w, h), (10, 10, 16), -1)
    cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)
    # Top accent line
    cv2.line(frame, (0, h - panel_h), (w, h - panel_h), (45, 50, 65), 1)

    y = h - 20  # text baseline

    # ── Mode dot + label ──────────────────────────────────────────────────
    mode_colors = {
        "draw":   (120, 255, 180),
        "hover":  (180, 180, 190),
        "select": (80,  210, 255),
        "erase":  (100, 130, 255),
        "clear":  (60,  80,  255),
        "undo":   (255, 200, 100),
        "none":   (80,  80,  90),
    }
    mc = mode_colors.get(mode, (150, 150, 150))
    cv2.circle(frame, (16, y), 4, mc, -1, cv2.LINE_AA)
    cv2.putText(frame, mode.upper(), (26, y + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, mc, 1, cv2.LINE_AA)

    # ── Color swatch + name ───────────────────────────────────────────────
    x = 100
    if canvas.eraser_mode:
        cv2.putText(frame, "ERASER", (x, y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 160, 170), 1, cv2.LINE_AA)
    else:
        cv2.rectangle(frame, (x, y - 7), (x + 14, y + 7),
                      canvas.color, -1, cv2.LINE_AA)
        cv2.putText(frame, canvas.color_name, (x + 20, y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (190, 190, 200), 1, cv2.LINE_AA)

    # ── Brush size ────────────────────────────────────────────────────────
    x = 220
    cv2.putText(frame, f"Size {canvas.brush_size}", (x, y + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (140, 150, 165), 1, cv2.LINE_AA)
    # Brush preview dot
    r = min(canvas.brush_size, 10)
    dot_c = canvas.color if not canvas.eraser_mode else (80, 80, 80)
    cv2.circle(frame, (x + 70, y), r, dot_c, -1, cv2.LINE_AA)

    # ── Shape tool ────────────────────────────────────────────────────────
    x = 330
    sname = canvas.get_shape_name()
    sc = (80, 210, 255) if canvas.shape_tool != SHAPE_FREEHAND else (100, 100, 110)
    cv2.putText(frame, sname, (x, y + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, sc, 1, cv2.LINE_AA)

    # ── Status badges (right side) ────────────────────────────────────────
    badges = []
    if glow.enabled:
        badges.append(("GLOW", (80, 255, 200)))
    if canvas.mirror_mode:
        badges.append(("MIRROR", (255, 210, 100)))

    bx = w - 20
    for label, bc in reversed(badges):
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.32, 1)
        bx -= tw + 16
        # Badge pill
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (bx - 4, y - 10), (bx + tw + 4, y + 5),
                      (25, 28, 35), -1)
        cv2.rectangle(overlay2, (bx - 4, y - 10), (bx + tw + 4, y + 5),
                      bc, 1, cv2.LINE_AA)
        cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)
        cv2.putText(frame, label, (bx, y + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, bc, 1, cv2.LINE_AA)
        bx -= 8

    # ── H for help hint ──────────────────────────────────────────────────
    cv2.putText(frame, "[H] Help", (w - 65, h - panel_h + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.28, (55, 55, 65), 1, cv2.LINE_AA)

    # ── Clear progress bar ────────────────────────────────────────────────
    if clear_progress > 0:
        bar_w = int(w * clear_progress)
        # Gradient bar above the HUD
        bar_y = h - panel_h - 5
        cv2.rectangle(frame, (0, bar_y), (bar_w, bar_y + 4),
                      (50, 100, 255), -1)
        if clear_progress > 0.85:
            cv2.rectangle(frame, (0, bar_y), (bar_w, bar_y + 4),
                          (80, 150, 255), -1)
        if clear_progress > 0.3:
            cv2.putText(frame, "Clearing...", (w // 2 - 35, bar_y - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1,
                        cv2.LINE_AA)

    # ── Help overlay ──────────────────────────────────────────────────────
    if show_help:
        _draw_help_overlay(frame)

    return frame


def _draw_help_overlay(frame):
    """Full-screen help reference with modern dark glass style."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (30, 55), (w - 30, h - 65), (8, 8, 14), -1)
    cv2.addWeighted(overlay, 0.94, frame, 0.06, 0, frame)
    cv2.rectangle(frame, (30, 55), (w - 30, h - 65), (50, 55, 70), 1, cv2.LINE_AA)

    accent   = (80, 240, 210)
    heading  = (120, 200, 255)
    text     = (190, 195, 205)
    key_c    = (255, 210, 120)
    font     = cv2.FONT_HERSHEY_SIMPLEX

    cv2.putText(frame, "AIR DRAWING", (50, 84), font, 0.65, accent, 2, cv2.LINE_AA)
    cv2.putText(frame, "Quick Reference", (210, 84), font, 0.45, (120, 125, 140), 1, cv2.LINE_AA)

    # Gestures
    cv2.putText(frame, "GESTURES", (50, 112), font, 0.4, heading, 1, cv2.LINE_AA)
    gestures = [
        ("Index finger up", "Draw"),
        ("Index + Middle", "Hover"),
        ("Pinch on palette", "Pick Color"),
        ("Fist", "Erase"),
        ("Open hand hold", "Clear All"),
        ("Ring + Pinky", "Undo"),
    ]
    for i, (g, a) in enumerate(gestures):
        y = 132 + i * 18
        cv2.putText(frame, g, (60, y), font, 0.34, text, 1, cv2.LINE_AA)
        cv2.putText(frame, a, (260, y), font, 0.34, (140, 255, 160), 1, cv2.LINE_AA)

    # Keys
    cv2.putText(frame, "KEYBOARD", (50, 250), font, 0.4, heading, 1, cv2.LINE_AA)
    keys = [
        ("Q", "Quit"), ("S", "Save"), ("Z", "Undo"), ("Y", "Redo"),
        ("G", "Glow"), ("M", "Mirror"), ("E", "Eraser"), ("H", "Help"),
        ("+/-", "Brush Size"), ("1-4", "Shape Tool"),
    ]
    col1, col2 = 60, 320
    for i, (k, a) in enumerate(keys):
        c = col1 if i < 5 else col2
        row = i if i < 5 else i - 5
        y = 270 + row * 18
        cv2.putText(frame, f"[{k}]", (c, y), font, 0.34, key_c, 1, cv2.LINE_AA)
        cv2.putText(frame, a, (c + 42, y), font, 0.34, text, 1, cv2.LINE_AA)

    # Close hint
    cv2.putText(frame, "Press H to close", (w // 2 - 55, h - 78), font, 0.32,
                (70, 70, 80), 1, cv2.LINE_AA)


# ── Splash ────────────────────────────────────────────────────────────────────

def show_splash(cap):
    """Modern startup splash with gradient and loading animation."""
    # Create gradient background
    splash = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
    for y in range(FRAME_H):
        t = y / FRAME_H
        splash[y, :] = (int(12 + 8 * t), int(10 + 6 * t), int(18 + 14 * t))

    font = cv2.FONT_HERSHEY_SIMPLEX
    cx, cy = FRAME_W // 2, FRAME_H // 2

    # Title
    title = "AIR DRAWING"
    (tw, th), _ = cv2.getTextSize(title, font, 1.1, 2)
    cv2.putText(splash, title, (cx - tw // 2, cy - 40), font, 1.1,
                (80, 250, 220), 2, cv2.LINE_AA)

    # Tagline
    tag = "Draw with your hands in mid-air"
    (sw, _), _ = cv2.getTextSize(tag, font, 0.45, 1)
    cv2.putText(splash, tag, (cx - sw // 2, cy), font, 0.45,
                (130, 140, 155), 1, cv2.LINE_AA)

    # Gesture hints
    hints = [
        "Point to draw  |  Peace to hover  |  Fist to erase",
        "Press H for full help  |  Q to quit",
    ]
    for i, h_text in enumerate(hints):
        (hw, _), _ = cv2.getTextSize(h_text, font, 0.34, 1)
        cv2.putText(splash, h_text, (cx - hw // 2, cy + 38 + i * 20),
                    font, 0.34, (90, 95, 110), 1, cv2.LINE_AA)

    # Animated loading bar
    bar_y = cy + 100
    bar_x1 = 120
    bar_x2 = FRAME_W - 120
    start = time.time()
    duration = 1.8

    while time.time() - start < duration:
        display = splash.copy()
        progress = (time.time() - start) / duration

        # Bar background
        cv2.rectangle(display, (bar_x1, bar_y), (bar_x2, bar_y + 4),
                      (30, 32, 40), -1)
        # Bar fill — gradient color shift
        fill_w = int((bar_x2 - bar_x1) * progress)
        bar_color = (int(60 + 40 * progress),
                     int(180 + 70 * progress),
                     int(200 - 20 * progress))
        cv2.rectangle(display, (bar_x1, bar_y), (bar_x1 + fill_w, bar_y + 4),
                      bar_color, -1)

        cv2.imshow("Air Drawing", display)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            return False

    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cap = cv2.VideoCapture(WEBCAM_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    if not cap.isOpened():
        print("❌ Could not open webcam. Check your camera connection.")
        return

    # Splash
    show_splash(cap)

    tracker   = HandTracker(max_hands=1, smoothing=0.60)
    detector  = DrawingGesture()
    canvas    = Canvas(FRAME_W, FRAME_H)

    # Effects
    glow      = NeonGlow()
    trail     = CursorTrail()
    toasts    = ToastManager()
    particles = ParticleEmitter()
    cursor_fx = AnimatedCursor()
    fps_ctr   = FPSCounter()
    vignette  = Vignette(FRAME_W, FRAME_H, strength=0.35)

    show_help = False

    print("✅ Air Drawing started. Press H for help, Q to quit.")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        fps_ctr.tick()
        frame = cv2.flip(frame, 1)
        frame, results = tracker.find_hands(frame)
        landmarks = tracker.get_landmarks(results, frame.shape)
        fingers   = tracker.fingers_up(landmarks)

        mode, tip = detector.detect(landmarks, fingers)

        # ── Clear progress ────────────────────────────────────────────────
        clear_progress = 0.0
        if detector._open_hand_start is not None:
            elapsed = time.time() - detector._open_hand_start
            clear_progress = min(elapsed / detector.CLEAR_HOLD_SEC, 1.0)

        # ── Handle mode ───────────────────────────────────────────────────
        if mode == DrawingGesture.MODE_DRAW and tip:
            canvas.draw(tip)

        elif mode == DrawingGesture.MODE_HOVER:
            canvas.lift_pen()

        elif mode == DrawingGesture.MODE_SELECT and tip:
            canvas.select_color_from_palette(tip[0], tip[1])
            canvas.lift_pen()

        elif mode == DrawingGesture.MODE_ERASE and tip:
            canvas.eraser_mode = True
            canvas.draw(tip)

        elif mode == DrawingGesture.MODE_UNDO:
            if canvas.undo():
                toasts.show("Undo", 1.0, (255, 210, 100))
            canvas.lift_pen()

        elif mode == DrawingGesture.MODE_CLEAR:
            canvas.clear()
            toasts.show("Canvas Cleared", 1.5, (100, 220, 255))

        else:
            if mode not in (DrawingGesture.MODE_DRAW, DrawingGesture.MODE_ERASE):
                canvas.eraser_mode = False
            canvas.lift_pen()

        # ── Update effects ────────────────────────────────────────────────
        trail.update(tip)
        if tip and mode == DrawingGesture.MODE_DRAW:
            particles.emit(tip[0], tip[1], canvas.color, count=2)

        # ── Compose final frame ───────────────────────────────────────────
        # Darken webcam for contrast
        dimmed = cv2.addWeighted(frame, ALPHA,
                                 np.zeros_like(frame), 1 - ALPHA, 0)
        # Apply vignette for cinematic look
        dimmed = vignette.apply(dimmed)

        # Drawing overlay
        output = canvas.overlay_on_frame(dimmed, glow)
        output = canvas.draw_palette(output)
        output = canvas.draw_mirror_line(output)

        # Effects
        output = trail.render(output, canvas.color if not canvas.eraser_mode
                              else (100, 100, 110))
        output = particles.update_and_render(output)
        output = cursor_fx.render(output, tip, canvas.color,
                                  canvas.brush_size, canvas.eraser_mode)
        output = toasts.render(output)

        # HUD
        draw_hud(output, mode, canvas, clear_progress, glow, show_help)
        fps_ctr.render(output)

        cv2.imshow("Air Drawing", output)

        # ── Keyboard ──────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            fname = canvas.save()
            toasts.show(f"Saved: {fname}", 2.0, (100, 255, 140))
        elif key == ord('z'):
            if canvas.undo():
                toasts.show("Undo", 1.0, (255, 210, 100))
        elif key == ord('y'):
            if canvas.redo():
                toasts.show("Redo", 1.0, (100, 210, 255))
        elif key == ord('g'):
            glow.toggle()
            s = "ON" if glow.enabled else "OFF"
            toasts.show(f"Glow {s}", 1.2, (80, 255, 210))
        elif key == ord('m'):
            canvas.toggle_mirror()
            s = "ON" if canvas.mirror_mode else "OFF"
            toasts.show(f"Mirror {s}", 1.2, (255, 210, 100))
        elif key == ord('e'):
            canvas.eraser_mode = not canvas.eraser_mode
            s = "ON" if canvas.eraser_mode else "OFF"
            toasts.show(f"Eraser {s}", 1.0, (160, 160, 170))
        elif key == ord('h'):
            show_help = not show_help
        elif key in (ord('+'), ord('=')):
            canvas.increase_brush()
            toasts.show(f"Brush {canvas.brush_size}px", 0.7, (140, 150, 165))
        elif key in (ord('-'), ord('_')):
            canvas.decrease_brush()
            toasts.show(f"Brush {canvas.brush_size}px", 0.7, (140, 150, 165))
        elif key == ord('1'):
            canvas.set_shape_tool(SHAPE_FREEHAND)
            toasts.show("Freehand", 1.0, (180, 180, 190))
        elif key == ord('2'):
            canvas.set_shape_tool(SHAPE_LINE)
            toasts.show("Line Tool", 1.0, (80, 210, 255))
        elif key == ord('3'):
            canvas.set_shape_tool(SHAPE_RECTANGLE)
            toasts.show("Rectangle Tool", 1.0, (80, 210, 255))
        elif key == ord('4'):
            canvas.set_shape_tool(SHAPE_CIRCLE)
            toasts.show("Circle Tool", 1.0, (80, 210, 255))

    cap.release()
    cv2.destroyAllWindows()
    print("👋 Exited Air Drawing.")


if __name__ == "__main__":
    main()
