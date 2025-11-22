# shooting.py
# Ray / hitscan math with wall blocking.

from __future__ import annotations

import math
from typing import Optional

from pygame.math import Vector3

from actors import Actor
from geometry import OBSTACLES, Obstacle


def ray_aabb_distance(
    origin: Vector3,
    direction: Vector3,
    max_range: float,
    ob: Obstacle,
) -> Optional[float]:
    """
    Ray vs AABB in X/Z (we ignore Y height for blocking).
    Returns distance t along the ray, or None if no hit within [0, max_range].
    """
    t_min = 0.0
    t_max = max_range

    # X slab
    min_x = min(ob.x1, ob.x2)
    max_x = max(ob.x1, ob.x2)
    if abs(direction.x) < 1e-6:
        # Ray parallel to X planes: must be inside slab
        if origin.x < min_x or origin.x > max_x:
            return None
    else:
        inv = 1.0 / direction.x
        t1 = (min_x - origin.x) * inv
        t2 = (max_x - origin.x) * inv
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
        if t_max < t_min:
            return None

    # Z slab
    min_z = min(ob.z1, ob.z2)
    max_z = max(ob.z1, ob.z2)
    if abs(direction.z) < 1e-6:
        if origin.z < min_z or origin.z > max_z:
            return None
    else:
        inv = 1.0 / direction.z
        t1 = (min_z - origin.z) * inv
        t2 = (max_z - origin.z) * inv
        if t1 > t2:
            t1, t2 = t2, t1
        t_min = max(t_min, t1)
        t_max = min(t_max, t2)
        if t_max < t_min:
            return None

    if t_min < 0.0 or t_min > max_range:
        return None
    return t_min


def ray_hits_actor(
    origin: Vector3,
    direction: Vector3,
    max_range: float,
    actor: Actor,
) -> bool:
    """
    Ray-sphere for the actor, BUT:
    if there is an obstacle closer than the actor, ray is blocked.
    """
    direction = direction.normalize()
    center = actor.pos
    radius = actor.radius

    # Sphere intersection (standard)
    m = origin - center
    b = m.dot(direction)
    c = m.dot(m) - radius * radius

    # Ray origin outside sphere and pointing away
    if c > 0.0 and b > 0.0:
        return False

    discr = b * b - c
    if discr < 0.0:
        return False

    t_actor = -b - math.sqrt(discr)
    if t_actor < 0.0:
        t_actor = 0.0

    if t_actor > max_range:
        return False

    # Now check if a wall is closer than t_actor
    nearest_wall = None
    for ob in OBSTACLES:
        t = ray_aabb_distance(origin, direction, max_range, ob)
        if t is None:
            continue
        if nearest_wall is not None and nearest_wall <= t:
            continue
        nearest_wall = t

    # If we found a wall closer than the actor → blocked
    if nearest_wall is not None and nearest_wall < t_actor:
        return False

    return True
