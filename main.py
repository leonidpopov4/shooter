# main.py
# Complete game loop + responsive menu for Blue Arena shooter (DUEL only),
# with RPG rockets that spawn ahead of the muzzle, grow an orange cube on impact,
# and the menu/UI restored to the previous responsive layout you liked.

import sys
import math
import random
import time

import pygame
from pygame.locals import (
    DOUBLEBUF, OPENGL,
    K_w, K_a, K_s, K_d,
    K_LSHIFT, K_ESCAPE, K_r,
    K_1, K_2,
    K_SPACE,
)
from pygame.math import Vector3

from OpenGL.GL import *
from OpenGL.GLU import *

from settings import (
    WIDTH, HEIGHT,
    FOV, NEAR_PLANE, FAR_PLANE,
    MOUSE_SENS, CAMERA_PITCH_LIMIT,
    MOVE_SPEED, SPRINT_MULTIPLIER,
)
from geometry import build_map_geometry, find_safe_spawn, move_with_collisions, OBSTACLES
from actors import Player, Bot, AI_PROFILES, AIProfile
from weapons import WEAPON_DEFS, Projectile, MuzzleFlash
from render import (
    draw_map_with_edges,
    draw_bot,
    draw_projectiles,
    draw_muzzle_flashes,
    draw_shells,
    draw_crosshair,
    draw_gun_ui,
    set_theme,
    get_theme,
    init_render_assets,
)
from shooting import ray_hits_actor


# -----------------------------
# Explosion cube with growth animation
# -----------------------------
class ExplosionCube:
    def __init__(self, pos: Vector3, start_size: float, target_size: float, lifetime: float, owner: str):
        self.pos = pos.copy()
        self.start_size = float(start_size)
        self.target_size = float(target_size)
        self.size = float(start_size)
        self.lifetime = float(lifetime)
        self.age = 0.0
        self.owner = owner  # 'player' or 'bot'
        self.damaged_player = False
        self.damaged_bots = set()  # indices of bots already damaged

    def half(self):
        return self.size * 0.5

    def contains_actor(self, actor_pos: Vector3, actor_radius: float) -> bool:
        # AABB check in X/Z and allow some vertical tolerance
        h = self.half()
        dx = abs(actor_pos.x - self.pos.x)
        dz = abs(actor_pos.z - self.pos.z)
        dy = abs(actor_pos.y - self.pos.y)
        vertical_limit = h + actor_radius + 0.5
        if dx <= (h + actor_radius) and dz <= (h + actor_radius) and dy <= vertical_limit:
            return True
        return False

    def update(self, dt: float):
        self.age += dt
        t = min(1.0, max(0.0, self.age / self.lifetime))
        # ease-out growth (smooth)
        ease = 1 - (1 - t) * (1 - t)
        self.size = self.start_size + (self.target_size - self.start_size) * ease

    def draw(self):
        s = self.half()
        x, y, z = self.pos.x, self.pos.y, self.pos.z
        glPushMatrix()
        glTranslatef(x, y, z)
        alpha = max(0.12, 0.9 * (1.0 - self.age / self.lifetime))
        glColor4f(1.0, 0.45, 0.0, alpha)
        # Draw cube centered at origin with side length self.size
        glBegin(GL_QUADS)
        # top face (+y)
        glVertex3f(-s, s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, s, s)
        glVertex3f(-s, s, s)
        # bottom face (-y)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, s)
        glVertex3f(s, -s, s)
        glVertex3f(s, -s, -s)
        # front (+z)
        glVertex3f(-s, -s, s)
        glVertex3f(-s, s, s)
        glVertex3f(s, s, s)
        glVertex3f(s, -s, s)
        # back (-z)
        glVertex3f(-s, -s, -s)
        glVertex3f(s, -s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(-s, s, -s)
        # right (+x)
        glVertex3f(s, -s, -s)
        glVertex3f(s, -s, s)
        glVertex3f(s, s, s)
        glVertex3f(s, s, -s)
        # left (-x)
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, s, -s)
        glVertex3f(-s, s, s)
        glVertex3f(-s, -s, s)
        glEnd()
        glPopMatrix()


