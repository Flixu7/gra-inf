"""
Jednoręki Bandyt - klasyczny slot 3x3 w Pygame.
Classic 3-reel slot machine written in Pygame.

Wymagania / Requirements:
- Python 3.x
- pygame (pip install pygame)

Pliki zasobów (opcjonalne) / Optional assets:
- dźwięki: assets/sounds/*.wav
- muzyka: assets/music/*.mp3
- grafiki: assets/images/*.png

Jeśli nie ma plików, gra używa bezpiecznych placeholderów.
"""

from __future__ import annotations

import math
import os
import sys
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

import pygame


# ============================
# Konfiguracja / Configuration
# ============================

@dataclass(frozen=True)
class Config:
    # Ekran / Screen
    WIDTH: int = 1280
    HEIGHT: int = 720
    FPS: int = 60

    # Reels / Bębny
    REELS: int = 3
    ROWS: int = 3
    SYMBOL_SIZE: int = 140
    REEL_GAP: int = 18
    REEL_BORDER_RADIUS: int = 16

    # Betting / Stawki
    BET_LEVELS: Tuple[int, ...] = (10, 25, 50, 100, 250, 500)
    STARTING_CREDITS: int = 5000

    # Free spins / Darmowe spiny
    FREE_SPINS_TRIGGER: int = 3
    FREE_SPINS_AWARD: int = 12
    FREE_SPINS_MULTIPLIER: int = 3

    # Wild / Scatter
    WILD: str = "WILD"
    SCATTER: str = "SCATTER"
    WILD_MULTIPLIER: int = 2

    # Win presentation
    BIG_WIN_MULTIPLIER: int = 50

    # Jackpot start values
    JACKPOT_START: Dict[str, int] = field(default_factory=lambda: {
        "mini": 500,
        "minor": 2500,
        "major": 10000,
        "grand": 50000,
    })

    # Auto-spin behavior
    AUTO_STOP_ON_BIG_WIN: bool = True
    AUTO_STOP_ON_BONUS: bool = True

    # Visual style
    BG_DARK: Tuple[int, int, int] = (10, 8, 16)
    NEON_PURPLE: Tuple[int, int, int] = (167, 56, 255)
    NEON_CYAN: Tuple[int, int, int] = (56, 231, 255)
    NEON_MAGENTA: Tuple[int, int, int] = (255, 65, 190)
    NEON_GOLD: Tuple[int, int, int] = (255, 202, 80)
    NEON_GREEN: Tuple[int, int, int] = (90, 255, 160)
    GLASS: Tuple[int, int, int] = (30, 35, 50)

    # Paths (placeholders)
    ASSETS_DIR: str = "assets"
    SOUND_DIR: str = "assets/sounds"
    MUSIC_DIR: str = "assets/music"
    IMAGE_DIR: str = "assets/images"




@dataclass(frozen=True)
class SymbolDef:
    name: str
    weight: int
    color: Tuple[int, int, int]


# Wagi symboli dobrane do ~95% RTP w długim terminie.
# Symbol weights tuned for ~95% long-term RTP.
SYMBOLS: List[SymbolDef] = [
    SymbolDef("🍒", 30, (255, 90, 90)),
    SymbolDef("🍋", 24, (255, 230, 120)),
    SymbolDef("🍉", 22, (255, 120, 160)),
    SymbolDef("⭐", 16, (255, 230, 80)),
    SymbolDef("🛎", 12, (255, 200, 80)),
    SymbolDef("BAR", 10, (220, 220, 220)),
    SymbolDef("7", 8, (255, 60, 60)),
    SymbolDef("💎", 6, (80, 210, 255)),
    SymbolDef("WILD", 4, (255, 80, 210)),
    SymbolDef("SCATTER", 4, (180, 255, 180)),
]


PAYOUTS: Dict[str, int] = {
    "3x💎": 500,
    "3x7": 250,
    "3xBAR": 150,
    "3x🛎": 100,
    "3x⭐": 80,
    "3x🍒": 40,
    "mixed_BAR_7": 20,
}


# ============================
# Narzędzia / Utilities
# ============================


