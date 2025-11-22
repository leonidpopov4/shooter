# weapons.py
# Weapon stats, projectiles, and Weapon class.

import random
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional

from pygame.math import Vector3


@dataclass
class WeaponStats:
    name: str
    fire_rate: float           # shots per second
    magazine_size: int
    reload_time: float         # seconds
    damage: float
    accuracy: float            # 0-1 base
    range: float               # world units
    pellet_count: int = 1
    projectile_speed: float = 80.0
    is_auto: bool = False
    aim_accuracy_bonus: float = 0.2
    close_range_only: bool = False


@dataclass
class Projectile:
    origin: Vector3
    direction: Vector3
    speed: float
    damage: float
    lifetime: float = 0.18
    age: float = 0.0
    color: Tuple[float, float, float] = (1.0, 1.0, 0.2)


@dataclass
class MuzzleFlash:
    pos: Vector3
    lifetime: float = 0.06
    age: float = 0.0


@dataclass
class ShellCasing:
    pos: Vector3
    vel: Vector3
    lifetime: float = 1.5
    age: float = 0.0


# -----------------------------
# Weapon definitions
# -----------------------------

WEAPON_DEFS = {
    "Pistol": WeaponStats(
        name="Pistol",
        fire_rate=5.0,
        magazine_size=12,
        reload_time=1.0,
        damage=20.0,
        accuracy=0.85,
        range=40.0,
        pellet_count=1,
        projectile_speed=120.0,
        is_auto=False,
        aim_accuracy_bonus=0.05,
    ),
    "minigun": WeaponStats(
        name="minigun",
        fire_rate=100,
        magazine_size=400,
        reload_time=10.0,
        damage=5.0,
        accuracy=0.05,
        range=40.0,
        pellet_count=1,
        projectile_speed=120.0,
        is_auto=False,
        aim_accuracy_bonus=0.05,
    ),
    "AK47": WeaponStats(
        name="AK47",
        fire_rate=9.0,
        magazine_size=30,
        reload_time=1.6,
        damage=16.0,
        accuracy=0.8,
        range=50.0,
        pellet_count=1,
        projectile_speed=130.0,
        is_auto=True,
        aim_accuracy_bonus=0.1,
    ),
    "Spray Gun": WeaponStats(
        name="Spray Gun",
        fire_rate=14.0,
        magazine_size=40,
        reload_time=2.0,
        damage=8.0,
        accuracy=0.5,
        range=25.0,
        pellet_count=1,
        projectile_speed=100.0,
        is_auto=True,
        aim_accuracy_bonus=0.05,
    ),
    "Sniper": WeaponStats(
        name="Sniper",
        fire_rate=0.7,
        magazine_size=5,
        reload_time=2.5,
        damage=100.0,
        accuracy=0.85,
        range=80.0,
        pellet_count=1,
        projectile_speed=200.0,
        is_auto=False,
        aim_accuracy_bonus=0.25,
    ),
    "Shotgun": WeaponStats(
        name="Shotgun",
        fire_rate=1.2,
        magazine_size=8,
        reload_time=2.4,
        damage=12.0,  # per pellet
        accuracy=0.1,
        range=18.0,
        pellet_count=8,
        projectile_speed=90.0,
        is_auto=False,
        aim_accuracy_bonus=0.05,
        close_range_only=True,
    ),
}


class Weapon:
    """Stateful weapon with magazine, reload, and spread."""

    def __init__(self, stats: WeaponStats):
        self.stats = stats
        self.mag = stats.magazine_size
        self.reserve = stats.magazine_size * 4
        self.last_shot_time = 0.0
        self.reloading = False
        self.reload_end_time = 0.0

    def start_reload(self, now: float):
        if self.reloading:
            return
        if self.mag == self.stats.magazine_size:
            return
        if self.reserve <= 0:
            return
        self.reloading = True
        self.reload_end_time = now + self.stats.reload_time

    def update(self, now: float):
        if self.reloading and now >= self.reload_end_time:
            need = self.stats.magazine_size - self.mag
            to_load = min(need, self.reserve)
            self.mag += to_load
            self.reserve -= to_load
            self.reloading = False

    def can_fire(self, now: float) -> bool:
        if self.reloading or self.mag <= 0:
            return False
        delay = 1.0 / self.stats.fire_rate
        return (now - self.last_shot_time) >= delay

    def try_fire(
        self,
        now: float,
        origin: Vector3,
        direction: Vector3,
        is_aiming: bool,
        from_player: bool,
    ) -> Tuple[List[Projectile], Optional[MuzzleFlash], Optional[ShellCasing]]:
        """
        Fire weapon if possible. Returns (projectiles, muzzle_flash, shell)
        or empty if it can't fire yet.
        """
        self.update(now)
        if not self.can_fire(now):
            return [], None, None

        self.last_shot_time = now
        self.mag -= 1

        accuracy = self.stats.accuracy
        if is_aiming:
            accuracy = min(1.0, accuracy + self.stats.aim_accuracy_bonus)

        projectiles: List[Projectile] = []
        color = (1.0, 1.0, 0.2) if from_player else (1.0, 0.3, 0.3)
        spread_base = (1.0 - accuracy) * 0.12

        for _ in range(self.stats.pellet_count):
            dx = (random.random() * 2 - 1) * spread_base
            dy = (random.random() * 2 - 1) * spread_base
            dz = (random.random() * 2 - 1) * spread_base
            dir_spread = Vector3(
                direction.x + dx,
                direction.y + dy,
                direction.z + dz,
            )
            if dir_spread.length() == 0:
                dir_spread = direction
            else:
                dir_spread = dir_spread.normalize()

            projectiles.append(
                Projectile(
                    origin=origin.copy(),
                    direction=dir_spread,
                    speed=self.stats.projectile_speed,
                    damage=self.stats.damage,
                    color=color,
                )
            )

        flash = MuzzleFlash(pos=origin.copy())

        # simple shell ejection to the right + upward
        right = Vector3(direction.z, 0, -direction.x)
        if right.length() == 0:
            right = Vector3(1, 0, 0)
        else:
            right = right.normalize()
        vel = right * 4.0 + Vector3(0, 2.0, 0)
        shell = ShellCasing(pos=origin.copy(), vel=vel)

        return projectiles, flash, shell
