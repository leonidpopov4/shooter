# geometry.py
# Obstacles, map layouts, and movement/collision helpers.

from dataclasses import dataclass
from typing import List

from pygame.math import Vector3

from settings import ARENA_HALF


@dataclass
class Obstacle:
    x1: float
    y1: float
    z1: float
    x2: float
    y2: float
    z2: float
    kind: str = "block"   # "wall" or "block"


OBSTACLES: List[Obstacle] = []


def add_obstacle(x1, y1, z1, x2, y2, z2, kind="block"):
    OBSTACLES.append(Obstacle(x1, y1, z1, x2, y2, z2, kind))


def add_frame(cx: float, cz: float, w: float, d: float, h: float, thick: float):
    """Approximate a hollow 'frame' shape using 4 thin boxes."""
    half_w = w / 2.0
    half_d = d / 2.0

    # top bar
    add_obstacle(cx - half_w, 0.0, cz - half_d,
                 cx + half_w, h, cz - half_d + thick)
    # bottom bar
    add_obstacle(cx - half_w, 0.0, cz + half_d - thick,
                 cx + half_w, h, cz + half_d)
    # left bar
    add_obstacle(cx - half_w, 0.0, cz - half_d,
                 cx - half_w + thick, h, cz + half_d)
    # right bar
    add_obstacle(cx + half_w - thick, 0.0, cz - half_d,
                 cx + half_w, h, cz + half_d)


# -----------------------------
# Map layouts
# -----------------------------

def _build_base_tray():
    """Outer tray walls common to all maps."""
    wall_h = 2.4
    t = 0.6

    # +Z wall
    add_obstacle(-ARENA_HALF, 0.0, ARENA_HALF - t,
                 ARENA_HALF, wall_h, ARENA_HALF, "wall")
    # -Z wall
    add_obstacle(-ARENA_HALF, 0.0, -ARENA_HALF,
                 ARENA_HALF, wall_h, -ARENA_HALF + t, "wall")
    # -X wall
    add_obstacle(-ARENA_HALF, 0.0, -ARENA_HALF,
                 -ARENA_HALF + t, wall_h, ARENA_HALF, "wall")
    # +X wall
    add_obstacle(ARENA_HALF - t, 0.0, -ARENA_HALF,
                 ARENA_HALF, wall_h, ARENA_HALF, "wall")


def _build_white_arena_layout():
    """Open layout with frames and a central pillar."""
    OBSTACLES.clear()
    _build_base_tray()

    # Central pillar
    add_obstacle(-2.0, 0.0, -2.0, 2.0, 4.0, 2.0, "block")

    # Four frames near corners
    add_frame(-7.0, -7.0, 4.0, 3.5, 3.0, 0.4)
    add_frame(7.0, -7.0, 4.0, 3.5, 3.0, 0.4)
    add_frame(-7.0, 7.0, 4.0, 3.5, 3.0, 0.4)
    add_frame(7.0, 7.0, 4.0, 3.5, 3.2, 0.4)

    # Side slabs
    add_obstacle(-10.0, 0.0, -3.0, -7.5, 2.8, 3.0, "block")
    add_obstacle(7.5, 0.0, -3.0, 10.0, 2.3, 3.0, "block")
    add_obstacle(-3.0, 0.0, -10.0, 3.0, 2.0, -7.5, "block")
    add_obstacle(-3.0, 0.0, 7.5, 3.0, 2.6, 10.0, "block")

    # Inner small blocks
    add_obstacle(-7.0, 0.0, -1.5, -4.0, 1.5, 1.5, "block")
    add_obstacle(4.0, 0.0, -1.5, 7.0, 1.5, 1.5, "block")
    add_obstacle(-1.5, 0.0, -7.0, 1.5, 1.5, -4.0, "block")
    add_obstacle(-1.5, 0.0, 4.0, 1.5, 1.5, 7.0, "block")


def _build_blue_arena_layout():
    """Distinct layout for Blue Arena: ring + mid platforms + side cover."""
    OBSTACLES.clear()
    _build_base_tray()

    # Central ring of cover around mid
    add_frame(0.0, 0.0, 8.0, 8.0, 3.0, 0.6)

    # Small central pillar for extra cover
    add_obstacle(-1.0, 0.0, -1.0, 1.0, 2.5, 1.0, "block")

    # Top and bottom platforms (good for peeking)
    add_obstacle(-5.0, 0.0, 6.5, 5.0, 1.4, 8.5, "block")   # north platform
    add_obstacle(-5.0, 0.0, -8.5, 5.0, 1.4, -6.5, "block")  # south platform

    # Diagonal corner cover blocks
    add_obstacle(-10.5, 0.0, 4.5, -7.5, 2.0, 7.5, "block")   # top-left
    add_obstacle(7.5, 0.0, 4.5, 10.5, 2.0, 7.5, "block")     # top-right
    add_obstacle(-10.5, 0.0, -7.5, -7.5, 2.0, -4.5, "block") # bottom-left
    add_obstacle(7.5, 0.0, -7.5, 10.5, 2.0, -4.5, "block")   # bottom-right


