# render.py
# All OpenGL drawing helpers: world, bullets, gun UI, HUD, themes.

from __future__ import annotations

import os
from typing import Dict, List, Tuple

import pygame
from OpenGL.GL import *

from settings import WIDTH, HEIGHT
from geometry import OBSTACLES
from weapons import Projectile, MuzzleFlash, ShellCasing
from actors import Bot, Player  # only for type hints

ARENA_HALF = 10.0

# -----------------------------
# Map themes
# -----------------------------

THEMES: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    "White Arena": {
        "floor_color": (0.90, 0.93, 0.96),
        "wall_color":  (0.80, 0.85, 0.92),
        "block_color": (0.82, 0.88, 0.95),
        "edge_color":  (0.00, 0.00, 0.00),
        "sky_color":   (0.70, 0.85, 1.00),
    },
    "Black Arena": {
        "floor_color": (0.12, 0.14, 0.18),
        "wall_color":  (0.18, 0.20, 0.26),
        "block_color": (0.20, 0.24, 0.30),
        "edge_color":  (1.00, 1.00, 1.00),
        "sky_color":   (0.03, 0.03, 0.05),
    },
    "Backrooms": {
        "floor_color": (0.78, 0.72, 0.42),
        "wall_color":  (0.82, 0.78, 0.52),
        "block_color": (0.84, 0.80, 0.56),
        "edge_color":  (0.00, 0.00, 0.00),
        "sky_color":   (0.05, 0.05, 0.05),
    },

    # New: blue arena (same layout as White, just blue colors)
    "Blue Arena": {
        "floor_color": (0.18, 0.23, 0.36),
        "wall_color":  (0.15, 0.20, 0.34),
        "block_color": (0.22, 0.32, 0.52),
        "edge_color":  (0.95, 0.98, 1.00),
        "sky_color":   (0.10, 0.18, 0.35),
    },

    # New: FFA Black map theme
    "FFA Black": {
        "floor_color": (0.07, 0.08, 0.10),
        "wall_color":  (0.14, 0.15, 0.20),
        "block_color": (0.20, 0.22, 0.28),
        "edge_color":  (1.00, 1.00, 1.00),
        "sky_color":   (0.00, 0.00, 0.00),
    },
}

_CURRENT_THEME: Dict[str, Tuple[float, float, float]] = THEMES["White Arena"]


def set_theme(map_name: str) -> None:
    global _CURRENT_THEME
    _CURRENT_THEME = THEMES.get(map_name, THEMES["White Arena"])


def get_theme(map_name: str | None = None) -> Dict[str, Tuple[float, float, float]]:
    if map_name is not None:
        return THEMES.get(map_name, THEMES["White Arena"])
    return _CURRENT_THEME


# -----------------------------
# Box helpers
# -----------------------------

def draw_box_solid(x1, y1, z1, x2, y2, z2):
    glBegin(GL_QUADS)

    # bottom
    glVertex3f(x1, y1, z1)
    glVertex3f(x2, y1, z1)
    glVertex3f(x2, y1, z2)
    glVertex3f(x1, y1, z2)

    # top
    glVertex3f(x1, y2, z1)
    glVertex3f(x2, y2, z1)
    glVertex3f(x2, y2, z2)
    glVertex3f(x1, y2, z2)

    # front
    glVertex3f(x1, y1, z2)
    glVertex3f(x2, y1, z2)
    glVertex3f(x2, y2, z2)
    glVertex3f(x1, y2, z2)

    # back
    glVertex3f(x1, y1, z1)
    glVertex3f(x2, y1, z1)
    glVertex3f(x2, y2, z1)
    glVertex3f(x1, y2, z1)

    # left
    glVertex3f(x1, y1, z1)
    glVertex3f(x1, y1, z2)
    glVertex3f(x1, y2, z2)
    glVertex3f(x1, y2, z1)

    # right
    glVertex3f(x2, y1, z1)
    glVertex3f(x2, y1, z2)
    glVertex3f(x2, y2, z2)
    glVertex3f(x2, y2, z1)

    glEnd()


