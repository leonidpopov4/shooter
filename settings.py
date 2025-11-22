# settings.py
# Global configuration for the Blue Arena shooter

import os

# -----------------------------
# Window / camera settings
# -----------------------------

WIDTH = 1280
HEIGHT = 720

FOV = 85.0          # slightly wider FOV so map feels less zoomed-in
NEAR_PLANE = 0.1
FAR_PLANE = 200.0

MOUSE_SENS = 0.15
CAMERA_PITCH_LIMIT = 89.0

MOVE_SPEED = 8.0
SPRINT_MULTIPLIER = 1.7

# Bigger arena than the very first version
ARENA_HALF = 13.0   # half-size of the tray


# -----------------------------
# Paths
# -----------------------------

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")  # for future textures / models
