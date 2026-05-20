import pygame
import math
import sys

# --- Konfiguracja Gry ---
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
RENDER_WIDTH, RENDER_HEIGHT = 640, 360
HALF_RENDER_WIDTH = RENDER_WIDTH // 2
HALF_RENDER_HEIGHT = RENDER_HEIGHT // 2
FPS = 60

# Mapa labiryntu (1=Cegły, 2=Zarośnięte cegły, 3=Wyjście)
LEVEL_MAP = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 1],
    [1, 0, 1, 0, 2, 0, 1, 1, 1, 0, 1, 0, 1, 2, 1, 1],
    [1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
    [1, 0, 2, 1, 1, 2, 1, 0, 2, 1, 1, 1, 1, 0, 1, 1],
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 2, 1, 1, 1, 0, 1, 2, 1, 1, 1, 1, 1, 2, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1],
    [1, 0, 1, 0, 1, 1, 1, 0, 2, 0, 1, 1, 0, 2, 0, 1],
    [1, 0, 2, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]

# --- Generatory Tekstur ---
def create_brick_texture(color_bg, color_brick):
    surf = pygame.Surface((64, 64))
    surf.fill(color_bg)
    for y in range(0, 64, 16):
        for x in range(0, 64 + 16, 32):
            offset = 16 if (y // 16) % 2 != 0 else 0
            pygame.draw.rect(surf, color_brick, (x - offset + 2, y + 2, 28, 12))
    return surf


def create_exit_texture():
    surf = pygame.Surface((64, 64))
    surf.fill((20, 20, 50))
    for i in range(5, 32, 5):
        pygame.draw.circle(surf, (50, 255 - i * 5, 100), (32, 32), 32 - i, 2)
    pygame.draw.rect(surf, (0, 255, 0), (0, 0, 64, 64), 4)
    return surf


def create_monster_texture():
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (40, 10, 60), (16, 10, 32, 50))
    pygame.draw.ellipse(surf, (80, 20, 100), (20, 15, 24, 40))
    pygame.draw.circle(surf, (255, 0, 0), (26, 30), 4)
    pygame.draw.circle(surf, (255, 0, 0), (38, 30), 4)
    pygame.draw.circle(surf, (255, 255, 255), (26, 30), 1)
    pygame.draw.circle(surf, (255, 255, 255), (38, 30), 1)
    pygame.draw.polygon(surf, (255, 255, 255), [(26, 45), (38, 45), (32, 50)])
    return surf


class Player:
    def __init__(self):
        self.x, self.y = 1.5, 1.5
        self.dir_x, self.dir_y = 1.0, 0.0
        self.plane_x, self.plane_y = 0.0, 0.66
        self.move_speed = 3.5
        self.mouse_sens = 0.002

        self.is_jumping = False
        self.jump_timer = 0.0
        self.z_offset = 0.0

        self.state = "playing"

    def process_input(self, dt):
        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        speed = self.move_speed * dt * (1.5 if keys[pygame.K_LSHIFT] else 1.0)

        move_x, move_y = 0.0, 0.0
        if keys[pygame.K_w]:
            move_x += self.dir_x * speed
            move_y += self.dir_y * speed
        if keys[pygame.K_s]:
            move_x -= self.dir_x * speed
            move_y -= self.dir_y * speed
        if keys[pygame.K_a]:
            move_x -= self.dir_y * speed
            move_y += self.dir_x * speed
        if keys[pygame.K_d]:
            move_x += self.dir_y * speed
            move_y -= self.dir_x * speed

        # Kolizje (ślizganie się)
        padding = 0.2
        if LEVEL_MAP[int(self.y)][int(self.x + move_x + math.copysign(padding, move_x))] in (0, 3):
            self.x += move_x
        if LEVEL_MAP[int(self.y + move_y + math.copysign(padding, move_y))][int(self.x)] in (0, 3):
            self.y += move_y

        # Sprawdzanie wyjścia
        if LEVEL_MAP[int(self.y)][int(self.x)] == 3:
            self.state = "victory"

        # Skok
        if keys[pygame.K_SPACE] and not self.is_jumping:
            self.is_jumping = True
            self.jump_timer = 0.0

    def process_mouse(self):
        if self.state != "playing":
            return

        mouse_dx, _ = pygame.mouse.get_rel()

        # Myszka w prawo -> obrót w prawo
        rot = mouse_dx * self.mouse_sens

        old_dir_x = self.dir_x
        self.dir_x = self.dir_x * math.cos(rot) - self.dir_y * math.sin(rot)
        self.dir_y = old_dir_x * math.sin(rot) + self.dir_y * math.cos(rot)

        old_plane_x = self.plane_x
        self.plane_x = self.plane_x * math.cos(rot) - self.plane_y * math.sin(rot)
        self.plane_y = old_plane_x * math.sin(rot) + self.plane_y * math.cos(rot)

    def update(self, dt):
        if self.is_jumping:
            self.jump_timer += dt * 5
            self.z_offset = math.sin(self.jump_timer) * 120.0
            if self.jump_timer > math.pi:
                self.is_jumping = False
                self.z_offset = 0.0