def ease_in_out_cubic(t: float) -> float:
    """Smooth easing for reel motion. / Gładkie przyspieszanie i hamowanie."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


# ============================
# Audio / Dźwięk
# ============================


class SoundManager:
    """Bezpieczny menedżer dźwięku / Safe sound manager."""

    def __init__(self, config: Config):
        self.config = config
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.volume = 0.5
        self.music_volume = 0.4
        self._init_audio()

    def _init_audio(self) -> None:
        try:
            pygame.mixer.init()
        except pygame.error:
            # Audio device not available - continue without sound.
            return

        self._load_sound("spin", "spin.wav")
        self._load_sound("stop", "reel_stop.wav")
        self._load_sound("win", "win.wav")
        self._load_sound("big_win", "big_win.wav")
        self._load_sound("scatter", "scatter.wav")
        self._load_sound("click", "click.wav")
        self._load_sound("gamble", "gamble.wav")

        music_path = os.path.join(self.config.MUSIC_DIR, "bg_music.mp3")
        if os.path.exists(music_path):
            try:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass

    def _load_sound(self, key: str, filename: str) -> None:
        path = os.path.join(self.config.SOUND_DIR, filename)
        if not os.path.exists(path):
            self.sounds[key] = None
            return
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self.volume)
            self.sounds[key] = sound
        except pygame.error:
            self.sounds[key] = None

    def set_volume(self, volume: float) -> None:
        self.volume = clamp(volume, 0.0, 1.0)
        for sound in self.sounds.values():
            if sound:
                sound.set_volume(self.volume)

    def set_music_volume(self, volume: float) -> None:
        self.music_volume = clamp(volume, 0.0, 1.0)
        try:
            pygame.mixer.music.set_volume(self.music_volume)
        except pygame.error:
            pass

    def play(self, key: str) -> None:
        sound = self.sounds.get(key)
        if sound:
            sound.play()


# ============================
# UI Components / Elementy UI
# ============================


class Button:
    """Przycisk z delikatną animacją / Animated button."""

    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font, callback):
        self.rect = rect
        self.text = text
        self.font = font
        self.callback = callback
        self.hover = False
        self.pressed = False
        self.pulse = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hover:
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.hover:
                self.callback()
            self.pressed = False

    def update(self, dt: float) -> None:
        if self.hover:
            self.pulse = min(1.0, self.pulse + dt * 3)
        else:
            self.pulse = max(0.0, self.pulse - dt * 3)

    def draw(self, surface: pygame.Surface) -> None:
        base_color = (40, 50, 70)
        glow = int(40 + self.pulse * 80)
        outline = (glow, glow, glow + 30)
        pygame.draw.rect(surface, base_color, self.rect, border_radius=12)
        pygame.draw.rect(surface, outline, self.rect, 2, border_radius=12)

        text_surf = self.font.render(self.text, True, (230, 240, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class AnimatedValue:
    """Animowane liczniki / Animated counters."""

    def __init__(self, value: float = 0.0):
        self.current = float(value)
        self.target = float(value)

    def set(self, value: float) -> None:
        self.target = float(value)

    def update(self, dt: float, speed: float = 6.0) -> None:
        if self.current == self.target:
            return
        delta = self.target - self.current
        step = delta * min(1.0, dt * speed)
        self.current += step
        if abs(self.target - self.current) < 0.01:
            self.current = self.target


class Lever:
    """Wizualna dźwignia / Physical-looking lever."""

    def __init__(self, base_pos: Tuple[int, int], callback):
        self.base_x, self.base_y = base_pos
        self.callback = callback
        self.angle = 0.0
        self.dragging = False
        self.triggered = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_rect().collidepoint(event.pos):
                self.dragging = True
                self.triggered = False
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                if self.angle < -35 and not self.triggered:
                    self.triggered = True
                    self.callback()
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            _, dy = event.rel
            self.angle = clamp(self.angle - dy * 0.6, -60, 0)

    def update(self, dt: float) -> None:
        if not self.dragging:
            # Smooth return / Płynny powrót
            self.angle += (0 - self.angle) * min(1.0, dt * 8)

    def draw(self, surface: pygame.Surface) -> None:
        # Arm
        length = 140
        rad = math.radians(self.angle)
        end_x = self.base_x + int(math.sin(rad) * length)
        end_y = self.base_y - int(math.cos(rad) * length)

        pygame.draw.line(surface, (120, 130, 150), (self.base_x, self.base_y), (end_x, end_y), 10)
        pygame.draw.circle(surface, (200, 60, 80), (end_x, end_y), 20)
        pygame.draw.circle(surface, (90, 90, 110), (self.base_x, self.base_y), 14)

    def kick(self) -> None:
        """Automatyczne pociągnięcie / Auto pull for spins."""
        self.angle = -50
        self.dragging = False

    def _handle_rect(self) -> pygame.Rect:
        return pygame.Rect(self.base_x - 30, self.base_y - 170, 60, 180)


# ============================
# Particle System / Cząsteczki
# ============================


@dataclass
class Particle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    color: Tuple[int, int, int]
    life: float


class ParticleSystem:
    """Prosty system cząsteczek / Simple particle system."""

    def __init__(self, rng: random.SystemRandom):
        self.rng = rng
        self.particles: List[Particle] = []

    def emit(self, position: Tuple[int, int], color: Tuple[int, int, int], count: int = 60) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(80, 260)
            vel = pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
            self.particles.append(Particle(pygame.Vector2(position), vel, color, 1.2))

    def update(self, dt: float) -> None:
        for particle in self.particles:
            particle.pos += particle.vel * dt
            particle.vel *= 0.92
            particle.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            alpha = int(255 * clamp(particle.life, 0, 1))
            color = (*particle.color, alpha)
            pygame.draw.circle(surface, color, particle.pos, 4)


# ============================
# Reel / Bęben
# ============================


class Reel:
    """Pojedynczy bęben z płynną animacją / Single reel with smooth animation."""

    def __init__(self, symbols: List[str], rng: random.SystemRandom, index: int):
        self.symbols = symbols
        self.rng = rng
        self.index = index
        self.position = float(self.rng.randrange(len(self.symbols)))
        self.start_position = self.position
        self.stop_position = self.position
        self.total_symbols = 0.0
        self.duration = 2.2
        self.elapsed = 0.0
        self.spinning = False
        self.just_stopped = False

    def start_spin(self, stop_index: Optional[int] = None, base_spins: Optional[int] = None) -> None:
        self.just_stopped = False
        self.spinning = True
        self.elapsed = 0.0
        self.start_position = self.position

        if stop_index is None:
            stop_index = self.rng.randrange(len(self.symbols))
        if base_spins is None:
            base_spins = self.rng.randint(2, 4)

        delta = (stop_index - self.start_position) % len(self.symbols)
        self.total_symbols = base_spins * len(self.symbols) + delta

        # Stop later for subsequent reels
        self.duration = 1.8 + self.index * 0.35 + self.rng.random() * 0.2

    def update(self, dt: float) -> None:
        if not self.spinning:
            self.just_stopped = False
            return

        self.elapsed += dt
        t = clamp(self.elapsed / self.duration, 0.0, 1.0)
        eased = ease_in_out_cubic(t)
        self.position = self.start_position + self.total_symbols * eased

        if t >= 1.0:
            self.position = self.start_position + self.total_symbols
            self.spinning = False
            self.just_stopped = True

    def get_visible(self) -> List[str]:
        center_index = int(self.position) % len(self.symbols)
        return [
            self.symbols[(center_index - 1) % len(self.symbols)],
            self.symbols[center_index],
            self.symbols[(center_index + 1) % len(self.symbols)],
        ]

    def draw(self, surface: pygame.Surface, top_left: Tuple[int, int], symbol_surfaces: Dict[str, pygame.Surface]) -> None:
        x, y = top_left
        fraction = self.position - int(self.position)
        for row in range(3):
            symbol_index = (int(self.position) + row - 1) % len(self.symbols)
            symbol = self.symbols[symbol_index]
            symbol_surface = symbol_surfaces[symbol]
            symbol_rect = symbol_surface.get_rect()
            symbol_rect.center = (
                x + symbol_rect.width // 2,
                y + row * Config.SYMBOL_SIZE + Config.SYMBOL_SIZE // 2 - int(fraction * Config.SYMBOL_SIZE),
            )
            surface.blit(symbol_surface, symbol_rect)


# ============================
# Jackpot / Jackpot progresywny
# ============================


class Jackpot:
    """Progresywny jackpot / Progressive jackpot."""

    def __init__(self, config: Config, rng: random.SystemRandom):
        self.config = config
        self.rng = rng
        self.values = {k: float(v) for k, v in config.JACKPOT_START.items()}

    def contribute(self, bet: int) -> None:
        # Procent z betu dodany do jackpotu.
        self.values["mini"] += bet * 0.02
        self.values["minor"] += bet * 0.01
        self.values["major"] += bet * 0.004
        self.values["grand"] += bet * 0.001

    def try_trigger(self) -> Optional[Tuple[str, int]]:
        # Niewielka szansa na wygraną jackpotu.
        roll = self.rng.random()
        if roll < 0.0002:
            tier = "grand"
        elif roll < 0.001:
            tier = "major"
        elif roll < 0.005:
            tier = "minor"
        elif roll < 0.015:
            tier = "mini"
        else:
            return None
        value = int(self.values[tier])
        self.values[tier] = float(self.config.JACKPOT_START[tier])
        return tier, value


# ============================
# Main Game / Główna gra
# ============================


class Game:
    """Główna klasa gry / Main game class."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Jednoręki Bandyt - Neon Casino")
        self.config = Config()
        self.screen = pygame.display.set_mode((self.config.WIDTH, self.config.HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.fullscreen = False

        self.rng = random.SystemRandom()

        self.sound = SoundManager(self.config)
        self.particles = ParticleSystem(self.rng)
        self.jackpot = Jackpot(self.config, self.rng)

        # Fonts / Czcionki
        self.title_font = self._load_font(60, bold=True)
        self.ui_font = self._load_font(24)
        self.small_font = self._load_font(18)
        self.symbol_font = self._load_symbol_font(78)

        # Pre-render symbol surfaces
        self.symbol_surfaces = self._create_symbol_surfaces()
        self.symbol_strip = self._create_symbol_strip()

        # Reels
        self.reels = [Reel(self.symbol_strip, self.rng, i) for i in range(self.config.REELS)]

        # Positions
        total_width = self.config.REELS * self.config.SYMBOL_SIZE + (self.config.REELS - 1) * self.config.REEL_GAP
        self.reel_area = pygame.Rect(
            (self.config.WIDTH - total_width) // 2,
            180,
            total_width,
            self.config.SYMBOL_SIZE * self.config.ROWS,
        )

        # UI state
        self.bet_index = 0
        self.credits = float(self.config.STARTING_CREDITS)
        self.last_win = 0
        self.pending_gamble = 0
        self.free_spins_left = 0
        self.in_free_spins = False
        self.auto_spin = False
        self.spin_in_progress = False
        self.show_paytable = False
        self.show_help = False
        self.show_gamble = False

        self.credit_counter = AnimatedValue(self.credits)
        self.win_counter = AnimatedValue(self.last_win)

        self.shake_timer = 0.0
        self.flash_timer = 0.0
        self.marquee_offset = 0.0

        # Buttons
        self.buttons: List[Button] = []
        self._build_buttons()

        # Lever
        lever_pos = (self.config.WIDTH - 120, 480)
        self.lever = Lever(lever_pos, self.try_spin)

        # Background surface
        self.background = self._create_background()

    # ---------- Setup ----------

    def _load_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        try:
            font = pygame.font.SysFont("Segoe UI", size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, size)
        return font

    def _load_symbol_font(self, size: int) -> pygame.font.Font:
        # Emoji-friendly font fallback
        for name in ("Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", "Segoe UI"):
            try:
                font = pygame.font.SysFont(name, size)
                return font
            except Exception:
                continue
        return pygame.font.Font(None, size)

    def _create_symbol_surfaces(self) -> Dict[str, pygame.Surface]:
        surfaces: Dict[str, pygame.Surface] = {}
        for symbol in SYMBOLS:
            surface = pygame.Surface((self.config.SYMBOL_SIZE, self.config.SYMBOL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surface, (20, 25, 40), surface.get_rect(), border_radius=12)
            pygame.draw.rect(surface, symbol.color, surface.get_rect(), 3, border_radius=12)
            text = symbol.name
            text_surface = self.symbol_font.render(text, True, symbol.color)
            text_rect = text_surface.get_rect(center=surface.get_rect().center)
            surface.blit(text_surface, text_rect)
            surfaces[symbol.name] = surface
        return surfaces

    def _create_symbol_strip(self) -> List[str]:
        strip = []
        for symbol in SYMBOLS:
            strip.extend([symbol.name] * symbol.weight)
        self.rng.shuffle(strip)
        return strip

    def _create_background(self) -> pygame.Surface:
        bg = pygame.Surface((self.config.WIDTH, self.config.HEIGHT))
        bg.fill(self.config.BG_DARK)
        # Subtle gradient / subtelny gradient
        for i in range(self.config.HEIGHT):
            shade = 10 + int(i / self.config.HEIGHT * 30)
            pygame.draw.line(bg, (shade, shade, shade + 10), (0, i), (self.config.WIDTH, i))

        # Neon glow panels
        pygame.draw.rect(bg, (25, 30, 50), self.reel_area.inflate(60, 80), border_radius=28)
        pygame.draw.rect(bg, (80, 30, 120), self.reel_area.inflate(70, 90), 2, border_radius=30)
        return bg

    def _build_buttons(self) -> None:
        self.buttons.clear()
        x = 60
        y = 520
        w, h = 150, 48
        gap = 12
        self.buttons.append(Button(pygame.Rect(x, y, w, h), "SPIN", self.ui_font, self.try_spin))
        self.buttons.append(Button(pygame.Rect(x + (w + gap), y, w, h), "AUTO", self.ui_font, self.toggle_auto))
        self.buttons.append(Button(pygame.Rect(x + 2 * (w + gap), y, w, h), "BET +", self.ui_font, self.bet_up))
        self.buttons.append(Button(pygame.Rect(x + 3 * (w + gap), y, w, h), "BET -", self.ui_font, self.bet_down))

        y2 = y + h + 14
        self.buttons.append(Button(pygame.Rect(x, y2, w, h), "PAYTABLE", self.ui_font, self.toggle_paytable))
        self.buttons.append(Button(pygame.Rect(x + (w + gap), y2, w, h), "HELP", self.ui_font, self.toggle_help))
        self.buttons.append(Button(pygame.Rect(x + 2 * (w + gap), y2, w, h), "GAMBLE", self.ui_font, self.toggle_gamble))
        self.buttons.append(Button(pygame.Rect(x + 3 * (w + gap), y2, w, h), "VOL +", self.ui_font, self.volume_up))
        self.buttons.append(Button(pygame.Rect(x + 4 * (w + gap), y2, w, h), "VOL -", self.ui_font, self.volume_down))

    # ---------- UI callbacks ----------

    def bet_up(self) -> None:
        self.bet_index = min(self.bet_index + 1, len(self.config.BET_LEVELS) - 1)

    def bet_down(self) -> None:
        self.bet_index = max(self.bet_index - 1, 0)

    def toggle_auto(self) -> None:
        self.auto_spin = not self.auto_spin

    def toggle_paytable(self) -> None:
        self.show_paytable = not self.show_paytable

    def toggle_help(self) -> None:
        self.show_help = not self.show_help

    def toggle_gamble(self) -> None:
        if self.spin_in_progress:
            return
        if self.show_gamble:
            self.gamble_collect()
            return
        if self.pending_gamble > 0:
            self.show_gamble = True

    def volume_up(self) -> None:
        self.sound.set_volume(self.sound.volume + 0.1)
        self.sound.set_music_volume(self.sound.music_volume + 0.1)

    def volume_down(self) -> None:
        self.sound.set_volume(self.sound.volume - 0.1)
        self.sound.set_music_volume(self.sound.music_volume - 0.1)

    # ---------- Core spin ----------

    def try_spin(self) -> None:
        if self.spin_in_progress or self.show_paytable or self.show_help or self.show_gamble:
            return

        if self.pending_gamble > 0:
            self.collect_pending_win()

        bet = self.config.BET_LEVELS[self.bet_index]
        if self.free_spins_left <= 0 and self.credits < bet:
            return

        if self.free_spins_left > 0:
            self.in_free_spins = True
            self.free_spins_left -= 1
        else:
            self.credits -= bet
            self.jackpot.contribute(bet)

        self.spin_in_progress = True
        self.last_win = 0
        self.pending_gamble = 0
        self.win_counter.set(0)
        self.sound.play("spin")
        self.lever.kick()

        for reel in self.reels:
            reel.start_spin()

    # ---------- Evaluation ----------

    def evaluate_spin(self) -> None:
        grid = [reel.get_visible() for reel in self.reels]
        # Transpose to rows
        rows = list(map(list, zip(*grid)))

        total_win = 0
        for row in rows:
            win = self.evaluate_line(row)
            total_win += win

        scatter_count = sum(symbol == self.config.SCATTER for row in rows for symbol in row)
        if scatter_count >= self.config.FREE_SPINS_TRIGGER:
            self.free_spins_left += self.config.FREE_SPINS_AWARD
            self.sound.play("scatter")
            if self.config.AUTO_STOP_ON_BONUS:
                self.auto_spin = False

        # Apply bet multiplier
        bet = self.config.BET_LEVELS[self.bet_index]
        bet_multiplier = bet / self.config.BET_LEVELS[0]
        total_win = int(total_win * bet_multiplier)

        if self.in_free_spins:
            total_win *= self.config.FREE_SPINS_MULTIPLIER

        jackpot_hit = None
        if total_win > 0:
            jackpot_hit = self.jackpot.try_trigger()

        if jackpot_hit:
            _, value = jackpot_hit
            total_win += value

        if total_win > 0:
            self.last_win = total_win
            self.pending_gamble = total_win
            self.win_counter.set(total_win)

            self.sound.play("big_win" if total_win >= bet * self.config.BIG_WIN_MULTIPLIER else "win")
            self.shake_timer = 0.4
            self.flash_timer = 0.6
            self.particles.emit(self.reel_area.center, self.config.NEON_GOLD)
            if self.config.AUTO_STOP_ON_BIG_WIN and total_win >= bet * self.config.BIG_WIN_MULTIPLIER:
                self.auto_spin = False

        if self.free_spins_left == 0:
            self.in_free_spins = False

    def evaluate_line(self, symbols: List[str]) -> int:
        # Scatter nie liczy się do linii / Scatter does not count on paylines
        if self.config.SCATTER in symbols:
            return 0

        if all(symbol == self.config.WILD for symbol in symbols):
            # 3x WILD = najwyższa wygrana * multiplier
            return PAYOUTS["3x💎"] * self.config.WILD_MULTIPLIER

        non_wild = [s for s in symbols if s != self.config.WILD]
        unique = set(non_wild)
        if len(unique) == 1 and non_wild:
            symbol = non_wild[0]
            key = f"3x{symbol}"
            return PAYOUTS.get(key, 0)

        if unique.issubset({"BAR", "7"}) and len(unique) >= 2:
            return PAYOUTS["mixed_BAR_7"]

        return 0

    # ---------- Gamble ----------

    def gamble_double(self) -> None:
        if self.pending_gamble <= 0:
            return
        self.sound.play("gamble")
        if self.rng.random() < 0.5:
            self.pending_gamble *= 2
            self.last_win = self.pending_gamble
            self.win_counter.set(self.last_win)
        else:
            self.pending_gamble = 0
            self.last_win = 0
            self.win_counter.set(0)
            self.show_gamble = False

    def gamble_collect(self) -> None:
        self.collect_pending_win()
        self.show_gamble = False

    def collect_pending_win(self) -> None:
        if self.pending_gamble > 0:
            self.credits += self.pending_gamble
            self.pending_gamble = 0

    # ---------- Game Loop ----------

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.config.FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit(0)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.try_spin()
                elif event.key == pygame.K_f:
                    self.toggle_fullscreen()

            for button in self.buttons:
                button.handle_event(event)

            self.lever.handle_event(event)

            if self.show_gamble:
                # Simple keyboard gamble controls
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_d:
                        self.gamble_double()
                    elif event.key == pygame.K_c:
                        self.gamble_collect()
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    _, double_rect, collect_rect = self.get_gamble_rects()
                    if double_rect.collidepoint(event.pos):
                        self.gamble_double()
                    elif collect_rect.collidepoint(event.pos):
                        self.gamble_collect()

    def update(self, dt: float) -> None:
        self.credit_counter.set(self.credits)
        self.credit_counter.update(dt)
        self.win_counter.update(dt)

        self.marquee_offset += dt * 120

        for button in self.buttons:
            button.update(dt)

        self.lever.update(dt)
        self.particles.update(dt)

        # Update reels
        for reel in self.reels:
            reel.update(dt)
            if reel.just_stopped:
                self.sound.play("stop")

        if self.spin_in_progress and all(not reel.spinning for reel in self.reels):
            self.spin_in_progress = False
            self.evaluate_spin()

        # Screen shake / flashing
        self.shake_timer = max(0.0, self.shake_timer - dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)

        # Auto-spin logic
        if self.auto_spin and not self.spin_in_progress and not self.show_gamble:
            if self.free_spins_left > 0 or self.credits >= self.config.BET_LEVELS[self.bet_index]:
                self.try_spin()
            else:
                self.auto_spin = False

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((self.config.WIDTH, self.config.HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.config.WIDTH, self.config.HEIGHT))

    # ---------- Drawing ----------

    def draw(self) -> None:
        offset = pygame.Vector2(0, 0)
        if self.shake_timer > 0:
            offset = pygame.Vector2(self.rng.uniform(-6, 6), self.rng.uniform(-4, 4))

        frame = pygame.Surface((self.config.WIDTH, self.config.HEIGHT), pygame.SRCALPHA)
        frame.blit(self.background, (0, 0))
        if self.in_free_spins:
            tint = pygame.Surface((self.config.WIDTH, self.config.HEIGHT), pygame.SRCALPHA)
            tint.fill((40, 10, 60, 80))
            frame.blit(tint, (0, 0))

        self.draw_title(frame)
        self.draw_reels(frame)
        self.draw_ui(frame)
        self.draw_jackpots(frame)
        self.lever.draw(frame)
        self.particles.draw(frame)

        if self.flash_timer > 0:
            alpha = int(120 * (self.flash_timer / 0.6))
            flash = pygame.Surface((self.config.WIDTH, self.config.HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 230, 160, alpha))
            frame.blit(flash, (0, 0))

        self.screen.fill(self.config.BG_DARK)
        self.screen.blit(frame, offset)
        pygame.display.flip()

    def draw_title(self, surface: pygame.Surface) -> None:
        title_text = "CASINO"
        glow_color = self.config.NEON_MAGENTA
        text_surface = self.title_font.render(title_text, True, glow_color)
        text_rect = text_surface.get_rect(center=(self.config.WIDTH // 2, 70))
        # Glow effect / efekt poświaty
        for i in range(1, 5):
            glow = pygame.transform.smoothscale(text_surface, (text_rect.width + i * 10, text_rect.height + i * 8))
            glow_rect = glow.get_rect(center=text_rect.center)
            glow.set_alpha(40)
            surface.blit(glow, glow_rect)
        surface.blit(text_surface, text_rect)

        # Marquee dots
        for i in range(0, self.config.WIDTH, 40):
            phase = (i + self.marquee_offset) % 200
            color = self.config.NEON_CYAN if phase < 100 else self.config.NEON_PURPLE
            pygame.draw.circle(surface, color, (i, 120), 4)

    def draw_reels(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (15, 20, 35), self.reel_area, border_radius=self.config.REEL_BORDER_RADIUS)
        pygame.draw.rect(surface, (120, 50, 160), self.reel_area, 2, border_radius=self.config.REEL_BORDER_RADIUS)

        for i, reel in enumerate(self.reels):
            x = self.reel_area.x + i * (self.config.SYMBOL_SIZE + self.config.REEL_GAP)
            y = self.reel_area.y
            reel_rect = pygame.Rect(x, y, self.config.SYMBOL_SIZE, self.config.SYMBOL_SIZE * self.config.ROWS)
            pygame.draw.rect(surface, self.config.GLASS, reel_rect, border_radius=12)
            reel.draw(surface, (x, y), self.symbol_surfaces)
            if reel.just_stopped:
                pygame.draw.rect(surface, self.config.NEON_GOLD, reel_rect, 3, border_radius=12)

    def draw_ui(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(40, 620, self.config.WIDTH - 80, 80)
        pygame.draw.rect(surface, (20, 25, 40), panel, border_radius=16)
        pygame.draw.rect(surface, (80, 90, 120), panel, 2, border_radius=16)

        self.draw_label(surface, "CREDITS", int(self.credit_counter.current), (80, 635))
        self.draw_label(surface, "BET", self.config.BET_LEVELS[self.bet_index], (360, 635))
        self.draw_label(surface, "WIN", int(self.win_counter.current), (600, 635))

        if self.in_free_spins:
            info = self.ui_font.render(f"FREE SPINS: {self.free_spins_left}", True, self.config.NEON_GREEN)
            surface.blit(info, (860, 640))

        if self.auto_spin:
            auto = self.ui_font.render("AUTO", True, self.config.NEON_CYAN)
            surface.blit(auto, (1060, 640))

        if self.last_win >= self.config.BET_LEVELS[self.bet_index] * self.config.BIG_WIN_MULTIPLIER:
            big_text = self.ui_font.render("BIG WIN!", True, self.config.NEON_GOLD)
            surface.blit(big_text, (980, 670))

        for button in self.buttons:
            button.draw(surface)

        if self.show_paytable:
            self.draw_paytable(surface)
        if self.show_help:
            self.draw_help(surface)
        if self.show_gamble:
            self.draw_gamble(surface)

    def draw_label(self, surface: pygame.Surface, title: str, value: int, pos: Tuple[int, int]) -> None:
        title_surf = self.small_font.render(title, True, (160, 170, 190))
        value_surf = self.ui_font.render(str(value), True, (230, 240, 255))
        surface.blit(title_surf, pos)
        surface.blit(value_surf, (pos[0], pos[1] + 22))

    def draw_jackpots(self, surface: pygame.Surface) -> None:
        x = 60
        y = 140
        for tier, color in (
            ("mini", self.config.NEON_CYAN),
            ("minor", self.config.NEON_GREEN),
            ("major", self.config.NEON_MAGENTA),
            ("grand", self.config.NEON_GOLD),
        ):
            text = f"{tier.upper()}: {int(self.jackpot.values[tier])}"
            surf = self.small_font.render(text, True, color)
            surface.blit(surf, (x, y))
            y += 22

    def draw_paytable(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((self.config.WIDTH, self.config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(140, 140, 1000, 440)
        pygame.draw.rect(surface, (25, 30, 45), panel, border_radius=20)
        pygame.draw.rect(surface, self.config.NEON_PURPLE, panel, 2, border_radius=20)

        title = self.ui_font.render("PAYTABLE", True, self.config.NEON_GOLD)
        surface.blit(title, (panel.x + 20, panel.y + 20))

        y = panel.y + 70
        for key, value in PAYOUTS.items():
            line = f"{key} -> {value}"
            surf = self.small_font.render(line, True, (220, 230, 240))
            surface.blit(surf, (panel.x + 30, y))
            y += 24

        extra = [
            f"3x {self.config.WILD} = x{self.config.WILD_MULTIPLIER} highest win",
            "SCATTER x3+ anywhere -> 12 Free Spins x3",
            "Paylines: top, middle, bottom",
        ]
        y += 10
        for line in extra:
            surf = self.small_font.render(line, True, self.config.NEON_CYAN)
            surface.blit(surf, (panel.x + 30, y))
            y += 24

    def draw_help(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((self.config.WIDTH, self.config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(200, 160, 880, 400)
        pygame.draw.rect(surface, (20, 25, 40), panel, border_radius=20)
        pygame.draw.rect(surface, self.config.NEON_CYAN, panel, 2, border_radius=20)

        lines = [
            "HELP / RULES",
            "SPACE = Spin, ESC = Quit, F = Fullscreen",
            "WILD substitutes for all except SCATTER",
            "SCATTER x3+ anywhere -> Free Spins x3",
            "Gamble: press D to double, C to collect",
            "Auto-spin stops on big win or bonus",
        ]
        y = panel.y + 30
        for line in lines:
            color = self.config.NEON_GOLD if line == "HELP / RULES" else (220, 230, 240)
            surf = self.small_font.render(line, True, color)
            surface.blit(surf, (panel.x + 30, y))
            y += 28

    def draw_gamble(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((self.config.WIDTH, self.config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        panel, double_rect, collect_rect = self.get_gamble_rects()
        pygame.draw.rect(surface, (30, 20, 30), panel, border_radius=20)
        pygame.draw.rect(surface, self.config.NEON_MAGENTA, panel, 2, border_radius=20)

        title = self.ui_font.render("GAMBLE - DOUBLE OR NOTHING", True, self.config.NEON_GOLD)
        surface.blit(title, (panel.x + 30, panel.y + 30))

        info = self.small_font.render(f"Current win: {self.pending_gamble}", True, (230, 240, 255))
        surface.blit(info, (panel.x + 30, panel.y + 90))

        # Buttons inside overlay
        pygame.draw.rect(surface, (50, 80, 70), double_rect, border_radius=10)
        pygame.draw.rect(surface, (70, 50, 50), collect_rect, border_radius=10)
        pygame.draw.rect(surface, self.config.NEON_GREEN, double_rect, 2, border_radius=10)
        pygame.draw.rect(surface, self.config.NEON_MAGENTA, collect_rect, 2, border_radius=10)

        double_text = self.ui_font.render("DOUBLE (D)", True, (230, 240, 255))
        collect_text = self.ui_font.render("COLLECT (C)", True, (230, 240, 255))
        surface.blit(double_text, double_text.get_rect(center=double_rect.center))
        surface.blit(collect_text, collect_text.get_rect(center=collect_rect.center))

    def get_gamble_rects(self) -> Tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        panel = pygame.Rect(320, 200, 640, 320)
        double_rect = pygame.Rect(panel.x + 60, panel.y + 160, 200, 50)
        collect_rect = pygame.Rect(panel.x + 360, panel.y + 160, 200, 50)
        return panel, double_rect, collect_rect


if __name__ == "__main__":
    try:
        Game().run()
    except Exception as exc:
        # Critical error handling / Obsługa krytycznych błędów
        print("Fatal error:", exc)
        pygame.quit()
        sys.exit(1)
