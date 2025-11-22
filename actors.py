# actors.py
# Player, Bot and AI profiles for Blue Arena shooter.

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from pygame.math import Vector3

from weapons import Weapon, WEAPON_DEFS, Projectile, MuzzleFlash, ShellCasing
from geometry import move_with_collisions, OBSTACLES


# -----------------------------
# AI profiles
# -----------------------------

@dataclass
class AIProfile:
    name: str
    weapon: str
    move_speed: float
    preferred_min: float
    preferred_max: float
    aim_time: float
    accuracy: float
    aggression: float  # 0–1


AI_PROFILES: Dict[str, AIProfile] = {
    "AK47 Bot": AIProfile(
        name="AK47 Bot",
        weapon="AK47",
        move_speed=6.5,
        preferred_min=6.0,
        preferred_max=13.0,
        aim_time=0.25,
        accuracy=0.4,
        aggression=0.6,
    ),
    "Sniper Bot": AIProfile(
        name="Sniper Bot",
        weapon="Sniper",
        move_speed=4.0,
        preferred_min=12.0,
        preferred_max=20.0,
        aim_time=0.8,
        accuracy=0.85,
        aggression=0.3,
    ),
    "sweat": AIProfile(
        name="no life",
        weapon="Sniper",
        move_speed=7.5,
        preferred_min=1.0,
        preferred_max=10.0,
        aim_time=0.1,
        accuracy=100,
        aggression=1.0,
    ),
    "Shotgun Bot": AIProfile(
        name="Shotgun Bot",
        weapon="Shotgun",
        move_speed=8.5,
        preferred_min=0.0,
        preferred_max=6.0,
        aim_time=0.2,
        accuracy=0.9,
        aggression=1.0,
    ),
}


# -----------------------------
# Base actor
# -----------------------------

@dataclass
class Actor:
    pos: Vector3
    yaw: float
    pitch: float
    health: float
    radius: float = 0.6   # collision radius

    def forward(self) -> Vector3:
        """Convert yaw/pitch into a normalized forward vector."""
        ry = math.radians(self.yaw)
        rp = math.radians(self.pitch)
        x = math.cos(rp) * math.sin(ry)
        y = math.sin(rp)
        z = -math.cos(rp) * math.cos(ry)
        v = Vector3(x, y, z)
        if v.length() == 0:
            return Vector3(0, 0, -1)
        return v.normalize()


# -----------------------------
# Player (2-weapon inventory)
# -----------------------------

class Player(Actor):
    """
    Player has two weapons:
      - primary: chosen in the menu (AK47 / Sniper / Spray Gun / Shotgun / etc)
      - secondary: always Pistol

    1 -> primary
    2 -> pistol
    """

    def __init__(self, pos: Vector3, start_weapon: str = "Pistol"):
        super().__init__(pos=pos, yaw=45.0, pitch=0.0, health=100.0, radius=0.55)

        # Aiming (right mouse button)
        self.is_aiming: bool = False

        # Jump / camera bob
        self.base_height = pos.y
        self.jump_offset = 0.0
        self.vel_y = 0.0
        self.on_ground = True

        # Inventory: always have pistol + one primary
        self.weapons: Dict[str, Weapon] = {}

        # Secondary = pistol
        self.weapons["Pistol"] = Weapon(WEAPON_DEFS["Pistol"])
        self.secondary_name: str = "Pistol"

        # Primary from menu (fallback to AK if something weird)
        if start_weapon not in WEAPON_DEFS:
            start_weapon = "AK47"
        if start_weapon != "Pistol":
            self.weapons[start_weapon] = Weapon(WEAPON_DEFS[start_weapon])
        self.primary_name: str = start_weapon

        # 0 = primary, 1 = secondary
        self.active_slot: int = 0

    # --- inventory helpers ---

    @property
    def current_weapon_name(self) -> str:
        return self.primary_name if self.active_slot == 0 else self.secondary_name

    @property
    def weapon(self) -> Weapon:
        """Current active weapon (used by main.py as player.weapon)."""
        return self.weapons[self.current_weapon_name]

    def switch_to_primary(self) -> None:
        self.active_slot = 0

    def switch_to_secondary(self) -> None:
        self.active_slot = 1

    def set_weapon(self, name: str) -> None:
        """
        Backwards-compatible helper so old code like player.set_weapon("AK47")
        still works. Also used when pressing 1/2 in some older versions.
        """
        if name == "Pistol":
            self.switch_to_secondary()
            return

        if name not in WEAPON_DEFS:
            return

        if name not in self.weapons:
            self.weapons[name] = Weapon(WEAPON_DEFS[name])

        self.primary_name = name
        self.active_slot = 0

    @property
    def eye_y(self) -> float:
        """Camera height (base + jump bob)."""
        return self.base_height + self.jump_offset


# -----------------------------
# Bot
# -----------------------------