def draw_box_edges(x1, y1, z1, x2, y2, z2):
    glLineWidth(1.4)

    glBegin(GL_LINE_LOOP)
    glVertex3f(x1, y1, z1)
    glVertex3f(x2, y1, z1)
    glVertex3f(x2, y1, z2)
    glVertex3f(x1, y1, z2)
    glEnd()

    glBegin(GL_LINE_LOOP)
    glVertex3f(x1, y2, z1)
    glVertex3f(x2, y2, z1)
    glVertex3f(x2, y2, z2)
    glVertex3f(x1, y2, z2)
    glEnd()

    glBegin(GL_LINE_LOOP)
    glVertex3f(x1, y1, z1)
    glVertex3f(x2, y1, z1)
    glVertex3f(x2, y2, z1)
    glVertex3f(x1, y2, z1)
    glEnd()

    glBegin(GL_LINE_LOOP)
    glVertex3f(x1, y1, z2)
    glVertex3f(x2, y1, z2)
    glVertex3f(x2, y2, z2)
    glVertex3f(x1, y2, z2)
    glEnd()

    glBegin(GL_LINE_LOOP)
    glVertex3f(x1, y1, z1)
    glVertex3f(x1, y1, z2)
    glVertex3f(x1, y2, z2)
    glVertex3f(x1, y2, z1)
    glEnd()

    glBegin(GL_LINE_LOOP)
    glVertex3f(x2, y1, z1)
    glVertex3f(x2, y1, z2)
    glVertex3f(x2, y2, z2)
    glVertex3f(x2, y2, z1)
    glEnd()


# -----------------------------
# Map + bullets
# -----------------------------

def draw_map_with_edges():
    theme = get_theme()
    floor_blue = theme["floor_color"]
    wall_blue = theme["wall_color"]
    block_blue = theme["block_color"]
    edge_color = theme["edge_color"]

    # Floor plate
    glColor3f(*floor_blue)
    draw_box_solid(-ARENA_HALF, -0.3, -ARENA_HALF,
                   ARENA_HALF, 0.0, ARENA_HALF)
    glColor3f(*edge_color)
    draw_box_edges(-ARENA_HALF, -0.3, -ARENA_HALF,
                   ARENA_HALF, 0.0, ARENA_HALF)

    # Obstacles
    for ob in OBSTACLES:
        color = wall_blue if getattr(ob, "kind", "block") == "wall" else block_blue
        glColor3f(*color)
        draw_box_solid(ob.x1, ob.y1, ob.z1, ob.x2, ob.y2, ob.z2)
        glColor3f(*edge_color)
        draw_box_edges(ob.x1, ob.y1, ob.z1, ob.x2, ob.y2, ob.z2)


def draw_bot(bot: Bot):
    edge_color = (0.0, 0.0, 0.0)
    glColor3f(1.0, 0.25, 0.35)
    x, z = bot.pos.x, bot.pos.z
    y1, y2 = 0.0, 2.0
    draw_box_solid(x - 0.5, y1, z - 0.5, x + 0.5, y2, z + 0.5)
    glColor3f(*edge_color)
    draw_box_edges(x - 0.5, y1, z - 0.5, x + 0.5, y2, z + 0.5)


def draw_projectiles(projectiles: List[Projectile]):
    # little cubes so they look like bullets
    for p in projectiles:
        glColor3f(*p.color)
        x, y, z = p.origin.x, p.origin.y, p.origin.z
        size = 0.12
        draw_box_solid(x - size, y - size, z - size,
                       x + size, y + size, z + size)


def draw_muzzle_flashes(flashes: List[MuzzleFlash]):
    glColor3f(1.0, 0.9, 0.3)
    for f in flashes:
        glPushMatrix()
        glTranslatef(f.pos.x, f.pos.y, f.pos.z)
        size = 0.25
        glBegin(GL_TRIANGLES)
        glVertex3f(0.0, size, 0.0)
        glVertex3f(-size, -size, 0.0)
        glVertex3f(size, -size, 0.0)
        glEnd()
        glPopMatrix()


def draw_shells(shells: List[ShellCasing]):
    glColor3f(0.8, 0.7, 0.3)
    for s in shells:
        x, y, z = s.pos.x, s.pos.y, s.pos.z
        size = 0.08
        draw_box_solid(x - size, y, z - size,
                       x + size, y + size * 0.4, z + size)


def draw_crosshair():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glDisable(GL_TEXTURE_2D)

    cx, cy = WIDTH // 2, HEIGHT // 2
    size = 9
    gap = 4
    glColor3f(0.0, 0.0, 0.0)
    glLineWidth(2.0)

    glBegin(GL_LINES)
    # horizontal
    glVertex2f(cx - gap - size, cy)
    glVertex2f(cx - gap, cy)
    glVertex2f(cx + gap, cy)
    glVertex2f(cx + gap + size, cy)
    # vertical
    glVertex2f(cx, cy - gap - size)
    glVertex2f(cx, cy - gap)
    glVertex2f(cx, cy + gap)
    glVertex2f(cx, cy + gap + size)
    glEnd()

    glEnable(GL_DEPTH_TEST)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# -----------------------------
# Gun PNG viewmodel
# -----------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

GUN_FILES: Dict[str, str] = {
    "gun1": "gun1.png",  # pistol
    "gun2": "gun2.png",  # sniper
    "gun3": "gun3.png",  # ak
    "gun4": "gun4.png",  # spray
    "gun5": "gun5.png",  # shotgun
}