# -----------------------------
# Duel-only
# -----------------------------
MODE_ID = "duel"
MODE_LABEL = "Duel (1v1, first to 5)"
DUEL_MAPS = ["White Arena", "Blue Arena", "Black Arena", "Backrooms"]


def show_menu():
    """
    Responsive menu UI (the improved layout you liked).
    Controls:
      - UP/DOWN (or W/S): select bot
      - LEFT/RIGHT (or A/D): select weapon
      - Q/E: change map
      - Z/X: decrease / increase difficulty (0..100)
      - ENTER: start
      - ESC: quit
    Returns: MODE_ID, bot_choice, weapon_choice, map_choice, difficulty_value (0..100)
    """
    pygame.init()
    screen = pygame.display.set_mode((900, 700))
    pygame.display.set_caption("Blue Arena - Menu")

    sw, sh = screen.get_size()

    title_font_size = max(36, int(sh * 0.10))
    option_font_size = max(20, int(sh * 0.055))
    hint_font_size = max(16, int(sh * 0.035))

    font_title = pygame.font.Font(None, title_font_size)
    font_option = pygame.font.Font(None, option_font_size)
    font_hint = pygame.font.Font(None, hint_font_size)

    bot_names = ["AK47 Bot", "Sniper Bot", "Shotgun Bot"]
    bot_index = 0

    weapon_names = list(WEAPON_DEFS.keys())
    weapon_index = 0

    map_index = 0

    difficulty_value = 50  # continuous 0..100
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    bot_index = (bot_index - 1) % len(bot_names)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    bot_index = (bot_index + 1) % len(bot_names)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    weapon_index = (weapon_index - 1) % len(weapon_names)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    weapon_index = (weapon_index + 1) % len(weapon_names)
                elif event.key == pygame.K_q:
                    map_index = (map_index - 1) % len(DUEL_MAPS)
                elif event.key == pygame.K_e:
                    map_index = (map_index + 1) % len(DUEL_MAPS)
                elif event.key == pygame.K_z:
                    difficulty_value = max(0, difficulty_value - 2)
                elif event.key == pygame.K_x:
                    difficulty_value = min(100, difficulty_value + 2)
                elif event.key == pygame.K_RETURN:
                    running = False

        # Clear + dynamic layout recompute
        screen.fill((16, 18, 25))
        sw, sh = screen.get_size()
        center_x = sw // 2

        # Larger vertical spacing to avoid overlap
        top_margin = int(sh * 0.06)
        section_spacing = int(sh * 0.115)
        small_spacing = int(sh * 0.02)

        title_y = top_margin
        mode_y = title_y + section_spacing
        bot_y = mode_y + section_spacing
        weapon_y = bot_y + section_spacing
        map_y = weapon_y + section_spacing
        slider_y = map_y + section_spacing
        hints_y = slider_y + int(section_spacing * 0.9)

        slider_w = int(sw * 0.60)
        slider_h = max(14, int(sh * 0.035))
        slider_x = center_x - slider_w // 2

        # Title
        title_surf = font_title.render("BLUE ARENA", True, (220, 235, 255))
        title_rect = title_surf.get_rect(center=(center_x, title_y + title_surf.get_height() // 2))
        screen.blit(title_surf, title_rect)

        # Mode
        mode_surf = font_option.render(f"Mode: {MODE_LABEL}", True, (180, 200, 240))
        mode_rect = mode_surf.get_rect(center=(center_x, mode_y + mode_surf.get_height() // 2))
        screen.blit(mode_surf, mode_rect)

        # Bot selection
        bot_text = f"Bot: {bot_names[bot_index]}"
        bot_surf = font_option.render(bot_text, True, (180, 200, 240))
        bot_rect = bot_surf.get_rect(center=(center_x, bot_y + bot_surf.get_height() // 2))
        screen.blit(bot_surf, bot_rect)

        # Weapon selection
        weapon_text = f"Primary: {weapon_names[weapon_index]}"
        weapon_surf = font_option.render(weapon_text, True, (180, 200, 240))
        weapon_rect = weapon_surf.get_rect(center=(center_x, weapon_y + weapon_surf.get_height() // 2))
        screen.blit(weapon_surf, weapon_rect)

        # Map selection
        map_name = DUEL_MAPS[map_index]
        map_text = f"Map: {map_name}"
        map_surf = font_option.render(map_text, True, (180, 200, 240))
        map_rect = map_surf.get_rect(center=(center_x, map_y + map_surf.get_height() // 2))
        screen.blit(map_surf, map_rect)

        # Difficulty slider UI
        outer_rect = pygame.Rect(slider_x - 4, slider_y - 4, slider_w + 8, slider_h + 8)
        pygame.draw.rect(screen, (24, 26, 32), outer_rect, border_radius=8)
        pygame.draw.rect(screen, (40, 44, 60), (slider_x, slider_y, slider_w, slider_h), border_radius=8)

        fill_w = int(slider_w * (difficulty_value / 100.0))
        pygame.draw.rect(screen, (96, 160, 255), (slider_x, slider_y, fill_w, slider_h), border_radius=8)

        knob_x = slider_x + fill_w
        knob_radius = max(8, int(slider_h * 0.9))
        pygame.draw.circle(
            screen,
            (220, 220, 220),
            (max(slider_x + 2, min(slider_x + slider_w - 2, knob_x)), slider_y + slider_h // 2),
            max(4, knob_radius // 2),
        )

        # Difficulty label
        percent_txt = font_option.render(f"Difficulty: {difficulty_value}%", True, (200, 220, 255))
        pct_rect = percent_txt.get_rect(center=(center_x, slider_y - int(slider_h * 1.6)))
        screen.blit(percent_txt, pct_rect)

        # Tag
        if difficulty_value < 33:
            tag = "Very Easy"
        elif difficulty_value < 66:
            tag = "Normal (previous Hard)"
        else:
            tag = "Very Hard"
        tag_txt = font_hint.render(tag, True, (220, 220, 220))
        tag_rect = tag_txt.get_rect(center=(center_x, slider_y + slider_h + int(small_spacing * 1.4)))
        screen.blit(tag_txt, tag_rect)

        # Ticks
        tick_values = [0, 25, 50, 75, 100]
        tick_margin = max(8, int(slider_w * 0.006))
        for v in tick_values:
            tx = slider_x + int(slider_w * (v / 100.0))
            tx = max(slider_x + tick_margin, min(slider_x + slider_w - tick_margin, tx))
            pygame.draw.line(screen, (200, 200, 200), (tx, slider_y), (tx, slider_y + slider_h), 2)
            txt = font_hint.render(str(v), True, (220, 220, 220))
            txt_rect = txt.get_rect(center=(tx, slider_y + slider_h + int(small_spacing * 3)))
            screen.blit(txt, txt_rect)

        # Hints
        hint_lines = [
            "Z/X: Difficulty    UP/DOWN: Bot    LEFT/RIGHT: Primary    Q/E: Map",
            "In game: 1=Primary  2=Pistol   RMB=Aim   LMB=Fire   R=Reload   ENTER: Start",
        ]
        base_hint_y = hints_y + int(small_spacing * 2)
        for i, line in enumerate(hint_lines):
            hint_surf = font_hint.render(line, True, (150, 170, 210))
            hint_rect = hint_surf.get_rect(center=(center_x, base_hint_y + i * (hint_surf.get_height() + 6)))
            screen.blit(hint_surf, hint_rect)

        pygame.display.flip()
        clock.tick(60)

    bot_choice = bot_names[bot_index]
    weapon_choice = weapon_names[weapon_index]
    map_choice = DUEL_MAPS[map_index]

    pygame.quit()
    return MODE_ID, bot_choice, weapon_choice, map_choice, difficulty_value


def draw_health_and_score(
        player: Player,
        bot: Bot,
        player_kills: int,
        bot_kills: int,
        player_wins: int,
        matches_played: int,
):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)

    max_hp = 100.0
    p_hp = max(0.0, min(max_hp, player.health))
    b_hp = max(0.0, min(max_hp, bot.health))

    bar_w = 220
    bar_h = 18
    margin = 18

    x = margin
    y = HEIGHT - margin - bar_h

    glColor3f(0.08, 0.08, 0.08)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + bar_w, y)
    glVertex2f(x + bar_w, y + bar_h)
    glVertex2f(x, y + bar_h)
    glEnd()

    fill_w = bar_w * (p_hp / max_hp)
    glColor3f(0.2, 0.9, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + fill_w, y)
    glVertex2f(x + fill_w, y + bar_h)
    glVertex2f(x, y + bar_h)
    glEnd()

    glColor3f(0.0, 0.0, 0.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x, y)
    glVertex2f(x + bar_w, y)
    glVertex2f(x + bar_w, y + bar_h)
    glVertex2f(x, y + bar_h)
    glEnd()

    x2 = WIDTH - margin - bar_w
    y2 = HEIGHT - margin - bar_h
    glColor3f(0.08, 0.08, 0.08)
    glBegin(GL_QUADS)
    glVertex2f(x2, y2)
    glVertex2f(x2 + bar_w, y2)
    glVertex2f(x2 + bar_w, y2 + bar_h)
    glVertex2f(x2, y2 + bar_h)
    glEnd()

    fill_w2 = bar_w * (b_hp / max_hp)
    glColor3f(0.9, 0.25, 0.25)
    glBegin(GL_QUADS)
    glVertex2f(x2, y2)
    glVertex2f(x2 + fill_w2, y2)
    glVertex2f(x2 + fill_w2, y2 + bar_h)
    glVertex2f(x2, y2 + bar_h)
    glEnd()

    glColor3f(0.0, 0.0, 0.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(x2, y2)
    glVertex2f(x2 + bar_w, y2)
    glVertex2f(x2 + bar_w, y2 + bar_h)
    glVertex2f(x2, y2 + bar_h)
    glEnd()

    sq = 10
    gap = 4
    ky = y - sq - 6
    kx = x
    for i in range(5):
        if i < player_kills:
            glColor3f(0.2, 0.9, 0.2)
        else:
            glColor3f(0.15, 0.3, 0.15)
        sx0 = kx + i * (sq + gap)
        sy0 = ky
        glBegin(GL_QUADS)
        glVertex2f(sx0, sy0)
        glVertex2f(sx0 + sq, sy0)
        glVertex2f(sx0 + sq, sy0 + sq)
        glVertex2f(sx0, sy0 + sq)
        glEnd()

    ky2 = y2 - sq - 6
    kx2 = x2 + bar_w - 5 * (sq + gap)
    for i in range(5):
        if i < bot_kills:
            glColor3f(0.9, 0.25, 0.25)
        else:
            glColor3f(0.3, 0.15, 0.15)
        sx0 = kx2 + i * (sq + gap)
        sy0 = ky2
        glBegin(GL_QUADS)
        glVertex2f(sx0, sy0)
        glVertex2f(sx0 + sq, sy0)
        glVertex2f(sx0 + sq, sy0 + sq)
        glVertex2f(sx0, sy0 + sq)
        glEnd()

    wr_w = 160
    wr_h = 10
    wr_x = (WIDTH - wr_w) / 2
    wr_y = HEIGHT - margin - bar_h - 28

    glColor3f(0.08, 0.08, 0.08)
    glBegin(GL_QUADS)
    glVertex2f(wr_x, wr_y)
    glVertex2f(wr_x + wr_w, wr_y)
    glVertex2f(wr_x + wr_w, wr_y + wr_h)
    glVertex2f(wr_x, wr_y + wr_h)
    glEnd()

    win_rate = 0.0
    if matches_played > 0:
        win_rate = max(0.0, min(1.0, player_wins / matches_played))
    fill_wr = wr_w * win_rate
    glColor3f(0.25, 0.5, 0.95)
    glBegin(GL_QUADS)
    glVertex2f(wr_x, wr_y)
    glVertex2f(wr_x + fill_wr, wr_y)
    glVertex2f(wr_x + fill_wr, wr_y + wr_h)
    glVertex2f(wr_x, wr_y + wr_h)
    glEnd()

    glColor3f(0.0, 0.0, 0.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(wr_x, wr_y)
    glVertex2f(wr_x + wr_w, wr_y)
    glVertex2f(wr_x + wr_w, wr_y + wr_h)
    glVertex2f(wr_x, wr_y + wr_h)
    glEnd()

    glEnable(GL_DEPTH_TEST)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def run_game(mode_id: str, bot_profile_name: str, start_weapon_name: str, map_name: str, difficulty_value: int):
    pygame.init()
    pygame.display.set_caption("Blue Arena Shooter")
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    glEnable(GL_DEPTH_TEST)

    set_theme(map_name)
    theme = get_theme(map_name)
    sky = theme["sky_color"]
    glClearColor(sky[0], sky[1], sky[2], 1.0)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV, WIDTH / HEIGHT, NEAR_PLANE, FAR_PLANE)
    glMatrixMode(GL_MODELVIEW)

    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    init_render_assets()
    clock = pygame.time.Clock()

    build_map_geometry(map_name)

    # Spawns + actors (duel)
    player_candidates = [
        Vector3(-9.0, 1.0, -9.0),
        Vector3(-9.0, 1.0, 9.0),
        Vector3(9.0, 1.0, -9.0),
        Vector3(9.0, 1.0, 9.0),
        Vector3(-7.0, 1.0, 0.0),
        Vector3(7.0, 1.0, 0.0),
    ]
    bot_candidates = [
        Vector3(9.0, 1.0, 9.0),
        Vector3(9.0, 1.0, -9.0),
        Vector3(-9.0, 1.0, 9.0),
        Vector3(7.0, 1.0, 0.0),
    ]

    player_start = find_safe_spawn(player_candidates, radius=0.55)
    bot_start = find_safe_spawn(bot_candidates, radius=0.55)

    player = Player(pos=player_start, start_weapon=start_weapon_name)
    bot_profile = AI_PROFILES.get(bot_profile_name, AI_PROFILES["AK47 Bot"])
    bots = [Bot(pos=bot_start, profile=bot_profile)]

    player_spawn = player.pos.copy()
    bot_spawn = bots[0].pos.copy()

    projectiles = []
    flashes = []
    shells = []
    explosions = []

    # Stats
    player_kills = 0
    bot_kills = 0
    player_wins = 0
    matches_played = 0

    last_time = pygame.time.get_ticks() / 1000.0

    # Map difficulty mapping
    d_raw = float(difficulty_value) / 100.0
    exponent = 0.46
    d = d_raw ** exponent

    # Parameter ranges
    acc_low, acc_high = 0.45, 1.45
    speed_low, speed_high = 0.65, 1.25
    aim_time_long, aim_time_short = 1.25, 0.05
    shoot_chance_low, shoot_chance_high = 0.35, 1.25
    peek_mult_low, peek_mult_high = 0.45, 1.35
    tactical_threshold_low, tactical_threshold_high = 1.4, 0.7

    acc_mult = acc_low + (acc_high - acc_low) * d
    speed_mult = speed_low + (speed_high - speed_low) * d
    aim_time_base = aim_time_long + (aim_time_short - aim_time_long) * d
    shoot_chance_mult = shoot_chance_low + (shoot_chance_high - shoot_chance_low) * d
    peek_mult = peek_mult_low + (peek_mult_high - peek_mult_low) * d
    tactical_threshold_mult = tactical_threshold_low + (tactical_threshold_high - tactical_threshold_low) * d

    for b in bots:
        b.profile.accuracy = max(0.02, min(1.0, b.profile.accuracy * acc_mult))
        b.profile.move_speed = max(1.0, b.profile.move_speed * speed_mult)
        if hasattr(b.profile, "aggression"):
            b.profile.aggression = max(0.0, min(1.0, getattr(b.profile, "aggression", 0.7) * (0.85 + d * 0.3)))

    # Smarter bot AI setup
    now_init = pygame.time.get_ticks() / 1000.0
    bot_ai_rand = {
        "strafe_dir": random.choice([-1, 1]),
        "next_strafe_switch": now_init + random.uniform(0.7, 2.2),
        "pause_until": 0.0,
        "is_paused": False,
        "zigzag_active": False,
        "next_zigzag_time": now_init + random.uniform(2, 6),
        "peek_cooldown_until": now_init + random.uniform(0.5, 1.5),
        "is_peeking": False,
        "peek_end": 0.0,
        "is_reloading_tactical": False,
        "reload_backoff_until": 0.0,
        "panic_until": 0.0,
        "is_aiming": False,
        "aim_end_time": 0.0,
        "aim_target_dir": Vector3(0, 0, -1),
    }

    left_mouse_down = False
    running = True
    user_requested_quit = False

    # helper: create explosion cube and apply immediate touch damage
    def create_explosion_cube(pos: Vector3, target_size: float, owner: str):
        nonlocal player_kills, bot_kills
        cube = ExplosionCube(pos, start_size=0.2, target_size=max(0.6, target_size), lifetime=0.45, owner=owner)
        explosions.append(cube)
        # immediate touch damage if touching right away
        if cube.contains_actor(player.pos, player.radius) and not cube.damaged_player:
            player.health -= 50.0
            cube.damaged_player = True
            if player.health <= 0 and owner == "bot":
                bot_kills += 1
        for i, other in enumerate(bots):
            if other.health <= 0:
                continue
            if cube.contains_actor(other.pos, other.radius) and i not in cube.damaged_bots:
                other.health -= 50.0
                cube.damaged_bots.add(i)
                if other.health <= 0 and owner == "player":
                    player_kills += 1

    # main loop
    while running:
        now = pygame.time.get_ticks() / 1000.0
        dt = max(0.0001, now - last_time)
        last_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                user_requested_quit = True
            elif event.type == pygame.KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                    user_requested_quit = True
                elif event.key == K_r:
                    player.weapon.start_reload(now)
                elif event.key == K_1:
                    player.switch_to_primary()
                elif event.key == K_2:
                    player.switch_to_secondary()
                elif event.key == K_SPACE:
                    if player.on_ground:
                        player.vel_y = 6.0
                        player.on_ground = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    left_mouse_down = True
                elif event.button == 3:
                    player.is_aiming = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    left_mouse_down = False
                elif event.button == 3:
                    player.is_aiming = False

        # Mouse look
        mx, my = pygame.mouse.get_rel()
        player.yaw += mx * MOUSE_SENS
        player.pitch -= my * MOUSE_SENS
        player.pitch = max(-CAMERA_PITCH_LIMIT, min(CAMERA_PITCH_LIMIT, player.pitch))

        # Movement
        keys = pygame.key.get_pressed()
        move_dir = Vector3(0, 0, 0)
        yaw_rad = math.radians(player.yaw)
        forward_flat = Vector3(math.sin(yaw_rad), 0, -math.cos(yaw_rad))
        right_flat = Vector3(-forward_flat.z, 0, forward_flat.x)

        if keys[K_w]:
            move_dir += forward_flat
        if keys[K_s]:
            move_dir -= forward_flat
        if keys[K_a]:
            move_dir -= right_flat
        if keys[K_d]:
            move_dir += right_flat

        if move_dir.length() > 0:
            move_dir = move_dir.normalize()
            speed = MOVE_SPEED * (SPRINT_MULTIPLIER if keys[K_LSHIFT] else 1.0)
            move_vec = move_dir * speed * dt
            player.pos = move_with_collisions(player.pos, move_vec, player.radius)

        if not player.on_ground:
            player.vel_y -= 12.0 * dt
            player.jump_offset += player.vel_y * dt
            if player.jump_offset <= 0.0:
                player.jump_offset = 0.0
                player.vel_y = 0.0
                player.on_ground = True

        player.weapon.update(now)

        # -----------------
        # Player shooting
        # -----------------
        if left_mouse_down:
            origin = Vector3(player.pos.x, player.eye_y, player.pos.z)
            direction = player.forward()
            new_proj, new_flash, new_shell = player.weapon.try_fire(
                now, origin, direction,
                is_aiming=player.is_aiming,
                from_player=True,
            )
            if new_proj:
                for p in new_proj:
                    # Immediate hits for hitscan projectiles only
                    if getattr(p, "is_hitscan", True):
                        for enemy in bots:
                            if enemy.health <= 0:
                                continue
                            if ray_hits_actor(p.origin, p.direction, player.weapon.stats.range, enemy):
                                was_alive = enemy.health > 0
                                enemy.health -= p.damage
                                if was_alive and enemy.health <= 0:
                                    player_kills += 1
                projectiles.extend(new_proj)
                if new_flash:
                    flashes.append(new_flash)
                if new_shell:
                    jitter = Vector3(
                        (random.random() - 0.5) * 0.6,
                        (random.random() - 0.5) * 0.4,
                        (random.random() - 0.5) * 0.6,
                    )
                    new_shell.vel += jitter
                    shells.append(new_shell)

        # -----------------
        # Bot AI (duel)
        # -----------------
        for bot_index_local, b in enumerate(bots):
            if b.health <= 0:
                continue
            if hasattr(b, "update_ai"):
                ai_proj, ai_flash, ai_shell = b.update_ai(dt, now, player)
                if ai_proj:
                    hitscan_proj = [p for p in ai_proj if getattr(p, "is_hitscan", True)]
                    if hitscan_proj and b._has_line_of_sight(player):
                        to_player = player.pos - b.pos
                        dist = to_player.length()
                        if dist <= b.weapon.stats.range:
                            total_damage = sum(p.damage for p in hitscan_proj) * 1.2
                            was_alive = player.health > 0
                            player.health -= total_damage
                            if was_alive and player.health <= 0:
                                bot_kills += 1
                    projectiles.extend(ai_proj)
                if ai_flash:
                    flashes.append(ai_flash)
                if ai_shell:
                    jitter = Vector3(
                        (random.random() - 0.5) * 0.6,
                        (random.random() - 0.5) * 0.4,
                        (random.random() - 0.5) * 0.6,
                    )
                    ai_shell.vel += jitter
                    shells.append(ai_shell)

        # -----------------
        # Update projectiles & check impacts. Ignore owner collisions briefly after spawn.
        # -----------------
        owner_grace = 0.12  # seconds to ignore owner collisions after spawn
        new_projectile_list = []
        for p in projectiles:
            p.age += dt
            p.origin += p.direction * p.speed * dt

            if not getattr(p, "is_hitscan", True):
                impacted = False
                # world collision
                check_radius = 0.15
                for ob in OBSTACLES:
                    min_x = min(ob.x1, ob.x2) - check_radius
                    max_x = max(ob.x1, ob.x2) + check_radius
                    min_z = min(ob.z1, ob.z2) - check_radius
                    max_z = max(ob.z1, ob.z2) + check_radius
                    if (min_x <= p.origin.x <= max_x) and (min_z <= p.origin.z <= max_z):
                        create_explosion_cube(p.origin, target_size=(p.explosion_radius or 1.6), owner=(p.owner or "bot"))
                        impacted = True
                        break
                if impacted:
                    continue

                # player collision (skip if owner is player and within grace time)
                if player.health > 0:
                    if not (p.owner == "player" and (now - p.creation_time) < owner_grace):
                        to_player = player.pos - p.origin
                        if to_player.length() <= (player.radius + 0.25):
                            create_explosion_cube(p.origin, target_size=(p.explosion_radius or 1.6), owner=(p.owner or "bot"))
                            continue

                # bots collision (skip their own rockets during grace)
                hit_bot = False
                for i, other in enumerate(bots):
                    if other.health <= 0:
                        continue
                    if not (p.owner == "bot" and (now - p.creation_time) < owner_grace):
                        to_bot = other.pos - p.origin
                        if to_bot.length() <= (other.radius + 0.25):
                            create_explosion_cube(p.origin, target_size=(p.explosion_radius or 1.6), owner=(p.owner or "player"))
                            hit_bot = True
                            break
                if hit_bot:
                    continue

                # keep rocket alive until lifetime
                if p.age <= p.lifetime:
                    new_projectile_list.append(p)
            else:
                # keep hitscan visuals
                if p.age <= p.lifetime:
                    new_projectile_list.append(p)

        projectiles = new_projectile_list

        # update flashes
        for f in flashes:
            f.age += dt
        flashes = [f for f in flashes if f.age <= f.lifetime]

        # update shells
        for s in shells:
            s.age += dt
            s.vel.y -= 9.8 * dt
            s.pos += s.vel * dt

            if s.pos.y < 0.0:
                s.pos.y = 0.0
                s.vel.x *= 0.6
                s.vel.z *= 0.6
                s.vel.y *= -0.3

            shell_radius = 0.05
            for ob in OBSTACLES:
                min_x = min(ob.x1, ob.x2) - shell_radius
                max_x = max(ob.x1, ob.x2) + shell_radius
                min_z = min(ob.z1, ob.z2) - shell_radius
                max_z = max(ob.z1, ob.z2) + shell_radius

                if (min_x <= s.pos.x <= max_x) and (min_z <= s.pos.z <= max_z):
                    overlap_right = max_x - s.pos.x
                    overlap_left = s.pos.x - min_x
                    overlap_fwd = max_z - s.pos.z
                    overlap_back = s.pos.z - min_z

                    direction, _ = min(
                        [
                            ("right", overlap_right),
                            ("left", overlap_left),
                            ("forward", overlap_fwd),
                            ("back", overlap_back),
                        ],
                        key=lambda kv: kv[1],
                    )

                    bounciness = 0.4
                    friction = 0.9

                    if direction == "right":
                        s.pos.x = max_x
                        s.vel.x = abs(s.vel.x) * bounciness
                        s.vel.z *= friction
                    elif direction == "left":
                        s.pos.x = min_x
                        s.vel.x = -abs(s.vel.x) * bounciness
                        s.vel.z *= friction
                    elif direction == "forward":
                        s.pos.z = max_z
                        s.vel.z = abs(s.vel.z) * bounciness
                        s.vel.x *= friction
                    else:
                        s.pos.z = min_z
                        s.vel.z = -abs(s.vel.z) * bounciness
                        s.vel.x *= friction

        shells = [s for s in shells if s.age <= s.lifetime]

        # update explosions: grow and apply damage once per actor when they touch
        new_explosions = []
        for ex in explosions:
            ex.update(dt)
            # player
            if not ex.damaged_player and player.health > 0 and ex.contains_actor(player.pos, player.radius):
                player.health -= 50.0
                ex.damaged_player = True
                if player.health <= 0 and ex.owner == "bot":
                    bot_kills += 1
            # bots
            for i, other in enumerate(bots):
                if other.health <= 0:
                    continue
                if i in ex.damaged_bots:
                    continue
                if ex.contains_actor(other.pos, other.radius):
                    other.health -= 50.0
                    ex.damaged_bots.add(i)
                    if other.health <= 0 and ex.owner == "player":
                        player_kills += 1
            if ex.age <= ex.lifetime:
                new_explosions.append(ex)
        explosions = new_explosions

        # respawns
        if bots:
            b0 = bots[0]
            if b0.health <= 0:
                b0.health = 100.0
                b0.pos = bot_spawn.copy()
        if player.health <= 0:
            player.health = 100.0
            player.pos = player_spawn.copy()
            player.jump_offset = 0.0
            player.vel_y = 0.0
            player.on_ground = True

        # duel match tracking
        if player_kills >= 5 or bot_kills >= 5:
            matches_played += 1
            if player_kills >= 5:
                player_wins += 1

            # reset for next match
            player_kills = 0
            bot_kills = 0
            player.health = 100.0
            for b in bots:
                b.health = 100.0
            player.pos = player_spawn.copy()
            for b in bots:
                b.pos = bot_spawn.copy()
            player.jump_offset = 0.0
            player.vel_y = 0.0
            player.on_ground = True

            if matches_played >= 10:
                running = False
                user_requested_quit = False
                break

        # Render
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        fwd = player.forward()
        eye_y = player.eye_y
        eye = (player.pos.x, eye_y, player.pos.z)
        center = (player.pos.x + fwd.x, eye_y + fwd.y, player.pos.z + fwd.z)
        gluLookAt(*eye, *center, 0.0, 1.0, 0.0)

        draw_map_with_edges()
        for b in bots:
            if b.health > 0:
                draw_bot(b)
        draw_projectiles(projectiles)
        draw_muzzle_flashes(flashes)
        draw_shells(shells)

        # draw explosion cubes
        for ex in explosions:
            ex.draw()

        first_bot = bots[0] if bots else None
        draw_health_and_score(
            player, first_bot,
            player_kills, bot_kills,
            player_wins, matches_played,
        )

        draw_gun_ui(player.current_weapon_name)
        draw_crosshair()

        pygame.display.flip()
        clock.tick(120)

    pygame.quit()
    if user_requested_quit:
        return False
    return True


if __name__ == "__main__":
    # Main loop: show menu -> run game -> if run_game returns True, go back to menu,
    # if it returns False, quit.
    while True:
        mode_id, bot_name, weapon_name, map_name, difficulty_value = show_menu()
        cont = run_game(mode_id, bot_name, weapon_name, map_name, difficulty_value)
        if not cont:
            break
    pygame.quit()
    sys.exit(0)
