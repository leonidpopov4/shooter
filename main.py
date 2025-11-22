# main.py
# Game loop + menu for Blue Arena shooter (Duel + FFA with bot-vs-bot).

import sys
import math
import random

import pygame
from pygame.locals import (
    DOUBLEBUF, OPENGL,
    K_w, K_a, K_s, K_d,
    K_LSHIFT, K_ESCAPE, K_r,
    K_1, K_2,
    K_SPACE, K_TAB,
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
from weapons import WEAPON_DEFS
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
# Modes / maps
# -----------------------------

MODE_IDS = ["duel", "ffa"]
MODE_LABELS = {
    "duel": "Duel (1v1, first to 5)",
    "ffa": "Free For All (10 bots)",
}

DUEL_MAPS = ["White Arena", "Blue Arena", "Black Arena", "Backrooms"]
FFA_MAP_NAME = "FFA Black"  # uses big spawn ring in run_game


# -----------------------------
# Menu
# -----------------------------

def show_menu():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Blue Arena - Menu")

    font_title = pygame.font.Font(None, 64)
    font_option = pygame.font.Font(None, 32)
    font_hint = pygame.font.Font(None, 24)

    mode_index = 0  # 0 = duel, 1 = ffa
    bot_names = ["AK47 Bot", "Sniper Bot", "Shotgun Bot"]
    bot_index = 0

    weapon_names = list(WEAPON_DEFS.keys())
    weapon_index = 0

    map_index = 0  # for Duel maps only

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

                elif event.key == pygame.K_TAB:
                    mode_index = 1 - mode_index

                elif event.key in (pygame.K_UP, pygame.K_w):
                    bot_index = (bot_index - 1) % len(bot_names)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    bot_index = (bot_index + 1) % len(bot_names)

                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    weapon_index = (weapon_index - 1) % len(weapon_names)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    weapon_index = (weapon_index + 1) % len(weapon_names)

                elif event.key == pygame.K_q:
                    if MODE_IDS[mode_index] == "duel":
                        map_index = (map_index - 1) % len(DUEL_MAPS)
                elif event.key == pygame.K_e:
                    if MODE_IDS[mode_index] == "duel":
                        map_index = (map_index + 1) % len(DUEL_MAPS)

                elif event.key == pygame.K_RETURN:
                    running = False

        screen.fill((16, 18, 25))

        mode_id = MODE_IDS[mode_index]
        mode_label = MODE_LABELS[mode_id]

        title_surf = pygame.font.Font(None, 64).render("BLUE ARENA", True, (220, 235, 255))
        title_rect = title_surf.get_rect(center=(400, 80))
        screen.blit(title_surf, title_rect)

        mode_surf = font_option.render(f"Mode: {mode_label}", True, (180, 200, 240))
        mode_rect = mode_surf.get_rect(center=(400, 170))
        screen.blit(mode_surf, mode_rect)

        bot_text = f"Bot: {bot_names[bot_index]}"
        if mode_id == "ffa":
            bot_text += " (RANDOM in FFA)"
        bot_surf = font_option.render(bot_text, True, (180, 200, 240))
        bot_rect = bot_surf.get_rect(center=(400, 220))
        screen.blit(bot_surf, bot_rect)

        weapon_text = f"Primary: {weapon_names[weapon_index]}"
        weapon_surf = font_option.render(weapon_text, True, (180, 200, 240))
        weapon_rect = weapon_surf.get_rect(center=(400, 270))
        screen.blit(weapon_surf, weapon_rect)

        if mode_id == "duel":
            map_name = DUEL_MAPS[map_index]
        else:
            map_name = FFA_MAP_NAME + " (HUGE!)"
        map_text = f"Map: {map_name}"
        map_surf = font_option.render(map_text, True, (180, 200, 240))
        map_rect = map_surf.get_rect(center=(400, 320))
        screen.blit(map_surf, map_rect)

        hint_surf = font_hint.render(
            "TAB: Mode   UP/DOWN: Bot   LEFT/RIGHT: Primary   Q/E: Map (Duel only)",
            True,
            (150, 170, 210),
        )
        hint_rect = hint_surf.get_rect(center=(400, 380))
        screen.blit(hint_surf, hint_rect)

        controls_surf = font_hint.render(
            "In game: 1=Primary 2=Pistol RMB=Aim LMB=Fire R=Reload TAB=Scores(FFA)",
            True,
            (140, 160, 200),
        )
        controls_rect = controls_surf.get_rect(center=(400, 410))
        screen.blit(controls_surf, controls_rect)

        start_surf = font_hint.render(
            "ENTER: Start   ESC: Quit",
            True,
            (170, 190, 220),
        )
        start_rect = start_surf.get_rect(center=(400, 450))
        screen.blit(start_surf, start_rect)

        pygame.display.flip()
        clock.tick(60)

    mode_id = MODE_IDS[mode_index]
    bot_choice = bot_names[bot_index]
    weapon_choice = weapon_names[weapon_index]
    if mode_id == "duel":
        map_choice = DUEL_MAPS[map_index]
    else:
        map_choice = FFA_MAP_NAME

    pygame.quit()
    return mode_id, bot_choice, weapon_choice, map_choice


# -----------------------------
# HP + Scoreboard overlay (Duel)
# -----------------------------

def draw_health_and_score(
        player: Player,
        bot: Bot | None,
        mode_id: str,
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
    b_hp = max_hp
    if bot is not None:
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

    if mode_id == "duel" and bot is not None:
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


# -----------------------------
# Leaderboard overlay (FFA)
# -----------------------------

def draw_leaderboard(kill_counts, show_full=False):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, 0, HEIGHT, -1, 1)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glDisable(GL_DEPTH_TEST)

    sorted_entries = sorted(kill_counts.items(), key=lambda x: x[1], reverse=True)

    if show_full:
        panel_w = 400
        panel_h = 450
        panel_x = (WIDTH - panel_w) / 2
        panel_y = (HEIGHT - panel_h) / 2

        glColor4f(0.0, 0.0, 0.0, 0.85)
        glBegin(GL_QUADS)
        glVertex2f(panel_x, panel_y)
        glVertex2f(panel_x + panel_w, panel_y)
        glVertex2f(panel_x + panel_w, panel_y + panel_h)
        glVertex2f(panel_x, panel_y + panel_h)
        glEnd()

        glColor3f(0.3, 0.5, 0.9)
        glLineWidth(3.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(panel_x, panel_y)
        glVertex2f(panel_x + panel_w, panel_y)
        glVertex2f(panel_x + panel_w, panel_y + panel_h)
        glVertex2f(panel_x, panel_y + panel_h)
        glEnd()

    else:
        panel_w = 200
        panel_h = 160
        panel_x = WIDTH - panel_w - 20
        panel_y = HEIGHT - panel_h - 20

        glColor4f(0.0, 0.0, 0.0, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(panel_x, panel_y)
        glVertex2f(panel_x + panel_w, panel_y)
        glVertex2f(panel_x + panel_w, panel_y + panel_h)
        glVertex2f(panel_x, panel_y + panel_h)
        glEnd()

        glColor3f(0.5, 0.5, 0.5)
        glLineWidth(1.5)
        glBegin(GL_LINE_LOOP)
        glVertex2f(panel_x, panel_y)
        glVertex2f(panel_x + panel_w, panel_y)
        glVertex2f(panel_x + panel_w, panel_y + panel_h)
        glVertex2f(panel_x, panel_y + panel_h)
        glEnd()

    glEnable(GL_DEPTH_TEST)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    font_size = 22 if show_full else 18
    font = pygame.font.Font(None, font_size)

    if show_full:
        title = font.render("LEADERBOARD", True, (255, 255, 255))
        title_x = int((WIDTH - title.get_width()) / 2)
        title_y = int((HEIGHT - panel_h) / 2 + 15)
    else:
        title = font.render("TOP 5", True, (220, 220, 220))
        title_x = int(WIDTH - panel_w + 15)
        title_y = int(HEIGHT - panel_h + 8)

    screen = pygame.display.get_surface()
    screen.blit(title, (title_x, title_y))

    max_display = len(sorted_entries) if show_full else min(5, len(sorted_entries))

    for i, (name, kills) in enumerate(sorted_entries[:max_display]):
        color = (255, 215, 0) if i == 0 else (220, 220, 220)
        text = font.render(f"{i + 1}. {name}: {kills}", True, color)

        if show_full:
            text_x = int((WIDTH - panel_w) / 2 + 25)
            text_y = int((HEIGHT - panel_h) / 2 + 55 + i * 32)
        else:
            text_x = int(WIDTH - panel_w + 15)
            text_y = int(HEIGHT - panel_h + 38 + i * 26)

        screen.blit(text, (text_x, text_y))


# -----------------------------
# Game loop
# -----------------------------

def run_game(mode_id: str, bot_profile_name: str, start_weapon_name: str, map_name: str):
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

    # -----------------
    # Spawns + actors
    # -----------------

    if mode_id == "duel":
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

        duel_bot_spawn_points = bot_candidates
        ffa_bot_spawn_points = None
        ffa_player_spawn_points = None

    else:  # FFA
        # Big ring of 10 spawn locations
        spawn_points = [
            Vector3(-24.0, 1.0, -24.0),
            Vector3(24.0, 1.0, -24.0),
            Vector3(-24.0, 1.0, 24.0),
            Vector3(24.0, 1.0, 24.0),
            Vector3(0.0, 1.0, -28.0),
            Vector3(0.0, 1.0, 28.0),
            Vector3(-28.0, 1.0, 0.0),
            Vector3(28.0, 1.0, 0.0),
            Vector3(-14.0, 1.0, -14.0),
            Vector3(14.0, 1.0, 14.0),
        ]

        player_start = find_safe_spawn(spawn_points, radius=0.55)
        player = Player(pos=player_start, start_weapon=start_weapon_name)

        bots = []
        weapon_choices = list(WEAPON_DEFS.keys())

        for i in range(10):
            pos = find_safe_spawn(spawn_points, radius=0.55)
            random_weapon = random.choice(weapon_choices)

            profile = AIProfile(
                name=f"Bot{i + 1}",
                weapon=random_weapon,
                move_speed=random.uniform(5.5, 8.0),
                preferred_min=random.uniform(4.0, 8.0),
                preferred_max=random.uniform(10.0, 18.0),
                aim_time=random.uniform(0.2, 0.5),
                accuracy=random.uniform(0.65, 0.9),
                aggression=random.uniform(0.5, 1.0),
            )

            bot = Bot(pos=pos, profile=profile)
            bot.bot_id = i
            bots.append(bot)

        duel_bot_spawn_points = None
        ffa_bot_spawn_points = spawn_points
        ffa_player_spawn_points = spawn_points

    player_spawn = player.pos.copy()
    if mode_id == "duel":
        bot_spawn = bots[0].pos.copy()
    else:
        bot_spawn = None

    projectiles = []
    flashes = []
    shells = []

    # Stats
    player_kills = 0
    bot_kills = 0
    player_wins = 0
    matches_played = 0

    # FFA leaderboard
    kill_counts = {}
    if mode_id == "ffa":
        kill_counts = {"You": 0}
        for i in range(10):
            kill_counts[f"Bot{i + 1}"] = 0

    last_time = pygame.time.get_ticks() / 1000.0
    left_mouse_down = False
    show_leaderboard_full = False
    running = True

    while running:
        now = pygame.time.get_ticks() / 1000.0
        dt = max(0.0001, now - last_time)
        last_time = now

        # -----------------
        # Input
        # -----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False

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

                elif event.key == K_TAB:
                    if mode_id == "ffa":
                        show_leaderboard_full = not show_leaderboard_full

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

        # Gravity / jump
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
                    for enemy in bots:
                        if enemy.health <= 0:
                            continue
                        if ray_hits_actor(p.origin, p.direction, player.weapon.stats.range, enemy):
                            was_alive = enemy.health > 0
                            enemy.health -= p.damage
                            if was_alive and enemy.health <= 0:
                                if mode_id == "duel":
                                    player_kills += 1
                                else:
                                    kill_counts["You"] += 1

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
        # Bot AI
        # -----------------
        for bot_index, b in enumerate(bots):
            if b.health <= 0:
                continue

            if mode_id == "duel":
                # Duel: use original state-machine AI against player only
                ai_proj, ai_flash, ai_shell = b.update_ai(dt, now, player)

                if ai_proj:
                    if b._has_line_of_sight(player):
                        to_player = player.pos - b.pos
                        dist = to_player.length()
                        if dist <= b.weapon.stats.range:
                            total_damage = sum(p.damage for p in ai_proj) * 1.2
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

            else:
                # -------- FFA: simple bot-vs-bot + player AI ----------
                closest_target = None
                closest_dist = 999999.0

                # Consider player
                if player.health > 0:
                    to_player = player.pos - b.pos
                    d = to_player.length()
                    if d < closest_dist:
                        closest_dist = d
                        closest_target = player

                # Consider other bots
                for other_index, other_bot in enumerate(bots):
                    if other_index == bot_index or other_bot.health <= 0:
                        continue
                    to_other = other_bot.pos - b.pos
                    d = to_other.length()
                    if d < closest_dist:
                        closest_dist = d
                        closest_target = other_bot

                if closest_target is None:
                    continue

                # Update weapon reloads / timers
                b.weapon.update(now)

                # Direction to target
                to_tgt = closest_target.pos - b.pos
                dist = to_tgt.length()
                if dist > 0:
                    dir_to_tgt = to_tgt.normalize()
                else:
                    dir_to_tgt = Vector3(0, 0, -1)

                # Face target
                b.yaw = math.degrees(math.atan2(dir_to_tgt.x, -dir_to_tgt.z))

                # Movement: keep preferred distance + strafe
                move_vec = Vector3(0, 0, 0)
                if dist > b.profile.preferred_max:
                    move_vec += dir_to_tgt          # move in
                elif dist < b.profile.preferred_min:
                    move_vec -= dir_to_tgt          # back up

                # Strafe left/right
                right = Vector3(-dir_to_tgt.z, 0, dir_to_tgt.x)
                if right.length() > 0:
                    right = right.normalize()
                    strafe_sign = 1.0 if (int(now * 1.5 + bot_index) % 2 == 0) else -1.0
                    move_vec += right * strafe_sign * 0.4

                if move_vec.length() > 0:
                    move_vec = move_vec.normalize()
                    move_vec *= b.profile.move_speed * dt
                    b.pos = move_with_collisions(b.pos, move_vec, b.radius)

                ai_proj = []
                ai_flash = None
                ai_shell = None

                # Fire only if we see the target and are in range
                if b._has_line_of_sight(closest_target) and dist <= b.weapon.stats.range * 1.05:
                    origin = b.pos + Vector3(0, 0.8, 0)

                    acc = b.profile.accuracy
                    if random.random() <= acc:
                        aim_dir = dir_to_tgt
                    else:
                        aim_dir = Vector3(
                            dir_to_tgt.x + (random.random() * 2 - 1) * 0.35,
                            dir_to_tgt.y + (random.random() * 2 - 1) * 0.12,
                            dir_to_tgt.z + (random.random() * 2 - 1) * 0.35,
                        )
                        if aim_dir.length() == 0:
                            aim_dir = dir_to_tgt
                        else:
                            aim_dir = aim_dir.normalize()

                    ai_proj, ai_flash, ai_shell = b.weapon.try_fire(
                        now, origin, aim_dir,
                        is_aiming=True,
                        from_player=False,
                    )

                if ai_proj:
                    # Simple hitscan-style damage on the chosen target
                    total_damage = sum(p.damage for p in ai_proj) * 1.2
                    was_alive = closest_target.health > 0
                    closest_target.health -= total_damage

                    if was_alive and closest_target.health <= 0:
                        killer_name = b.profile.name
                        if killer_name not in kill_counts:
                            kill_counts[killer_name] = 0
                        kill_counts[killer_name] += 1

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
        # Update visual FX
        # -----------------
        for p in projectiles:
            p.age += dt
            p.origin += p.direction * p.speed * dt
        projectiles = [p for p in projectiles if p.age <= p.lifetime]

        for f in flashes:
            f.age += dt
        flashes = [f for f in flashes if f.age <= f.lifetime]

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

        # -----------------
        # Respawns
        # -----------------
        if mode_id == "duel":
            b = bots[0]
            if b.health <= 0:
                b.health = 100.0
                b.pos = bot_spawn.copy()
        else:
            for b in bots:
                if b.health <= 0:
                    b.health = 100.0
                    if ffa_bot_spawn_points:
                        b.pos = find_safe_spawn(ffa_bot_spawn_points, radius=b.radius)

        if player.health <= 0:
            player.health = 100.0
            if mode_id == "duel":
                player.pos = player_spawn.copy()
            else:
                if ffa_player_spawn_points:
                    player.pos = find_safe_spawn(ffa_player_spawn_points, radius=player.radius)
            player.jump_offset = 0.0
            player.vel_y = 0.0
            player.on_ground = True

        # -----------------
        # Duel win condition
        # -----------------
        if mode_id == "duel":
            if player_kills >= 5 or bot_kills >= 5:
                matches_played += 1
                if player_kills >= 5:
                    player_wins += 1

                player_kills = 0
                bot_kills = 0

                player.health = 100.0
                bots[0].health = 100.0
                player.pos = player_spawn.copy()
                bots[0].pos = bot_spawn.copy()
                player.jump_offset = 0.0
                player.vel_y = 0.0
                player.on_ground = True

        # -----------------
        # Render
        # -----------------
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

        if mode_id == "duel":
            first_bot = bots[0] if bots else None
            draw_health_and_score(
                player, first_bot, mode_id,
                player_kills, bot_kills,
                player_wins, matches_played,
            )
        else:
            draw_leaderboard(kill_counts, show_full=show_leaderboard_full)

        draw_gun_ui(player.current_weapon_name)
        draw_crosshair()

        pygame.display.flip()
        clock.tick(120)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    mode_id, bot_name, weapon_name, map_name = show_menu()
    run_game(mode_id, bot_name, weapon_name, map_name)