def _build_black_arena_layout():
    """More corridor / cross layout for tighter fights."""
    OBSTACLES.clear()
    _build_base_tray()

    # Thick plus-shaped cross in the middle
    add_obstacle(-1.0, 0.0, -10.0, 1.0, 3.0, 10.0, "block")
    add_obstacle(-10.0, 0.0, -1.0, 10.0, 3.0, 1.0, "block")

    # Four rectangular 'rooms' at diagonals
    add_obstacle(-10.5, 0.0, -10.5, -5.5, 2.5, -5.5, "block")
    add_obstacle(5.5, 0.0, -10.5, 10.5, 2.5, -5.5, "block")
    add_obstacle(-10.5, 0.0, 5.5, -5.5, 2.5, 10.5, "block")
    add_obstacle(5.5, 0.0, 5.5, 10.5, 2.5, 10.5, "block")

    # Short cover blocks near center
    add_obstacle(-4.0, 0.0, -2.0, -2.5, 1.5, 2.0, "block")
    add_obstacle(2.5, 0.0, -2.0, 4.0, 1.5, 2.0, "block")
    add_obstacle(-2.0, 0.0, -4.0, 2.0, 1.2, -2.5, "block")
    add_obstacle(-2.0, 0.0, 2.5, 2.0, 1.2, 4.0, "block")


def _build_backrooms_layout():
    """Maze-y repeating columns/walls for the Backrooms vibe."""
    OBSTACLES.clear()
    _build_base_tray()

    # Grid of square columns
    col_size = 1.4
    gap = 4.0
    for ix in range(-2, 3):
        for iz in range(-2, 3):
            if ix == 0 and iz == 0:
                continue  # leave center open
            cx = ix * gap
            cz = iz * gap
            add_obstacle(
                cx - col_size / 2, 0.0, cz - col_size / 2,
                cx + col_size / 2, 3.5, cz + col_size / 2,
                "block"
            )

    # Some longer walls to break sight lines
    add_obstacle(-10.0, 0.0, -6.0, 0.0, 3.2, -4.0, "block")
    add_obstacle(0.0, 0.0, 4.0, 10.0, 3.2, 6.0, "block")
    add_obstacle(-6.0, 0.0, -1.0, -4.0, 3.0, 9.0, "block")
    add_obstacle(4.0, 0.0, -9.0, 6.0, 3.0, 1.0, "block")


def build_map_geometry(map_name: str = "White Arena"):
    """Entry point: choose layout based on map_name."""
    if map_name == "Backrooms":
        _build_backrooms_layout()
    elif map_name == "Black Arena":
        _build_black_arena_layout()
    elif map_name == "Blue Arena":
        _build_blue_arena_layout()
    else:
        _build_white_arena_layout()


# -----------------------------
# Movement + collisions
# -----------------------------

def circle_overlaps_obstacle(x: float, z: float, radius: float, ob: Obstacle) -> bool:
    """Check top-down circle vs obstacle footprint."""
    min_x = min(ob.x1, ob.x2) - radius
    max_x = max(ob.x1, ob.x2) + radius
    min_z = min(ob.z1, ob.z2) - radius
    max_z = max(ob.z1, ob.z2) + radius
    return (min_x <= x <= max_x) and (min_z <= z <= max_z)


def is_position_free(pos: Vector3, radius: float) -> bool:
    for ob in OBSTACLES:
        if circle_overlaps_obstacle(pos.x, pos.z, radius, ob):
            return False
    return True


def move_with_collisions(pos: Vector3, move: Vector3, radius: float) -> Vector3:
    """Step movement and push out of obstacles (slide along walls)."""
    if move.length() == 0:
        return pos.copy()

    step_len = 0.4
    total_len = move.length()
    steps = max(1, int(total_len / step_len))
    step = move / steps
    cur = pos.copy()

    for _ in range(steps):
        candidate = cur + step

        for ob in OBSTACLES:
            min_x = min(ob.x1, ob.x2) - radius
            max_x = max(ob.x1, ob.x2) + radius
            min_z = min(ob.z1, ob.z2) - radius
            max_z = max(ob.z1, ob.z2) + radius

            if min_x <= candidate.x <= max_x and min_z <= candidate.z <= max_z:
                overlap_right = max_x - candidate.x
                overlap_left = candidate.x - min_x
                overlap_fwd = max_z - candidate.z
                overlap_back = candidate.z - min_z

                overlaps = [
                    ("right", overlap_right),
                    ("left", overlap_left),
                    ("forward", overlap_fwd),
                    ("back", overlap_back),
                ]
                direction, _ = min(overlaps, key=lambda kv: kv[1])

                if direction == "right":
                    candidate.x = max_x
                elif direction == "left":
                    candidate.x = min_x
                elif direction == "forward":
                    candidate.z = max_z
                else:
                    candidate.z = min_z

        # stay inside tray
        limit = ARENA_HALF - 0.2
        candidate.x = max(-limit, min(limit, candidate.x))
        candidate.z = max(-limit, min(limit, candidate.z))

        cur = candidate

    return cur


def find_safe_spawn(candidates: List[Vector3], radius: float) -> Vector3:
    for c in candidates:
        if is_position_free(c, radius):
            return c
    return candidates[0]