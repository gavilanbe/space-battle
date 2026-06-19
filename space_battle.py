#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║   COSMIC DEFENDER  ·  Terminal Space Battle                   ║
║   Shoot'em up con inercia, fuego con gradiente y jefes         ║
╚═══════════════════════════════════════════════════════════════╝
"""

import curses
import random
import time
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════
# PALETA DE COLOR
# ═══════════════════════════════════════════════════════════════
# Pares de color. Si la terminal soporta 256 colores usamos una
# paleta rica (fuego con gradiente real); si no, caemos a 8 colores.

class C:
    PLAYER       = 1
    PLAYER_HOT   = 2
    ENEMY        = 3
    ENEMY_WARM   = 4   # tanks / élites
    ENEMY_DIVE   = 5   # kamikazes
    BULLET       = 6
    BULLET_ENEMY = 7
    POWERUP      = 8
    STAR_FAR     = 9
    STAR_NEAR    = 10
    STAR_BLUE    = 11
    UI           = 12
    UI_ACCENT    = 13
    BOSS         = 14
    BOSS_CORE    = 15
    SHIELD       = 16
    NEBULA       = 17
    # gradiente de fuego (caliente -> frío)
    FIRE_WHITE   = 18
    FIRE_YELLOW  = 19
    FIRE_ORANGE  = 20
    FIRE_RED     = 21
    SMOKE        = 22
    COMBO        = 23
    HEAL         = 24

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    rich = curses.COLORS >= 256

    def pair(idx, fg256, fg8):
        curses.init_pair(idx, fg256 if rich else fg8, -1)

    pair(C.PLAYER,       51,  curses.COLOR_CYAN)
    pair(C.PLAYER_HOT,   123, curses.COLOR_WHITE)
    pair(C.ENEMY,        203, curses.COLOR_RED)
    pair(C.ENEMY_WARM,   208, curses.COLOR_YELLOW)
    pair(C.ENEMY_DIVE,   201, curses.COLOR_MAGENTA)
    pair(C.BULLET,       227, curses.COLOR_YELLOW)
    pair(C.BULLET_ENEMY, 213, curses.COLOR_MAGENTA)
    pair(C.POWERUP,      46,  curses.COLOR_GREEN)
    pair(C.STAR_FAR,     239, curses.COLOR_WHITE)
    pair(C.STAR_NEAR,    255, curses.COLOR_WHITE)
    pair(C.STAR_BLUE,    111, curses.COLOR_CYAN)
    pair(C.UI,           111, curses.COLOR_CYAN)
    pair(C.UI_ACCENT,    213, curses.COLOR_MAGENTA)
    pair(C.BOSS,         171, curses.COLOR_MAGENTA)
    pair(C.BOSS_CORE,    214, curses.COLOR_RED)
    pair(C.SHIELD,       45,  curses.COLOR_BLUE)
    pair(C.NEBULA,       60,  curses.COLOR_BLUE)
    pair(C.FIRE_WHITE,   231, curses.COLOR_WHITE)
    pair(C.FIRE_YELLOW,  226, curses.COLOR_YELLOW)
    pair(C.FIRE_ORANGE,  208, curses.COLOR_YELLOW)
    pair(C.FIRE_RED,     196, curses.COLOR_RED)
    pair(C.SMOKE,        242, curses.COLOR_WHITE)
    pair(C.COMBO,        220, curses.COLOR_YELLOW)
    pair(C.HEAL,         48,  curses.COLOR_GREEN)


# ═══════════════════════════════════════════════════════════════
# ARTE
# ═══════════════════════════════════════════════════════════════

SHIP_ART = [
    "  ▲  ",
    " ▟█▙ ",
    "▟███▙",
    "▘▀█▀▘",
]
SHIP_W = 5
SHIP_H = 4

# llamas del propulsor (animadas por frame)
THRUST_FRAMES = [
    ["▝▼▘"],
    ["▝▽▘"],
    [" ▼ "],
]

ENEMY_TYPES = {
    'scout': {
        'art': ["◢▆◣"],
        'health': 1, 'points': 100, 'speed': 0.45,
        'color': C.ENEMY, 'behavior': 'sine', 'fire': 0.004,
    },
    'fighter': {
        'art': ["◣▼◢", "▝█▘"],
        'health': 2, 'points': 180, 'speed': 0.32,
        'color': C.ENEMY, 'behavior': 'zigzag', 'fire': 0.012,
    },
    'darter': {
        'art': ["▕█▏", "╲▼╱"],
        'health': 1, 'points': 250, 'speed': 0.7,
        'color': C.ENEMY_DIVE, 'behavior': 'dive', 'fire': 0.0,
    },
    'tank': {
        'art': ["▛▀▀▀▜", "▌███▐", "▙▄▄▄▟"],
        'health': 6, 'points': 400, 'speed': 0.14,
        'color': C.ENEMY_WARM, 'behavior': 'straight', 'fire': 0.018,
    },
    'boss': {
        'art': [
            " ▟██████████▙ ",
            "▟████◤  ◥████▙",
            "███  ◉  ◉  ███",
            "████▄██████▄███",
            "▜███ ▼▼▼▼ ███▛",
            " ▜██▙▂▂▂▂▟██▛ ",
            "   ▀▀    ▀▀   ",
        ],
        'health': 60, 'points': 6000, 'speed': 0.05,
        'color': C.BOSS, 'behavior': 'boss', 'fire': 0.0,
    },
}

POWERUP_TYPES = {
    'power':  {'symbol': '⊕', 'color': C.POWERUP, 'label': 'ARMA+'},
    'shield': {'symbol': '⊛', 'color': C.SHIELD,  'label': 'ESCUDO'},
    'rapid':  {'symbol': '↯', 'color': C.BULLET,  'label': 'RÁPIDO'},
    'bomb':   {'symbol': '✺', 'color': C.UI_ACCENT,'label': 'BOMBA'},
    'life':   {'symbol': '♥', 'color': C.HEAL,    'label': 'VIDA'},
}

FIRE_CHARS_HOT  = ['@', '●', '◉', '█']
FIRE_CHARS_MID  = ['*', '✦', '◆', '+']
FIRE_CHARS_COOL = ['·', '˙', '.', '°']


# ═══════════════════════════════════════════════════════════════
# ENTIDADES
# ═══════════════════════════════════════════════════════════════

@dataclass
class Particle:
    x: float; y: float
    vx: float; vy: float
    life: int; max_life: int
    kind: str = 'fire'          # fire | spark | engine | smoke | debris
    glyph: Optional[str] = None
    color: Optional[int] = None

@dataclass
class Star:
    x: float; y: float
    speed: float
    char: str
    color: int

@dataclass
class Nebula:
    x: float; y: float
    speed: float
    cells: list                  # [(dx,dy,char)]

@dataclass
class Bullet:
    x: float; y: float
    vx: float; vy: float
    damage: int = 1
    friendly: bool = True
    glyph: str = '|'
    color: int = C.BULLET

@dataclass
class Enemy:
    x: float; y: float
    type: str
    health: int
    max_health: int
    shoot_cooldown: int = 0
    phase: float = 0.0
    hit_flash: int = 0
    vx: float = 0.0
    # boss
    attack: int = 0
    attack_timer: int = 0
    telegraph: int = 0

@dataclass
class PowerUp:
    x: float; y: float
    type: str
    phase: float = 0.0

@dataclass
class Explosion:
    x: float; y: float
    frame: float = 0.0
    max_frames: int = 6

@dataclass
class Shockwave:
    x: float; y: float
    r: float = 0.5
    max_r: float = 8.0
    color: int = C.FIRE_ORANGE

@dataclass
class Popup:
    x: float; y: float
    text: str
    life: int
    color: int


@dataclass
class Player:
    x: float; y: float
    vx: float = 0.0
    vy: float = 0.0
    lives: int = 3
    score: int = 0
    weapon: int = 1            # 1..5 nivel de arma
    shield: int = 0
    rapid_fire: int = 0
    invincible: int = 0
    shoot_cooldown: int = 0
    bombs: int = 1
    fire_hold: int = 0


# ═══════════════════════════════════════════════════════════════
# JUEGO
# ═══════════════════════════════════════════════════════════════

class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.setup_curses()
        self.height, self.width = stdscr.getmaxyx()
        self.reset()

    def reset(self):
        self.player = Player(x=self.width / 2 - SHIP_W / 2, y=self.height - 7)
        self.bullets: List[Bullet] = []
        self.enemies: List[Enemy] = []
        self.powerups: List[PowerUp] = []
        self.particles: List[Particle] = []
        self.explosions: List[Explosion] = []
        self.shockwaves: List[Shockwave] = []
        self.popups: List[Popup] = []
        self.stars: List[Star] = []
        self.nebulae: List[Nebula] = []

        self.wave = 1
        self.wave_timer = 0
        self.boss_spawned = False
        self.boss_active = False
        self.game_over = False
        self.paused = False
        self.frame = 0
        self.combo = 0
        self.combo_timer = 0
        self.shake_frames = 0
        self.shake_power = 0
        self.flash = 0
        self.flash_color = C.FIRE_WHITE
        self.wave_banner = 90
        self.init_starfield()

    def setup_curses(self):
        init_colors()
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)

    # ── fondo ──────────────────────────────────────────────────
    def init_starfield(self):
        for _ in range(70):
            layer = random.random()
            if layer < 0.5:
                speed, char, color = random.uniform(0.06, 0.14), random.choice(['·', '.']), C.STAR_FAR
            elif layer < 0.85:
                speed, char, color = random.uniform(0.18, 0.32), random.choice(['*', '✦', '∗']), C.STAR_NEAR
            else:
                speed, char, color = random.uniform(0.35, 0.6), random.choice(['★', '✧', '✦']), C.STAR_BLUE
            self.stars.append(Star(
                x=random.uniform(0, self.width - 1),
                y=random.uniform(0, self.height),
                speed=speed, char=char, color=color,
            ))
        for _ in range(3):
            self.spawn_nebula(random.uniform(0, self.height))

    def spawn_nebula(self, y):
        cx = random.randint(2, max(3, self.width - 12))
        cells = []
        glyphs = ['░', '▒', '·', '∴', '∵']
        for _ in range(random.randint(14, 26)):
            dx = random.randint(-6, 6)
            dy = random.randint(-3, 3)
            cells.append((dx, dy, random.choice(glyphs)))
        self.nebulae.append(Nebula(x=cx, y=y, speed=random.uniform(0.04, 0.09), cells=cells))

    # ── spawning ───────────────────────────────────────────────
    def spawn_enemy(self):
        if self.wave % 4 == 0 and not self.boss_spawned:
            hp = ENEMY_TYPES['boss']['health'] + self.wave * 6
            art = ENEMY_TYPES['boss']['art']
            self.enemies.append(Enemy(
                x=self.width / 2 - len(art[0]) / 2, y=2.0,
                type='boss', health=hp, max_health=hp, attack_timer=120,
            ))
            self.boss_spawned = True
            self.boss_active = True
            self.popup_center("⚠  JEFE  ⚠", C.BOSS_CORE)
            return

        roster = ['scout', 'fighter', 'darter', 'tank']
        weights = [
            max(8, 55 - self.wave * 3),
            25 + self.wave * 2,
            12 + self.wave,
            8 + self.wave,
        ]
        etype = random.choices(roster, weights=weights, k=1)[0]
        info = ENEMY_TYPES[etype]
        w = len(info['art'][0])
        self.enemies.append(Enemy(
            x=random.randint(1, max(1, self.width - w - 1)),
            y=random.uniform(-4, -1),
            type=etype, health=info['health'], max_health=info['health'],
            phase=random.uniform(0, math.tau),
        ))

    def maybe_spawn_powerup(self, x, y, force=False):
        if force or random.random() < 0.16:
            # ponderar: armas/escudo comunes, vida rara
            ptype = random.choices(
                ['power', 'shield', 'rapid', 'bomb', 'life'],
                weights=[34, 24, 22, 12, 8], k=1)[0]
            self.powerups.append(PowerUp(x=x, y=y, type=ptype))

    # ── efectos ────────────────────────────────────────────────
    def add_shake(self, power):
        self.shake_power = max(self.shake_power, power)
        self.shake_frames = max(self.shake_frames, power * 3)

    def screen_flash(self, color, frames=2):
        self.flash = max(self.flash, frames)
        self.flash_color = color

    def explode(self, x, y, intensity=1, shock=False):
        self.explosions.append(Explosion(x=x, y=y, max_frames=6))
        self.add_shake(intensity)
        n = intensity * 10
        if len(self.particles) < 600:
            for _ in range(n):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(0.4, 1.8) * (0.7 + intensity * 0.3)
                ml = random.randint(8, 18 + intensity * 3)
                self.particles.append(Particle(
                    x=x, y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd * 0.6,
                    life=ml, max_life=ml, kind='fire',
                ))
            # debris
            for _ in range(intensity * 3):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(1.0, 2.6)
                ml = random.randint(10, 20)
                self.particles.append(Particle(
                    x=x, y=y, vx=math.cos(ang) * spd, vy=math.sin(ang) * spd * 0.6,
                    life=ml, max_life=ml, kind='debris',
                    glyph=random.choice(['▖', '▘', '▝', '▗', '◢', '◣', '◤', '◥']),
                ))
        if shock:
            self.shockwaves.append(Shockwave(x=x, y=y, max_r=intensity * 5 + 4))

    def popup(self, x, y, text, color):
        self.popups.append(Popup(x=x, y=y, text=text, life=30, color=color))

    def popup_center(self, text, color):
        self.popup(self.width / 2 - len(text) / 2, self.height / 2 - 3, text, color)

    # ── input ──────────────────────────────────────────────────
    def handle_input(self):
        keys = []
        while True:
            try:
                k = self.stdscr.getch()
            except Exception:
                break
            if k == -1:
                break
            keys.append(k)

        for k in keys:
            if k in (ord('q'), 27):
                return False
            if k == ord('p'):
                self.paused = not self.paused
            if k == ord('r') and self.game_over:
                self.reset()
                return True

        if self.paused or self.game_over:
            return True

        accel = 0.85
        for k in keys:
            if k in (curses.KEY_LEFT, ord('a')):
                self.player.vx -= accel
            elif k in (curses.KEY_RIGHT, ord('d')):
                self.player.vx += accel
            elif k in (curses.KEY_UP, ord('w')):
                self.player.vy -= accel
            elif k in (curses.KEY_DOWN, ord('s')):
                self.player.vy += accel
            elif k == ord(' '):
                self.player.fire_hold = 6      # se mantiene con auto-repeat
            elif k == ord('b'):
                self.use_bomb()
        return True

    # ── armas ──────────────────────────────────────────────────
    def shoot(self):
        p = self.player
        if p.shoot_cooldown > 0:
            return
        p.shoot_cooldown = 4 if p.rapid_fire > 0 else 8
        cx = p.x + SHIP_W / 2
        top = p.y - 1
        lvl = p.weapon

        shots = []
        if lvl == 1:
            shots = [(0, -1.8)]
        elif lvl == 2:
            shots = [(-1, -1.8), (1, -1.8)]
        elif lvl == 3:
            shots = [(0, -1.9), (-1.5, -1.7), (1.5, -1.7)]
        elif lvl == 4:
            shots = [(-0.6, -1.9), (0.6, -1.9), (-2.0, -1.5), (2.0, -1.5)]
        else:  # 5
            shots = [(0, -2.0), (-1.2, -1.8), (1.2, -1.8), (-2.4, -1.4), (2.4, -1.4)]

        for vx, vy in shots:
            self.bullets.append(Bullet(
                x=cx + vx * 0.6, y=top, vx=vx * 0.5, vy=vy,
                damage=1, glyph='┃' if lvl < 4 else '╏', color=C.BULLET,
            ))
        # fogonazo
        for _ in range(3):
            self.particles.append(Particle(
                x=cx + random.uniform(-1, 1), y=top,
                vx=random.uniform(-0.3, 0.3), vy=-0.6,
                life=4, max_life=4, kind='spark', color=C.FIRE_WHITE,
            ))

    def use_bomb(self):
        if self.player.bombs <= 0 or not self.enemies:
            return
        self.player.bombs -= 1
        self.screen_flash(C.FIRE_WHITE, 2)
        self.add_shake(4)
        self.shockwaves.append(Shockwave(
            x=self.player.x + SHIP_W / 2, y=self.player.y,
            max_r=max(self.width, self.height), color=C.FIRE_YELLOW))
        for e in self.enemies[:]:
            info = ENEMY_TYPES[e.type]
            if e.type == 'boss':
                e.health -= 15
                e.hit_flash = 4
                self.explode(e.x + len(info['art'][0]) / 2, e.y + 2, 2)
                continue
            self.explode(e.x + len(info['art'][0]) / 2, e.y + len(info['art']) / 2, 2)
            self.player.score += info['points']
            self.enemies.remove(e)
        # limpiar balas enemigas
        self.bullets = [b for b in self.bullets if b.friendly]

    def enemy_shoot(self, e: Enemy):
        info = ENEMY_TYPES[e.type]
        art = info['art']
        cx = e.x + len(art[0]) / 2
        by = e.y + len(art)
        # apuntar al jugador
        px = self.player.x + SHIP_W / 2
        dx = px - cx
        dist = max(1.0, abs(dx))
        aim_vx = (dx / dist) * 0.5
        self.bullets.append(Bullet(
            x=cx, y=by, vx=aim_vx, vy=0.55,
            friendly=False, glyph='•', color=C.BULLET_ENEMY,
        ))
        e.shoot_cooldown = random.randint(50, 110)

    def boss_attack(self, e: Enemy):
        info = ENEMY_TYPES['boss']
        cx = e.x + len(info['art'][0]) / 2
        by = e.y + len(info['art'])
        px = self.player.x + SHIP_W / 2
        pat = e.attack % 3
        if pat == 0:      # abanico
            for off in range(-3, 4):
                self.bullets.append(Bullet(
                    x=cx, y=by, vx=off * 0.18, vy=0.7,
                    friendly=False, glyph='◦', color=C.BULLET_ENEMY))
        elif pat == 1:    # ráfaga dirigida
            dx = px - cx
            dist = max(1.0, math.hypot(dx, 6))
            for s in (-1, 0, 1):
                self.bullets.append(Bullet(
                    x=cx + s, y=by, vx=(dx / dist) * 0.7, vy=0.7,
                    friendly=False, glyph='✦', color=C.BULLET_ENEMY))
        else:             # lluvia
            for _ in range(5):
                self.bullets.append(Bullet(
                    x=cx + random.uniform(-6, 6), y=by,
                    vx=random.uniform(-0.2, 0.2), vy=random.uniform(0.5, 0.9),
                    friendly=False, glyph='•', color=C.BULLET_ENEMY))
        e.attack += 1

    # ── update ─────────────────────────────────────────────────
    def update(self):
        if self.paused or self.game_over:
            return
        self.frame += 1
        p = self.player

        # timers
        for attr in ('shoot_cooldown', 'shield', 'rapid_fire', 'invincible', 'fire_hold'):
            v = getattr(p, attr)
            if v > 0:
                setattr(p, attr, v - 1)
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0
        if self.shake_frames > 0:
            self.shake_frames -= 1
        else:
            self.shake_power = 0
        if self.flash > 0:
            self.flash -= 1
        if self.wave_banner > 0:
            self.wave_banner -= 1

        # física del jugador (inercia)
        p.vx *= 0.80
        p.vy *= 0.80
        p.vx = max(-2.4, min(2.4, p.vx))
        p.vy = max(-2.0, min(2.0, p.vy))
        p.x += p.vx
        p.y += p.vy
        p.x = max(0, min(self.width - SHIP_W, p.x))
        p.y = max(2, min(self.height - SHIP_H - 1, p.y))

        # propulsor
        if self.frame % 2 == 0 and len(self.particles) < 500:
            spread = abs(p.vx) * 0.4
            self.particles.append(Particle(
                x=p.x + SHIP_W / 2 + random.uniform(-0.8, 0.8) - p.vx * 0.3,
                y=p.y + SHIP_H - 0.5,
                vx=-p.vx * 0.3 + random.uniform(-spread, spread),
                vy=0.4 + random.uniform(0, 0.3),
                life=random.randint(3, 6), max_life=6, kind='engine',
            ))

        # disparo continuo
        if p.fire_hold > 0:
            self.shoot()

        # spawn enemigos
        self.wave_timer += 1
        spawn_rate = max(22, 90 - self.wave * 4)
        if (not self.boss_active and self.wave_timer >= spawn_rate
                and len(self.enemies) < 8 + self.wave):
            self.spawn_enemy()
            self.wave_timer = 0

        # avanzar de oleada
        if not self.enemies and self.wave_timer > 70 and self.wave_banner <= 0:
            self.wave += 1
            self.boss_spawned = False
            self.boss_active = False
            self.wave_timer = 0
            self.wave_banner = 80
            self.popup_center(f"OLEADA {self.wave}", C.UI_ACCENT)

        self.update_background()
        self.update_bullets()
        self.update_enemies()
        self.update_powerups()
        self.update_particles()
        self.update_explosions()
        self.update_shockwaves()
        self.update_popups()
        self.check_collisions()

    def update_background(self):
        for s in self.stars:
            s.y += s.speed
            if s.y >= self.height:
                s.y = 0
                s.x = random.uniform(0, self.width - 1)
        for n in self.nebulae[:]:
            n.y += n.speed
            if n.y - 4 >= self.height:
                self.nebulae.remove(n)
                self.spawn_nebula(-4)

    def update_bullets(self):
        for b in self.bullets[:]:
            b.x += b.vx
            b.y += b.vy
            # estela
            if b.friendly and self.frame % 2 == 0 and len(self.particles) < 500:
                self.particles.append(Particle(
                    x=b.x, y=b.y + 0.5, vx=0, vy=0.3,
                    life=3, max_life=3, kind='spark', color=C.FIRE_ORANGE))
            if not (0 <= b.y < self.height and -2 <= b.x < self.width + 2):
                self.bullets.remove(b)

    def update_enemies(self):
        p = self.player
        for e in self.enemies[:]:
            info = ENEMY_TYPES[e.type]
            beh = info['behavior']
            e.phase += 0.06
            if e.hit_flash > 0:
                e.hit_flash -= 1

            if beh == 'straight':
                e.y += info['speed']
            elif beh == 'sine':
                e.y += info['speed']
                e.x += math.sin(e.phase) * 0.7
            elif beh == 'zigzag':
                e.y += info['speed']
                e.x += math.sin(e.phase * 1.6) * 1.0
            elif beh == 'dive':
                e.y += info['speed']
                target = p.x + SHIP_W / 2
                cx = e.x + len(info['art'][0]) / 2
                e.x += max(-0.5, min(0.5, (target - cx) * 0.04))
            elif beh == 'boss':
                e.x = self.width / 2 - len(info['art'][0]) / 2 + math.sin(e.phase * 0.4) * (self.width / 5)
                if e.y < 3:
                    e.y += 0.08
                e.attack_timer -= 1
                if e.telegraph > 0:
                    e.telegraph -= 1
                    if e.telegraph == 0:
                        self.boss_attack(e)
                elif e.attack_timer <= 0:
                    e.telegraph = 12
                    e.hit_flash = 12
                    rage = e.health < e.max_health * 0.4
                    e.attack_timer = (28 if rage else 55)

            art_w = len(info['art'][0])
            e.x = max(0, min(self.width - art_w, e.x))

            # disparo de enemigos normales
            if e.type != 'boss':
                if e.shoot_cooldown > 0:
                    e.shoot_cooldown -= 1
                elif info['fire'] > 0 and random.random() < info['fire']:
                    self.enemy_shoot(e)

            if e.y > self.height + 4:
                self.enemies.remove(e)

    def update_powerups(self):
        for pu in self.powerups[:]:
            pu.y += 0.28
            pu.phase += 0.2
            if pu.y >= self.height:
                self.powerups.remove(pu)

    def update_particles(self):
        for pa in self.particles[:]:
            pa.x += pa.vx
            pa.y += pa.vy
            if pa.kind == 'fire':
                pa.vy += 0.02
                pa.vx *= 0.92
            elif pa.kind == 'debris':
                pa.vy += 0.06
            elif pa.kind == 'engine':
                pa.vx *= 0.9
            pa.life -= 1
            if pa.life <= 0:
                self.particles.remove(pa)

    def update_explosions(self):
        for ex in self.explosions[:]:
            ex.frame += 0.35
            if ex.frame >= ex.max_frames:
                self.explosions.remove(ex)

    def update_shockwaves(self):
        for sw in self.shockwaves[:]:
            sw.r += 1.1
            if sw.r >= sw.max_r:
                self.shockwaves.remove(sw)

    def update_popups(self):
        for po in self.popups[:]:
            po.y -= 0.25
            po.life -= 1
            if po.life <= 0:
                self.popups.remove(po)

    # ── colisiones ─────────────────────────────────────────────
    def check_collisions(self):
        p = self.player
        prect = (p.x + 0.5, p.y + 0.5, SHIP_W - 1, SHIP_H - 1)

        # balas jugador vs enemigos
        for b in self.bullets[:]:
            if not b.friendly:
                continue
            for e in self.enemies[:]:
                info = ENEMY_TYPES[e.type]
                art = info['art']
                erect = (e.x, e.y, len(art[0]), len(art))
                if self.collide((b.x, b.y, 1, 1), erect):
                    if b in self.bullets:
                        self.bullets.remove(b)
                    e.health -= b.damage
                    e.hit_flash = max(e.hit_flash, 2)
                    # chispas de impacto
                    for _ in range(3):
                        self.particles.append(Particle(
                            x=b.x, y=b.y, vx=random.uniform(-0.6, 0.6),
                            vy=random.uniform(-0.6, 0.2),
                            life=4, max_life=4, kind='spark', color=C.FIRE_YELLOW))
                    if e.health <= 0:
                        self.kill_enemy(e)
                    break

        # balas enemigas vs jugador
        if p.invincible <= 0:
            for b in self.bullets[:]:
                if b.friendly:
                    continue
                if self.collide((b.x, b.y, 1, 1), prect):
                    self.bullets.remove(b)
                    self.hit_player()
                    break

        # cuerpo enemigo vs jugador
        if p.invincible <= 0:
            for e in self.enemies[:]:
                info = ENEMY_TYPES[e.type]
                art = info['art']
                erect = (e.x, e.y, len(art[0]), len(art))
                if self.collide(prect, erect):
                    if e.type != 'boss':
                        self.kill_enemy(e, by_ram=True)
                    self.hit_player()
                    break

        # powerups
        for pu in self.powerups[:]:
            if self.collide((pu.x, pu.y, 1, 1), prect):
                self.powerups.remove(pu)
                self.apply_powerup(pu.type)

    def kill_enemy(self, e: Enemy, by_ram=False):
        info = ENEMY_TYPES[e.type]
        art = info['art']
        cx = e.x + len(art[0]) / 2
        cy = e.y + len(art) / 2
        if e in self.enemies:
            self.enemies.remove(e)
        boss = e.type == 'boss'
        self.explode(cx, cy, 3 if boss else (2 if e.type == 'tank' else 1), shock=boss or e.type == 'tank')
        if boss:
            self.screen_flash(C.FIRE_WHITE, 2)
            self.boss_active = False
            for _ in range(5):
                self.shockwaves.append(Shockwave(
                    x=cx + random.uniform(-3, 3), y=cy + random.uniform(-2, 2),
                    max_r=random.uniform(8, 16), color=random.choice(
                        [C.FIRE_YELLOW, C.FIRE_ORANGE, C.FIRE_RED])))

        self.combo += 1
        self.combo_timer = 70
        mult = 1 + self.combo * 0.12
        pts = int(info['points'] * mult)
        self.player.score += pts
        self.popup(cx, cy, f"+{pts}", C.COMBO if self.combo > 2 else C.STAR_NEAR)
        if boss:
            self.maybe_spawn_powerup(cx, cy, force=True)
            self.maybe_spawn_powerup(cx + 2, cy, force=True)
        else:
            self.maybe_spawn_powerup(cx, cy)

    def hit_player(self):
        p = self.player
        if p.shield > 0:
            p.shield = 0
            self.explode(p.x + SHIP_W / 2, p.y + 1, 1)
            self.popup(p.x, p.y - 1, "ESCUDO!", C.SHIELD)
            p.invincible = 30
            self.add_shake(2)
            return
        p.lives -= 1
        p.invincible = 110
        p.weapon = max(1, p.weapon - 1)   # pierde nivel de arma
        p.vx = p.vy = 0
        self.explode(p.x + SHIP_W / 2, p.y + 1, 2, shock=True)
        self.screen_flash(C.FIRE_RED, 2)
        self.add_shake(4)
        if p.lives <= 0:
            self.game_over = True

    def apply_powerup(self, ptype):
        p = self.player
        info = POWERUP_TYPES[ptype]
        if ptype == 'power':
            p.weapon = min(5, p.weapon + 1)
        elif ptype == 'shield':
            p.shield = 380
        elif ptype == 'rapid':
            p.rapid_fire = 420
        elif ptype == 'bomb':
            p.bombs = min(5, p.bombs + 1)
        elif ptype == 'life':
            p.lives = min(6, p.lives + 1)
        self.popup(p.x, p.y - 1, info['label'], info['color'])
        for _ in range(16):
            ang = random.uniform(0, math.tau)
            self.particles.append(Particle(
                x=p.x + SHIP_W / 2, y=p.y + 1,
                vx=math.cos(ang) * 1.4, vy=math.sin(ang) * 1.0,
                life=14, max_life=14, kind='spark', color=info['color']))

    def collide(self, r1, r2):
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2

    # ── render ─────────────────────────────────────────────────
    def fire_style(self, ratio):
        """Devuelve (color, glyph) según lo 'caliente' (1=fresco, 0=muerto)."""
        if ratio > 0.78:
            return C.FIRE_WHITE, random.choice(FIRE_CHARS_HOT)
        if ratio > 0.5:
            return C.FIRE_YELLOW, random.choice(FIRE_CHARS_HOT)
        if ratio > 0.3:
            return C.FIRE_ORANGE, random.choice(FIRE_CHARS_MID)
        if ratio > 0.13:
            return C.FIRE_RED, random.choice(FIRE_CHARS_MID)
        return C.SMOKE, random.choice(FIRE_CHARS_COOL)

    def draw(self):
        self.stdscr.erase()
        sx = random.randint(-self.shake_power, self.shake_power) if self.shake_frames > 0 else 0
        sy = (random.randint(-1, 1) if self.shake_power > 1 and self.shake_frames > 0 else 0)

        # flash de pantalla (tinte de fondo)
        if self.flash > 0:
            self.draw_flash()

        self.draw_nebulae(sx, sy)
        self.draw_stars(sx, sy)
        self.draw_shockwaves(sx, sy)
        self.draw_powerups(sx, sy)
        self.draw_bullets(sx, sy)
        self.draw_enemies(sx, sy)
        self.draw_particles(sx, sy)
        self.draw_explosions(sx, sy)
        self.draw_player(sx, sy)
        self.draw_popups(sx, sy)
        self.draw_ui()

        if self.wave_banner > 60 and not self.boss_active:
            pass  # el popup ya lo muestra

        if self.paused:
            self.box("⏸  PAUSA", ["", "P  ·  continuar", "Q  ·  salir", ""])
        if self.game_over:
            self.box("☠  GAME OVER  ☠", [
                "",
                f"Puntuación   {self.player.score:>10,}",
                f"Oleada       {self.wave:>10}",
                "",
                "R  ·  reiniciar      Q  ·  salir",
                "",
            ])
        self.stdscr.refresh()

    def draw_flash(self):
        attr = curses.color_pair(self.flash_color) | curses.A_REVERSE | curses.A_DIM
        step = 1 if self.flash > 1 else 2
        for y in range(0, self.height, step):
            self.addstr(y, 0, ' ' * (self.width - 1), attr)

    def draw_nebulae(self, sx, sy):
        attr = curses.color_pair(C.NEBULA) | curses.A_DIM
        for n in self.nebulae:
            for dx, dy, ch in n.cells:
                x = int(n.x + dx) + sx
                y = int(n.y + dy) + sy
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.addstr(y, x, ch, attr)

    def draw_stars(self, sx, sy):
        for s in self.stars:
            x, y = int(s.x) + sx, int(s.y) + sy
            if 0 <= x < self.width and 0 <= y < self.height:
                attr = curses.A_DIM if s.color == C.STAR_FAR else (
                    curses.A_BOLD if s.color == C.STAR_BLUE else curses.A_NORMAL)
                self.addstr(y, x, s.char, curses.color_pair(s.color) | attr)

    def draw_shockwaves(self, sx, sy):
        for sw in self.shockwaves:
            r = sw.r
            steps = max(8, int(r * 4))
            attr = curses.color_pair(sw.color) | curses.A_BOLD
            for i in range(steps):
                ang = (i / steps) * math.tau
                x = int(sw.x + math.cos(ang) * r) + sx
                y = int(sw.y + math.sin(ang) * r * 0.55) + sy
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.addstr(y, x, '∘' if r < sw.max_r * 0.6 else '·', attr)

    def draw_powerups(self, sx, sy):
        for pu in self.powerups:
            info = POWERUP_TYPES[pu.type]
            x, y = int(pu.x) + sx, int(pu.y) + sy
            blink = math.sin(pu.phase) > -0.3
            attr = curses.color_pair(info['color']) | (curses.A_BOLD if blink else curses.A_DIM)
            if 0 <= x < self.width - 1 and 0 <= y < self.height:
                self.addstr(y, max(0, x - 1), f"({info['symbol']})", attr)

    def draw_bullets(self, sx, sy):
        for b in self.bullets:
            x, y = int(b.x) + sx, int(b.y) + sy
            if 0 <= x < self.width and 0 <= y < self.height:
                self.addstr(y, x, b.glyph, curses.color_pair(b.color) | curses.A_BOLD)

    def draw_enemies(self, sx, sy):
        for e in self.enemies:
            info = ENEMY_TYPES[e.type]
            if e.hit_flash > 0:
                color = C.FIRE_WHITE
            elif e.type == 'boss' and e.telegraph > 0:
                color = C.BOSS_CORE
            else:
                color = info['color']
            attr = curses.color_pair(color) | curses.A_BOLD
            for i, line in enumerate(info['art']):
                x = int(e.x) + sx
                y = int(e.y) + i + sy
                if 0 <= y < self.height:
                    self.addstr(y, max(0, x), line, attr)
            if e.type == 'boss':
                self.draw_boss_bar(e)

    def draw_boss_bar(self, e):
        bw = min(40, self.width - 8)
        filled = int((max(0, e.health) / e.max_health) * bw)
        bar = '█' * filled + '░' * (bw - filled)
        label = "◤ JEFE ◥"
        x = (self.width - bw - 2) // 2
        self.addstr(0, x, label, curses.color_pair(C.BOSS_CORE) | curses.A_BOLD)
        self.addstr(1, x, bar, curses.color_pair(
            C.FIRE_RED if filled < bw * 0.35 else C.BOSS) | curses.A_BOLD)

    def draw_particles(self, sx, sy):
        for pa in self.particles:
            x, y = int(pa.x) + sx, int(pa.y) + sy
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            ratio = pa.life / pa.max_life
            if pa.kind == 'fire':
                color, glyph = self.fire_style(ratio)
            elif pa.kind == 'engine':
                color = C.FIRE_WHITE if ratio > 0.6 else (C.FIRE_YELLOW if ratio > 0.3 else C.FIRE_ORANGE)
                glyph = '▴' if ratio > 0.5 else '·'
            elif pa.kind == 'debris':
                color = pa.color or C.SMOKE
                glyph = pa.glyph or '·'
            else:  # spark
                color = pa.color or C.FIRE_YELLOW
                glyph = pa.glyph or ('✦' if ratio > 0.5 else '·')
            attr = curses.A_BOLD if ratio > 0.4 else curses.A_DIM
            self.addstr(y, x, glyph, curses.color_pair(color) | attr)

    def draw_explosions(self, sx, sy):
        FR = [
            ['▪'],
            [' ▴ ', '◂◆▸', ' ▾ '],
            ['  ◦  ', ' ◢█◣ ', '◀███▶', ' ◥█◤ ', '  ◦  '],
            [' ░ ░ ', '░ ▒ ░', ' ░ ░ '],
            ['  ·  ', ' · · ', '  ·  '],
            ['  ˙  '],
        ]
        for ex in self.explosions:
            idx = min(int(ex.frame), len(FR) - 1)
            frame = FR[idx]
            color = [C.FIRE_WHITE, C.FIRE_YELLOW, C.FIRE_ORANGE, C.FIRE_RED, C.SMOKE, C.SMOKE][idx]
            attr = curses.color_pair(color) | curses.A_BOLD
            for i, line in enumerate(frame):
                x = int(ex.x) - len(line) // 2 + sx
                y = int(ex.y) - len(frame) // 2 + i + sy
                if 0 <= y < self.height:
                    self.addstr(y, max(0, x), line, attr)

    def draw_player(self, sx, sy):
        p = self.player
        # parpadeo de invencibilidad
        if p.invincible > 0 and self.frame % 6 < 3:
            return
        color = C.PLAYER_HOT if (p.rapid_fire > 0 or p.weapon >= 4) else C.PLAYER
        attr = curses.color_pair(color) | curses.A_BOLD
        for i, line in enumerate(SHIP_ART):
            x = int(p.x) + sx
            y = int(p.y) + i + sy
            if 0 <= y < self.height:
                self.addstr(y, max(0, x), line, attr)
        # llama del propulsor
        tf = THRUST_FRAMES[self.frame // 3 % len(THRUST_FRAMES)]
        for i, line in enumerate(tf):
            x = int(p.x) + 1 + sx
            y = int(p.y) + SHIP_H + i + sy
            self.addstr(y, max(0, x), line, curses.color_pair(C.FIRE_ORANGE) | curses.A_BOLD)
        # escudo
        if p.shield > 0:
            ph = self.frame * 0.3
            blink = curses.A_BOLD if math.sin(ph) > 0 else curses.A_DIM
            sattr = curses.color_pair(C.SHIELD) | blink
            ring = ['◜▔▔▔◝', '▏   ▕', '◟▁▁▁◞']
            for i, line in enumerate(ring):
                x = int(p.x) + sx
                y = int(p.y) + i + sy
                if 0 <= y < self.height:
                    self.addstr(y, max(0, x), line, sattr)

    def draw_popups(self, sx, sy):
        for po in self.popups:
            x, y = int(po.x) + sx, int(po.y) + sy
            attr = curses.color_pair(po.color) | (curses.A_BOLD if po.life > 12 else curses.A_DIM)
            if 0 <= y < self.height:
                self.addstr(y, max(0, x), po.text, attr)

    def draw_ui(self):
        p = self.player
        # barra superior
        score = f" SCORE {p.score:,} "
        self.addstr(0, 1, score, curses.color_pair(C.UI) | curses.A_BOLD)
        if self.combo > 1:
            ctext = f" x{self.combo} "
            cattr = curses.color_pair(C.COMBO) | curses.A_BOLD
            self.addstr(0, len(score) + 2, ctext, cattr)
        wave = f" WAVE {self.wave} "
        self.addstr(0, self.width - len(wave) - 1, wave, curses.color_pair(C.UI_ACCENT) | curses.A_BOLD)

        # barra inferior
        y = self.height - 1
        lives = "♥ " * p.lives + "♡ " * max(0, 6 - p.lives)
        self.addstr(y, 1, lives.rstrip(), curses.color_pair(C.ENEMY) | curses.A_BOLD)

        # nivel de arma
        wstr = f"ARMA {'▮' * p.weapon}{'▯' * (5 - p.weapon)}"
        self.addstr(y, len("♥ " * 6) + 3, wstr, curses.color_pair(C.BULLET) | curses.A_BOLD)

        # estado / bombas
        seg = []
        if p.shield > 0:
            seg.append(f"⊛{p.shield // 60 + 1}")
        if p.rapid_fire > 0:
            seg.append(f"↯{p.rapid_fire // 60 + 1}")
        seg.append(f"✺{p.bombs}")
        stat = "  ".join(seg) + " "
        self.addstr(y, self.width - len(stat) - 1, stat, curses.color_pair(C.POWERUP) | curses.A_BOLD)

    def box(self, title, lines):
        w = max(len(title), max((len(l) for l in lines), default=0)) + 6
        h = len(lines) + 4
        x = (self.width - w) // 2
        y = (self.height - h) // 2
        ui = curses.color_pair(C.UI)
        acc = curses.color_pair(C.UI_ACCENT) | curses.A_BOLD
        self.addstr(y, x, "╔" + "═" * (w - 2) + "╗", ui)
        self.addstr(y + 1, x, "║" + title.center(w - 2) + "║", acc)
        self.addstr(y + 2, x, "╠" + "═" * (w - 2) + "╣", ui)
        for i, line in enumerate(lines):
            self.addstr(y + 3 + i, x, "║" + line.center(w - 2) + "║", ui)
        self.addstr(y + h - 1, x, "╚" + "═" * (w - 2) + "╝", ui)

    def addstr(self, y, x, text, attr=0):
        try:
            if 0 <= y < self.height and x < self.width:
                if x < 0:
                    text = text[-x:]
                    x = 0
                maxlen = self.width - x - 1
                if maxlen > 0:
                    self.stdscr.addstr(y, x, text[:maxlen], attr)
        except curses.error:
            pass

    # ── bucle ──────────────────────────────────────────────────
    def run(self):
        if not self.title_screen():
            return
        target = 1 / 60
        while True:
            t0 = time.perf_counter()
            if not self.handle_input():
                break
            self.update()
            self.draw()
            dt = time.perf_counter() - t0
            if dt < target:
                time.sleep(target - dt)

    def title_screen(self):
        title = [
            "█▀▀ █▀█ █▀ █▀▄▀█ █ █▀▀",
            "█▄▄ █▄█ ▄█ █ ▀ █ █ █▄▄",
            "  █▀▄ █▀▀ █▀▀ █▀▀ █▄ █ █▀▄ █▀▀ █▀█",
            "  █▄▀ ██▄ █▀  ██▄ █ ▀█ █▄▀ ██▄ █▀▄",
        ]
        controls = [
            "",
            "─────────── CONTROLES ───────────",
            "  ← → ↑ ↓  /  W A S D   mover (inercia)",
            "  ESPACIO   disparar (mantén pulsado)",
            "  B  bomba      P  pausa      Q  salir",
            "",
            "─────────── POWER-UPS ───────────",
            "  ⊕ arma+   ⊛ escudo   ↯ rápido",
            "  ✺ bomba   ♥ vida",
            "",
            "      ESPACIO para comenzar",
        ]
        while True:
            self.stdscr.erase()
            self.update_background()
            self.draw_nebulae(0, 0)
            self.draw_stars(0, 0)
            ty = max(1, (self.height - len(title) - len(controls)) // 2)
            for i, line in enumerate(title):
                x = (self.width - len(line)) // 2
                col = C.PLAYER if i < 2 else C.UI_ACCENT
                self.addstr(ty + i, x, line, curses.color_pair(col) | curses.A_BOLD)
            for i, line in enumerate(controls):
                x = (self.width - len(line)) // 2
                col = C.UI_ACCENT if line.strip().startswith('─') else C.UI
                self.addstr(ty + len(title) + i, x, line, curses.color_pair(col))
            self.stdscr.refresh()
            try:
                k = self.stdscr.getch()
                if k == ord(' '):
                    return True
                if k in (ord('q'), 27):
                    return False
            except Exception:
                pass
            time.sleep(1 / 30)


def main(stdscr):
    h, w = stdscr.getmaxyx()
    if h < 20 or w < 50:
        stdscr.addstr(0, 0, "Agranda la terminal (min 50x20) y reinicia.")
        stdscr.refresh()
        stdscr.getch()
        return
    Game(stdscr).run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n¡Gracias por jugar COSMIC DEFENDER!  ✦")
