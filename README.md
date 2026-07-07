# 🎨 Air Drawing

A modern Python application for drawing in mid-air using intuitive hand gestures. The system utilizes **MediaPipe** for precise hand tracking and **OpenCV** for high-performance graphics rendering, all wrapped in a sleek, glassmorphism-inspired UI.

---

## ✨ Features

- **✋ Gesture-Based Controls**: Draw, hover, erase, and interact using natural hand movements.
- **🖌️ Freehand & Shape Tools**: Draw smooth freehand paths or precise lines, rectangles, and circles.
- **🎨 Dynamic Color Palette**: Quick selection from 12 vibrant colors using a pinch gesture.
- **✨ Visual Effects**: Cinematic vignette, neon glow shaders, particle emissions, and animated cursor trails.
- **🪞 Mirror Mode**: Symmetric drawing across the Y-axis.
- **⏪ Undo / Redo**: Robust history stack for fixing mistakes.
- **🪄 Dynamic Brush Sizing**: Adjust brush size dynamically via keyboard or gestures.
- **🎛️ Modern HUD**: Beautiful glassmorphism UI showing the current mode, color, brush size, and active effects.

## 🕹️ Gesture Controls

| Gesture | Action |
| :--- | :--- |
| ☝️ **Index finger up** | Draw |
| ✌️ **Index + Middle up** | Hover (move cursor without drawing) |
| 🤏 **Pinch on palette** | Select Color |
| ✊ **Fist** | Erase mode |
| 🖐️ **Open hand (hold 1.2s)** | Clear entire canvas |
| 🤟 **Ring + Pinky up** | Undo |

## ⌨️ Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| `Q` | Quit Application |
| `S` | Save Canvas to PNG |
| `Z` | Undo |
| `Y` | Redo |
| `G` | Toggle Neon Glow Effect |
| `M` | Toggle Mirror Mode |
| `E` | Toggle Eraser |
| `H` | Show/Hide Help Overlay |
| `+` / `-` | Increase/Decrease Brush Size |
| `1` - `4` | Shape Tools (1: Freehand, 2: Line, 3: Rectangle, 4: Circle) |

## 🛠️ Tech Stack

- **Python 3.8+**
- **OpenCV** (cv2)
- **MediaPipe**
- **NumPy**

## 🚀 Installation & Usage

1. **Clone this repository** (or navigate to the project directory).
   ```bash
   cd Drawing
   ```

2. **Create and activate a Python virtual environment** (recommended).
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or venv\Scripts\activate on Windows
   ```

3. **Install dependencies**.
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**. Make sure your webcam is connected!
   ```bash
   python main.py
   ```

---
*Made with ❤️ using Python and OpenCV.*