WEAPON_TO_GUN: Dict[str, str] = {
    "Pistol": "gun1",
    "Sniper": "gun2",
    "AK47": "gun3",
    "Spray Gun": "gun4",
    "Shotgun": "gun5",
}

GUN_TEXTURES: Dict[str, Tuple[int, int, int]] = {}  # key -> (tex_id, w, h)


def _load_texture(path: str) -> Tuple[int, int, int]:
    surf = pygame.image.load(path).convert_alpha()
    w, h = surf.get_size()
    img_data = pygame.image.tostring(surf, "RGBA", True)

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA,
        w,
        h,
        0,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        img_data,
    )

    glBindTexture(GL_TEXTURE_2D, 0)
    return tex_id, w, h


def init_render_assets() -> None:
    """Load gun PNGs — call this AFTER OpenGL context is created."""
    global GUN_TEXTURES
    for key, filename in GUN_FILES.items():
        path = os.path.join(ASSETS_DIR, filename)
        if not os.path.exists(path):
            print(f"[WARN] gun texture missing: {path}")
            continue
        try:
            tex_id, w, h = _load_texture(path)
            GUN_TEXTURES[key] = (tex_id, w, h)
            print(f"[INFO] loaded {key} from {path} ({w}x{h})")
        except Exception as e:
            print(f"[WARN] failed to load {path}: {e}")


def draw_gun_ui(weapon_name: str) -> None:
    """Draw gun image as UI in the top-right corner."""
    gun_key = WEAPON_TO_GUN.get(weapon_name)
    if not gun_key:
        return
    tex_info = GUN_TEXTURES.get(gun_key)
    if not tex_info:
        return

    tex_id, w, h = tex_info

    target_h = int(HEIGHT * 0.45)
    aspect = w / float(h)
    target_w = int(target_h * aspect)

    pad_x = 40
    pad_y = 20
    x = WIDTH - target_w - pad_x
    y = pad_y

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glColor4f(1.0, 1.0, 1.0, 1.0)

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex2f(x,           y)
    glTexCoord2f(1.0, 0.0); glVertex2f(x+target_w,  y)
    glTexCoord2f(1.0, 1.0); glVertex2f(x+target_w,  y+target_h)
    glTexCoord2f(0.0, 1.0); glVertex2f(x,           y+target_h)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# -----------------------------
# HUD (HP bars)
# -----------------------------

def draw_hud(player: Player, bot: Bot) -> None:
    """2D health bars for player (bottom-left) and bot (top)."""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)
    glDisable(GL_TEXTURE_2D)

    # --- Player HP bottom-left ---
    max_hp = 100.0
    hp_pct = max(0.0, min(1.0, player.health / max_hp))

    bar_w = 220
    bar_h = 18
    x = 30
    y = 30

    # background
    glColor3f(0.08, 0.08, 0.10)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + bar_w, y)
    glVertex2f(x + bar_w, y + bar_h)
    glVertex2f(x, y + bar_h)
    glEnd()

    # fill
    r = 1.0 - hp_pct
    g = 0.2 + 0.8 * hp_pct
    b = 0.25
    fill_w = bar_w * hp_pct
    glColor3f(r, g, b)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + fill_w, y)
    glVertex2f(x + fill_w, y + bar_h)
    glVertex2f(x, y + bar_h)
    glEnd()

    # border
    glColor3f(0.0, 0.0, 0.0)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y)
    glVertex2f(x + bar_w, y)
    glVertex2f(x + bar_w, y + bar_h)
    glVertex2f(x, y + bar_h)
    glEnd()

    # --- Bot HP top-center ---
    bot_pct = max(0.0, min(1.0, bot.health / 100.0))
    bar_w2 = 180
    bar_h2 = 12
    cx = WIDTH / 2
    x2 = cx - bar_w2 / 2
    y2 = HEIGHT - 40

    glColor3f(0.08, 0.08, 0.10)
    glBegin(GL_QUADS)
    glVertex2f(x2, y2)
    glVertex2f(x2 + bar_w2, y2)
    glVertex2f(x2 + bar_w2, y2 + bar_h2)
    glVertex2f(x2, y2 + bar_h2)
    glEnd()

    glColor3f(1.0, 0.35, 0.35)
    fill2 = bar_w2 * bot_pct
    glBegin(GL_QUADS)
    glVertex2f(x2, y2)
    glVertex2f(x2 + fill2, y2)
    glVertex2f(x2 + fill2, y2 + bar_h2)
    glVertex2f(x2, y2 + bar_h2)
    glEnd()

    glColor3f(0.0, 0.0, 0.0)
    glLineWidth(1.5)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x2, y2)
    glVertex2f(x2 + bar_w2, y2)
    glVertex2f(x2 + bar_w2, y2 + bar_h2)
    glVertex2f(x2, y2 + bar_h2)
    glEnd()

    glEnable(GL_DEPTH_TEST)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)