class Bot(Actor):
    def __init__(self, pos: Vector3, profile: AIProfile):
        super().__init__(pos=pos, yaw=-135.0, pitch=0.0, health=100.0, radius=0.6)
        self.profile = profile
        self.weapon = Weapon(WEAPON_DEFS[profile.weapon])
        self.state = "seek"
        self.aim_timer = 0.0
        self.strafe_dir = 1.0

    # ----- line of sight -----

    def _has_line_of_sight(self, player: Player) -> bool:
        """Ray vs map obstacles on X/Z to see if we can see the player."""
        origin = self.pos + Vector3(0, 0.8, 0)
        dir_vec = (player.pos - self.pos)
        dist = dir_vec.length()
        if dist <= 0.0:
            return False

        direction = dir_vec.normalize()
        max_range = dist + 0.1

        for ob in OBSTACLES:
            min_x = min(ob.x1, ob.x2)
            max_x = max(ob.x1, ob.x2)
            min_z = min(ob.z1, ob.z2)
            max_z = max(ob.z1, ob.z2)

            t0 = 0.0
            t1 = max_range

            # X slab
            if abs(direction.x) < 1e-6:
                if not (min_x <= origin.x <= max_x):
                    continue
            else:
                invx = 1.0 / direction.x
                a = (min_x - origin.x) * invx
                b = (max_x - origin.x) * invx
                if a > b:
                    a, b = b, a
                t0 = max(t0, a)
                t1 = min(t1, b)
                if t1 < t0:
                    continue

            # Z slab
            if abs(direction.z) < 1e-6:
                if not (min_z <= origin.z <= max_z):
                    continue
            else:
                invz = 1.0 / direction.z
                a = (min_z - origin.z) * invz
                b = (max_z - origin.z) * invz
                if a > b:
                    a, b = b, a
                t0 = max(t0, a)
                t1 = min(t1, b)
                if t1 < t0:
                    continue

            # Hit an obstacle before the player
            if 0.0 <= t0 <= max_range:
                return False

        return True

    # ----- AI state machine -----

    def update_ai(
        self,
        dt: float,
        now: float,
        player: Player,
    ) -> Tuple[List[Projectile], MuzzleFlash | None, ShellCasing | None]:
        proj_list: List[Projectile] = []
        flash = None
        shell = None

        to_target = player.pos - self.pos
        dist = to_target.length()
        dir_to_target = to_target.normalize() if dist > 0 else Vector3(0, 0, -1)

        # Face player
        self.yaw = math.degrees(math.atan2(dir_to_target.x, -dir_to_target.z))

        has_los = self._has_line_of_sight(player)

        # Movement: keep distance + strafe
        move_dir = Vector3(0, 0, 0)
        if dist > self.profile.preferred_max:
            move_dir += dir_to_target
        elif dist < self.profile.preferred_min:
            move_dir -= dir_to_target

        if has_los:
            right = Vector3(dir_to_target.z, 0, -dir_to_target.x)
            if random.random() < 0.01:
                self.strafe_dir *= -1.0
            move_dir += right * self.strafe_dir * 0.4

        if move_dir.length() > 0:
            move_dir = move_dir.normalize()
            move_vec = move_dir * self.profile.move_speed * dt
            self.pos = move_with_collisions(self.pos, move_vec, self.radius)

        # Weapon timers
        self.weapon.update(now)

        # --- State machine ---
        if self.state == "seek":
            if has_los and dist <= self.profile.preferred_max + 1.5:
                self.state = "aim"
                self.aim_timer = 0.0

        elif self.state == "aim":
            if not has_los:
                self.state = "seek"
            else:
                self.aim_timer += dt
                if self.aim_timer >= self.profile.aim_time:
                    self.state = "fire"

        elif self.state == "fire":
            stats = self.weapon.stats
            if stats.close_range_only and dist > stats.range:
                self.state = "seek"
            else:
                origin = self.pos + Vector3(0, 0.8, 0)

                acc = self.profile.accuracy
                if random.random() <= acc:
                    aim_dir = dir_to_target
                else:
                    aim_dir = Vector3(
                        dir_to_target.x + (random.random() * 2 - 1) * 0.35,
                        dir_to_target.y + (random.random() * 2 - 1) * 0.12,
                        dir_to_target.z + (random.random() * 2 - 1) * 0.35,
                    ).normalize()

                new_proj, new_flash, new_shell = self.weapon.try_fire(
                    now, origin, aim_dir,
                    is_aiming=True, from_player=False
                )

                if new_proj:
                    proj_list.extend(new_proj)
                    flash = new_flash
                    shell = new_shell

                    if self.weapon.mag == 0 and self.weapon.reserve > 0:
                        self.weapon.start_reload(now)
                        self.state = "reload"
                    else:
                        self.state = "aim"
                        self.aim_timer = 0.0
                else:
                    self.state = "aim"
                    self.aim_timer = 0.0

        elif self.state == "reload":
            if not self.weapon.reloading:
                self.state = "seek"

        return proj_list, flash, shell