class Monster:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 1.2

    def update(self, player, dt):
        if player.state != "playing":
            return

        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        if 0.5 < dist < 7.0:
            move_x = (dx / dist) * self.speed * dt
            move_y = (dy / dist) * self.speed * dt

            padding = 0.3

            if LEVEL_MAP[int(self.y)][int(self.x + move_x + math.copysign(padding, move_x))] in (0, 3):
                self.x += move_x
            if LEVEL_MAP[int(self.y + move_y + math.copysign(padding, move_y))][int(self.x)] in (0, 3):
                self.y += move_y

        if dist <= 0.5:
            player.state = "gameover"


class Raycaster:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cat Maze - Monster Pursuit")

        self.render_surf = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

        self.textures = {
            1: create_brick_texture((50, 50, 50), (120, 80, 80)),
            2: create_brick_texture((30, 60, 30), (80, 100, 60)),
            3: create_exit_texture(),
        }
        self.tex_width = 64
        self.tex_height = 64
        self.monster_tex = create_monster_texture()

        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.title_font = pygame.font.SysFont("Impact", 80)
        self.z_buffer = [0.0] * RENDER_WIDTH

    def draw_3d(self, player, monsters):
        pygame.draw.rect(
            self.render_surf,
            (20, 20, 20),
            (0, 0, RENDER_WIDTH, HALF_RENDER_HEIGHT + player.z_offset),
        )
        pygame.draw.rect(
            self.render_surf,
            (40, 40, 40),
            (0, HALF_RENDER_HEIGHT + player.z_offset, RENDER_WIDTH, RENDER_HEIGHT),
        )

        for x in range(RENDER_WIDTH):
            camera_x = 2 * x / RENDER_WIDTH - 1
            ray_dir_x = player.dir_x + player.plane_x * camera_x
            ray_dir_y = player.dir_y + player.plane_y * camera_x

            map_x, map_y = int(player.x), int(player.y)
            delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else 1e30
            delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else 1e30

            hit, side, wall_type = 0, 0, 1

            if ray_dir_x < 0:
                step_x, side_dist_x = -1, (player.x - map_x) * delta_dist_x
            else:
                step_x, side_dist_x = 1, (map_x + 1.0 - player.x) * delta_dist_x

            if ray_dir_y < 0:
                step_y, side_dist_y = -1, (player.y - map_y) * delta_dist_y
            else:
                step_y, side_dist_y = 1, (map_y + 1.0 - player.y) * delta_dist_y

            while hit == 0:
                if side_dist_x < side_dist_y:
                    side_dist_x += delta_dist_x
                    map_x += step_x
                    side = 0
                else:
                    side_dist_y += delta_dist_y
                    map_y += step_y
                    side = 1

                if LEVEL_MAP[map_y][map_x] > 0:
                    hit = 1
                    wall_type = LEVEL_MAP[map_y][map_x]

            if side == 0:
                perp_wall_dist = (map_x - player.x + (1 - step_x) / 2) / ray_dir_x
                wall_hit_x = player.y + perp_wall_dist * ray_dir_y
            else:
                perp_wall_dist = (map_y - player.y + (1 - step_y) / 2) / ray_dir_y
                wall_hit_x = player.x + perp_wall_dist * ray_dir_x

            wall_hit_x -= math.floor(wall_hit_x)

            tex_x = int(wall_hit_x * self.tex_width)
            if (side == 0 and ray_dir_x > 0) or (side == 1 and ray_dir_y < 0):
                tex_x = self.tex_width - tex_x - 1

            if perp_wall_dist <= 0.01:
                perp_wall_dist = 0.01
            self.z_buffer[x] = perp_wall_dist

            line_height = int(RENDER_HEIGHT / perp_wall_dist)

            texture = self.textures[wall_type]
            sliver = texture.subsurface((tex_x, 0, 1, self.tex_height))

            if line_height > 0:
                scaled_sliver = pygame.transform.scale(sliver, (1, line_height))
                if side == 1:
                    dark = pygame.Surface((1, line_height), pygame.SRCALPHA)
                    dark.fill((0, 0, 0, 80))
                    scaled_sliver.blit(dark, (0, 0))

                draw_start = -line_height // 2 + HALF_RENDER_HEIGHT + player.z_offset
                self.render_surf.blit(scaled_sliver, (x, int(draw_start)))

        sorted_monsters = sorted(
            monsters,
            key=lambda m: (player.x - m.x) ** 2 + (player.y - m.y) ** 2,
            reverse=True,
        )

        for monster in sorted_monsters:
            sprite_dx = monster.x - player.x
            sprite_dy = monster.y - player.y

            inv_det = 1.0 / (player.plane_x * player.dir_y - player.dir_x * player.plane_y)
            transform_x = inv_det * (player.dir_y * sprite_dx - player.dir_x * sprite_dy)
            transform_y = inv_det * (-player.plane_y * sprite_dx + player.plane_x * sprite_dy)

            if transform_y > 0:
                sprite_screen_x = int((RENDER_WIDTH / 2) * (1 + transform_x / transform_y))
                sprite_size = abs(int(RENDER_HEIGHT / transform_y))

                draw_start_y = -sprite_size // 2 + HALF_RENDER_HEIGHT + player.z_offset
                draw_start_x = -sprite_size // 2 + sprite_screen_x

                if 0 < sprite_screen_x < RENDER_WIDTH and transform_y < self.z_buffer[sprite_screen_x]:
                    scaled_monster = pygame.transform.scale(
                        self.monster_tex, (sprite_size, sprite_size)
                    )
                    self.render_surf.blit(scaled_monster, (draw_start_x, int(draw_start_y)))

        scaled_frame = pygame.transform.scale(self.render_surf, (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.screen.blit(scaled_frame, (0, 0))

    def draw_minimap(self, player, monsters):
        map_w, map_h = 200, 200
        map_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
        map_surf.fill((0, 0, 0, 150))

        cell_w, cell_h = map_w / len(LEVEL_MAP[0]), map_h / len(LEVEL_MAP)

        for y, row in enumerate(LEVEL_MAP):
            for x, cell in enumerate(row):
                if cell in (1, 2):
                    pygame.draw.rect(
                        map_surf,
                        (100, 100, 100),
                        (x * cell_w, y * cell_h, cell_w, cell_h),
                    )
                elif cell == 3:
                    pygame.draw.rect(
                        map_surf,
                        (50, 255, 50),
                        (x * cell_w, y * cell_h, cell_w, cell_h),
                    )

        px, py = int(player.x * cell_w), int(player.y * cell_h)
        pygame.draw.circle(map_surf, (0, 255, 0), (px, py), 4)

        for m in monsters:
            mx, my = int(m.x * cell_w), int(m.y * cell_h)
            pygame.draw.circle(map_surf, (255, 0, 0), (mx, my), 4)

        self.screen.blit(map_surf, (WINDOW_WIDTH - map_w - 20, 20))

    def draw_hud(self, elapsed_time):
        time_text = self.font.render(f"Czas: {int(elapsed_time)}s", True, (255, 255, 255))
        self.screen.blit(time_text, (20, 20))

        ctrl_text = self.font.render(
            "WASD: Ruch | Mysz: Kamera | Spacja: Skok | LShift: Sprint",
            True,
            (200, 200, 200),
        )
        self.screen.blit(ctrl_text, (20, WINDOW_HEIGHT - 40))

    def draw_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((100, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        text = self.title_font.render("ZŁAPAŁ CIĘ POTWÓR!", True, (255, 255, 255))
        self.screen.blit(
            text,
            (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT // 2 - 100),
        )

    def draw_victory(self, time):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 100, 0, 150))
        self.screen.blit(overlay, (0, 0))

        text = self.title_font.render("UDAŁO CI SIĘ UCIEC!", True, (255, 255, 255))
        time_txt = self.font.render(f"Twój czas: {int(time)}s", True, (255, 255, 255))
        self.screen.blit(
            text,
            (WINDOW_WIDTH // 2 - text.get_width() // 2, WINDOW_HEIGHT // 2 - 100),
        )
        self.screen.blit(
            time_txt,
            (WINDOW_WIDTH // 2 - time_txt.get_width() // 2, WINDOW_HEIGHT // 2 + 10),
        )

    def draw_button(self, rect, text, is_hover):
        color = (150, 50, 50) if is_hover else (100, 30, 30)
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 3, border_radius=10)

        txt_surf = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(
            txt_surf,
            (
                rect.centerx - txt_surf.get_width() // 2,
                rect.centery - txt_surf.get_height() // 2,
            ),
        )


class Game:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.renderer = Raycaster()
        self.reset()

    def reset(self):
        self.player = Player()
        self.monsters = [Monster(7.5, 3.5), Monster(13.5, 7.5), Monster(5.5, 9.5)]
        self.start_time = pygame.time.get_ticks()

        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def run(self):
        running = True
        btn_rect = pygame.Rect(
            WINDOW_WIDTH // 2 - 100, WINDOW_HEIGHT // 2 + 60, 200, 60
        )

        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.player.state in ["gameover", "victory"]:
                        if btn_rect.collidepoint(event.pos):
                            self.reset()

            if self.player.state == "playing":
                self.player.process_input(dt)
                self.player.process_mouse()
                self.player.update(dt)

                for m in self.monsters:
                    m.update(self.player, dt)

                elapsed_time = (pygame.time.get_ticks() - self.start_time) / 1000.0

            else:
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)

            self.renderer.draw_3d(self.player, self.monsters)
            self.renderer.draw_minimap(self.player, self.monsters)

            if self.player.state == "playing":
                self.renderer.draw_hud(elapsed_time)
            else:
                if self.player.state == "gameover":
                    self.renderer.draw_game_over()
                elif self.player.state == "victory":
                    self.renderer.draw_victory(elapsed_time)

                mouse_pos = pygame.mouse.get_pos()
                is_hover = btn_rect.collidepoint(mouse_pos)
                self.renderer.draw_button(btn_rect, "PLAY AGAIN", is_hover)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
