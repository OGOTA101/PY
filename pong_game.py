import pygame
import sys
import random
import numpy as np
import traceback

# ---------- CONSTANTS ----------
# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PADDLE_BASE_COLOR = WHITE
CENTER_ZONE_COLOR = (255, 0, 0)      # 中央ゾーン：赤
EDGE_ZONE_COLOR = (0, 0, 255)          # 両端：青
EFFECT_COLOR_WALL = (255, 255, 255)    # 壁衝突：白
EFFECT_COLOR_CENTER = (255, 0, 0)      # 中央衝突：赤

CENTER_THRESHOLD = 5    # ±5ピクセルを中央とする
ACCEL_FACTOR = 1.5      # 加速倍率

BASE_BALL_SPEED_X = 4
BASE_BALL_SPEED_Y = 4

# Paddle sizes
PADDLE_WIDTH_H = 10
PADDLE_HEIGHT_H = 100
PADDLE_WIDTH_V = 100
PADDLE_HEIGHT_V = 15

BALL_SIZE = 15

CPU_SPEED_LEVEL = {1: 3, 2: 5, 3: 7}

WIN_SCORE = 5

# ---------- EFFECTS ----------
effects = []

def add_effect(pos, accelerated=False, color=CENTER_ZONE_COLOR):
    """指定位置に衝突エフェクトを追加（新たなエフェクト追加時は既存エフェクトをクリアして１つだけ表示）"""
    global effects
    effects.clear()  # 既存のエフェクトをクリア
    effect = {
        "pos": pos,
        "radius": 5,
        "max_radius": 20 if not accelerated else 40,
        "growth": 2 if not accelerated else 4,
        "alpha": 255,
        "color": color
    }
    effects.append(effect)

def update_and_draw_effects(surface):
    global effects
    for effect in effects[:]:
        effect_surf = pygame.Surface((effect["max_radius"]*2, effect["max_radius"]*2), pygame.SRCALPHA)
        current_color = effect["color"] + (effect["alpha"],)
        pygame.draw.circle(effect_surf, current_color, (effect["max_radius"], effect["max_radius"]), int(effect["radius"]))
        pos = (int(effect["pos"][0] - effect["max_radius"]), int(effect["pos"][1] - effect["max_radius"]))
        surface.blit(effect_surf, pos)
        effect["radius"] += effect["growth"]
        effect["alpha"] = max(effect["alpha"] - 15, 0)
        if effect["alpha"] <= 0 or effect["radius"] >= effect["max_radius"]:
            effects.remove(effect)

# ---------- SOUND GENERATION ----------
def generate_beep(frequency=600, duration=0.15, volume=0.5, sample_rate=44100):
    """ビープ音を生成して pygame.mixer.Sound を返す"""
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    waveform = volume * np.sin(2 * np.pi * frequency * t)
    waveform_integers = np.int16(waveform * 32767)
    stereo_waveform = np.column_stack((waveform_integers, waveform_integers))
    sound = pygame.sndarray.make_sound(stereo_waveform)
    return sound

# ---------- PADDLE DRAWING FUNCTIONS ----------
def draw_vertical_paddle(rect, surface):
    """縦のパドルを描画（上端・下端：青、中央帯：赤、それ以外：白）"""
    blue_edge = 5
    red_band = 10
    # 上端青
    pygame.draw.rect(surface, EDGE_ZONE_COLOR, (rect.x, rect.y, rect.width, blue_edge))
    # 下端青
    pygame.draw.rect(surface, EDGE_ZONE_COLOR, (rect.x, rect.bottom - blue_edge, rect.width, blue_edge))
    # 中央赤帯
    red_y = rect.y + (rect.height - red_band) // 2
    pygame.draw.rect(surface, CENTER_ZONE_COLOR, (rect.x, red_y, rect.width, red_band))
    # 残りを白で塗る
    pygame.draw.rect(surface, PADDLE_BASE_COLOR, (rect.x, rect.y + blue_edge, rect.width, red_y - (rect.y + blue_edge)))
    pygame.draw.rect(surface, PADDLE_BASE_COLOR, (rect.x, red_y + red_band, rect.width, rect.bottom - red_y - red_band - blue_edge))

def draw_horizontal_paddle(rect, surface):
    """横のパドルを描画（左端・右端：青、中央帯：赤、それ以外：白）"""
    blue_edge = 5
    red_band = 10
    # 左端青
    pygame.draw.rect(surface, EDGE_ZONE_COLOR, (rect.x, rect.y, blue_edge, rect.height))
    # 右端青
    pygame.draw.rect(surface, EDGE_ZONE_COLOR, (rect.right - blue_edge, rect.y, blue_edge, rect.height))
    # 中央赤帯
    red_x = rect.x + (rect.width - red_band) // 2
    pygame.draw.rect(surface, CENTER_ZONE_COLOR, (red_x, rect.y, red_band, rect.height))
    # 残りを白で塗る
    pygame.draw.rect(surface, PADDLE_BASE_COLOR, (rect.x + blue_edge, rect.y, red_x - (rect.x + blue_edge), rect.height))
    pygame.draw.rect(surface, PADDLE_BASE_COLOR, (red_x + red_band, rect.y, rect.right - (red_x + red_band) - blue_edge, rect.height))

# ---------- MAIN MENU ----------
def main_menu(screen):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 36)
    mode = None
    cpu_level = None
    while mode is None:
        screen.fill(BLACK)
        title = font.render("PONG GAME - MODE SELECTION", True, WHITE)
        option1 = font.render("1: PLAYER VS PLAYER (HORIZONTAL)", True, WHITE)
        option2 = font.render("2: CPU VS PLAYER (VERTICAL)", True, WHITE)
        quit_text = font.render("Q: QUIT", True, WHITE)
        screen.blit(title, (screen.get_width()//2 - title.get_width()//2, 100))
        screen.blit(option1, (screen.get_width()//2 - option1.get_width()//2, 200))
        screen.blit(option2, (screen.get_width()//2 - option2.get_width()//2, 250))
        screen.blit(quit_text, (screen.get_width()//2 - quit_text.get_width()//2, 300))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    mode = "PVP"
                elif event.key == pygame.K_2:
                    mode = "CPU"
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
        clock.tick(30)
    
    # CPUモードの場合、難易度選択メニューで戻る機能を追加
    if mode == "CPU":
        selecting = True
        while selecting:
            screen.fill(BLACK)
            title = font.render("SELECT CPU DIFFICULTY", True, WHITE)
            level1 = font.render("1: EASY", True, WHITE)
            level2 = font.render("2: MEDIUM", True, WHITE)
            level3 = font.render("3: HARD", True, WHITE)
            back_text = font.render("B: BACK", True, WHITE)
            screen.blit(title, (screen.get_width()//2 - title.get_width()//2, 100))
            screen.blit(level1, (screen.get_width()//2 - level1.get_width()//2, 200))
            screen.blit(level2, (screen.get_width()//2 - level2.get_width()//2, 250))
            screen.blit(level3, (screen.get_width()//2 - level3.get_width()//2, 300))
            screen.blit(back_text, (screen.get_width()//2 - back_text.get_width()//2, 350))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        cpu_level = 1
                        selecting = False
                    elif event.key == pygame.K_2:
                        cpu_level = 2
                        selecting = False
                    elif event.key == pygame.K_3:
                        cpu_level = 3
                        selecting = False
                    elif event.key == pygame.K_b:
                        # 戻る場合はモード選択に戻る
                        mode = None
                        selecting = False
            clock.tick(30)
        if mode is None:
            return main_menu(screen)
    return mode, cpu_level

# ---------- GAME LOOP ----------
def game_loop(screen, mode, cpu_level):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 30)

    # サウンド生成
    START_SOUND = generate_beep(frequency=800, duration=0.3, volume=0.5)
    GAME_OVER_SOUND = generate_beep(frequency=300, duration=0.3, volume=0.5)
    GAME_CLEAR_SOUND = generate_beep(frequency=1200, duration=0.3, volume=0.5)
    NORMAL_SOUND = generate_beep(frequency=600, duration=0.15, volume=0.5)
    ACCELERATED_SOUND = generate_beep(frequency=1000, duration=0.15, volume=0.5)

    # モードに応じた画面サイズ設定
    if mode == "PVP":
        w, h = 800, 600
    else:
        w, h = 600, 800
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("PONG GAME")
    
    # スコア初期化（相手のミスで得点）
    if mode == "PVP":
        score_left = 0
        score_right = 0
    else:
        score_player = 0
        score_cpu = 0

    # パドルとボールの初期化
    if mode == "PVP":
        left_paddle = pygame.Rect(50, h // 2 - PADDLE_HEIGHT_H // 2, PADDLE_WIDTH_H, PADDLE_HEIGHT_H)
        right_paddle = pygame.Rect(w - 50 - PADDLE_WIDTH_H, h // 2 - PADDLE_HEIGHT_H // 2, PADDLE_WIDTH_H, PADDLE_HEIGHT_H)
    else:
        player_paddle = pygame.Rect(w // 2 - PADDLE_WIDTH_V // 2, h - 40, PADDLE_WIDTH_V, PADDLE_HEIGHT_V)
        cpu_paddle = pygame.Rect(w // 2 - PADDLE_WIDTH_V // 2, 40, PADDLE_WIDTH_V, PADDLE_HEIGHT_V)

    ball = pygame.Rect(w // 2 - BALL_SIZE // 2, h // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)
    ball_dx = BASE_BALL_SPEED_X * random.choice([-1, 1])
    ball_dy = BASE_BALL_SPEED_Y * random.choice([-1, 1])
    
    global effects
    effects.clear()

    START_SOUND.play()
    last_paddle_hit = None

    session_running = True
    game_over = False
    winner = None

    while session_running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

        keys = pygame.key.get_pressed()

        # 勝利判定
        if mode == "PVP":
            if score_left >= WIN_SCORE or score_right >= WIN_SCORE:
                game_over = True
                winner = "LEFT PLAYER" if score_left >= WIN_SCORE else "RIGHT PLAYER"
        else:
            if score_player >= WIN_SCORE or score_cpu >= WIN_SCORE:
                game_over = True
                winner = "PLAYER" if score_player >= WIN_SCORE else "CPU"

        if not game_over:
            # パドル操作
            if mode == "PVP":
                if keys[pygame.K_w] and left_paddle.top > 0:
                    left_paddle.y -= 6
                if keys[pygame.K_s] and left_paddle.bottom < h:
                    left_paddle.y += 6
                if keys[pygame.K_UP] and right_paddle.top > 0:
                    right_paddle.y -= 6
                if keys[pygame.K_DOWN] and right_paddle.bottom < h:
                    right_paddle.y += 6
            else:
                if (keys[pygame.K_LEFT] or keys[pygame.K_a]) and player_paddle.left > 0:
                    player_paddle.x -= 6
                if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) and player_paddle.right < w:
                    player_paddle.x += 6
                cpu_speed = CPU_SPEED_LEVEL.get(cpu_level, 3)
                if cpu_paddle.centerx < ball.centerx and cpu_paddle.right < w:
                    cpu_paddle.x += cpu_speed
                elif cpu_paddle.centerx > ball.centerx and cpu_paddle.left > 0:
                    cpu_paddle.x -= cpu_speed

            ball.x += int(ball_dx)
            ball.y += int(ball_dy)

            # 壁との衝突（バウンド処理）
            if mode == "PVP":
                if ball.top <= 0 or ball.bottom >= h:
                    ball_dy *= -1
                    effect_pos = (ball.centerx, 0 if ball.top <= 0 else h)
                    add_effect(effect_pos, accelerated=False, color=EFFECT_COLOR_WALL)
                    NORMAL_SOUND.play()
                # PVPでは左右から出たら得点
                if ball.left <= 0:
                    score_right += 1  # 左側がミス → 右に得点
                    ball.center = (w//2, h//2)
                    ball_dx = BASE_BALL_SPEED_X * random.choice([-1, 1])
                    ball_dy = BASE_BALL_SPEED_Y * random.choice([-1, 1])
                    last_paddle_hit = None
                elif ball.right >= w:
                    score_left += 1  # 右側がミス → 左に得点
                    ball.center = (w//2, h//2)
                    ball_dx = BASE_BALL_SPEED_X * random.choice([-1, 1])
                    ball_dy = BASE_BALL_SPEED_Y * random.choice([-1, 1])
                    last_paddle_hit = None
            else:
                # CPUモード：左右壁でバウンド
                if ball.left <= 0 or ball.right >= w:
                    ball_dx *= -1
                    effect_pos = (0 if ball.left <= 0 else w, ball.centery)
                    add_effect(effect_pos, accelerated=False, color=EFFECT_COLOR_WALL)
                    NORMAL_SOUND.play()
                # CPUモード：上下から出たら得点（自分のミスなら相手に得点）
                if ball.top <= 0:
                    score_player += 1  # CPUがミス → プレイヤー得点
                    ball.center = (w//2, h//2)
                    ball_dx = BASE_BALL_SPEED_X * random.choice([-1, 1])
                    ball_dy = BASE_BALL_SPEED_Y * random.choice([-1, 1])
                    last_paddle_hit = None
                elif ball.bottom >= h:
                    score_cpu += 1  # プレイヤーがミス → CPU得点
                    ball.center = (w//2, h//2)
                    ball_dx = BASE_BALL_SPEED_X * random.choice([-1, 1])
                    ball_dy = BASE_BALL_SPEED_Y * random.choice([-1, 1])
                    last_paddle_hit = None

            # パドルとの衝突処理
            if mode == "PVP":
                # 左側パドル
                if ball.colliderect(left_paddle) and ball_dx < 0:
                    paddle_center = left_paddle.centery
                    ball_center = ball.centery
                    if abs(paddle_center - ball_center) <= CENTER_THRESHOLD and last_paddle_hit != "left":
                        ball_dx = -abs(ball_dx) * ACCEL_FACTOR
                        ball_dy = (ball_dy/abs(ball_dy) if ball_dy != 0 else 1) * abs(ball_dy) * ACCEL_FACTOR
                        last_paddle_hit = "left"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EFFECT_COLOR_CENTER)
                        ACCELERATED_SOUND.play()
                    elif ((ball_center - left_paddle.top) <= CENTER_THRESHOLD or (left_paddle.bottom - ball_center) <= CENTER_THRESHOLD) and last_paddle_hit != "left_edge":
                        ball_dx = -abs(ball_dx) * ACCEL_FACTOR
                        last_paddle_hit = "left_edge"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EDGE_ZONE_COLOR)
                        ACCELERATED_SOUND.play()
                    else:
                        ball_dx = -abs(ball_dx)
                        last_paddle_hit = "left"
                        add_effect((ball.centerx, ball.centery), accelerated=False, color=WHITE)
                        NORMAL_SOUND.play()
                # 右側パドル
                if ball.colliderect(right_paddle) and ball_dx > 0:
                    paddle_center = right_paddle.centery
                    ball_center = ball.centery
                    if abs(paddle_center - ball_center) <= CENTER_THRESHOLD and last_paddle_hit != "right":
                        ball_dx = abs(ball_dx) * ACCEL_FACTOR
                        ball_dy = (ball_dy/abs(ball_dy) if ball_dy != 0 else 1) * abs(ball_dy) * ACCEL_FACTOR
                        last_paddle_hit = "right"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EFFECT_COLOR_CENTER)
                        ACCELERATED_SOUND.play()
                    elif ((ball_center - right_paddle.top) <= CENTER_THRESHOLD or (right_paddle.bottom - ball_center) <= CENTER_THRESHOLD) and last_paddle_hit != "right_edge":
                        ball_dx = abs(ball_dx) * ACCEL_FACTOR
                        last_paddle_hit = "right_edge"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EDGE_ZONE_COLOR)
                        ACCELERATED_SOUND.play()
                    else:
                        ball_dx = abs(ball_dx)
                        last_paddle_hit = "right"
                        add_effect((ball.centerx, ball.centery), accelerated=False, color=WHITE)
                        NORMAL_SOUND.play()
            else:
                # CPUモード：下側（プレイヤー）パドル
                if ball.colliderect(player_paddle) and ball_dy > 0:
                    paddle_center = player_paddle.centerx
                    ball_center = ball.centerx
                    if abs(paddle_center - ball_center) <= CENTER_THRESHOLD and last_paddle_hit != "player":
                        ball_dy = -abs(ball_dy) * ACCEL_FACTOR
                        ball_dx = (ball_dx/abs(ball_dx) if ball_dx != 0 else 1) * abs(ball_dx) * ACCEL_FACTOR
                        last_paddle_hit = "player"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EFFECT_COLOR_CENTER)
                        ACCELERATED_SOUND.play()
                    elif ((ball_center - player_paddle.left) <= CENTER_THRESHOLD or (player_paddle.right - ball_center) <= CENTER_THRESHOLD) and last_paddle_hit != "player_edge":
                        ball_dx = (ball_dx/abs(ball_dx) if ball_dx != 0 else 1) * abs(ball_dx) * ACCEL_FACTOR
                        last_paddle_hit = "player_edge"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EDGE_ZONE_COLOR)
                        ACCELERATED_SOUND.play()
                    else:
                        ball_dy = -abs(ball_dy)
                        last_paddle_hit = "player"
                        add_effect((ball.centerx, ball.centery), accelerated=False, color=WHITE)
                        NORMAL_SOUND.play()
                # CPUモード：上側（CPU）パドル
                if ball.colliderect(cpu_paddle) and ball_dy < 0:
                    paddle_center = cpu_paddle.centerx
                    ball_center = ball.centerx
                    if abs(paddle_center - ball_center) <= CENTER_THRESHOLD and last_paddle_hit != "cpu":
                        ball_dy = abs(ball_dy) * ACCEL_FACTOR
                        ball_dx = (ball_dx/abs(ball_dx) if ball_dx != 0 else 1) * abs(ball_dx) * ACCEL_FACTOR
                        last_paddle_hit = "cpu"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EFFECT_COLOR_CENTER)
                        ACCELERATED_SOUND.play()
                    elif ((ball_center - cpu_paddle.left) <= CENTER_THRESHOLD or (cpu_paddle.right - ball_center) <= CENTER_THRESHOLD) and last_paddle_hit != "cpu_edge":
                        ball_dx = (ball_dx/abs(ball_dx) if ball_dx != 0 else 1) * abs(ball_dx) * ACCEL_FACTOR
                        last_paddle_hit = "cpu_edge"
                        add_effect((ball.centerx, ball.centery), accelerated=True, color=EDGE_ZONE_COLOR)
                        ACCELERATED_SOUND.play()
                    else:
                        ball_dy = abs(ball_dy)
                        last_paddle_hit = "cpu"
                        add_effect((ball.centerx, ball.centery), accelerated=False, color=WHITE)
                        NORMAL_SOUND.play()

        # 描画処理
        screen.fill(BLACK)
        if mode == "PVP":
            pygame.draw.aaline(screen, WHITE, (w // 2, 0), (w // 2, h))
            draw_vertical_paddle(left_paddle, screen)
            draw_vertical_paddle(right_paddle, screen)
        else:
            pygame.draw.aaline(screen, WHITE, (0, h // 2), (w, h // 2))
            draw_horizontal_paddle(player_paddle, screen)
            draw_horizontal_paddle(cpu_paddle, screen)
        pygame.draw.ellipse(screen, WHITE, ball)
        update_and_draw_effects(screen)

        # スコア表示
        if mode == "PVP":
            score_text = font.render(f"LEFT: {score_left}   RIGHT: {score_right}", True, WHITE)
        else:
            score_text = font.render(f"PLAYER: {score_player}   CPU: {score_cpu}", True, WHITE)
        screen.blit(score_text, (w // 2 - score_text.get_width() // 2, 10))
        pygame.display.flip()

        # ゲームオーバー判定時の処理
        if game_over:
            GAME_CLEAR_SOUND.play()
            # ゲーム終了後、リプレイ（R）、タイトルへ戻る（T）、終了（Q）の選択画面を表示
            while True:
                screen.fill(BLACK)
                over_text = font.render(f"GAME OVER! WINNER: {winner}", True, WHITE)
                option_text = font.render("R: REPLAY   T: TITLE   Q: QUIT", True, WHITE)
                screen.blit(over_text, (w//2 - over_text.get_width()//2, h//2 - over_text.get_height()))
                screen.blit(option_text, (w//2 - option_text.get_width()//2, h//2 + 10))
                pygame.display.flip()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return "quit"
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            return "replay"
                        elif event.key == pygame.K_t:
                            return "title"
                        elif event.key == pygame.K_q:
                            return "quit"
                clock.tick(30)

# ---------- MAIN ----------
def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    while True:
        mode, cpu_level = main_menu(screen)
        result = game_loop(screen, mode, cpu_level)
        if result == "replay" or result == "title":
            continue
        elif result == "quit":
            break
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print("ERROR OCCURRED:", e)
        traceback.print_exc()
    input("PRESS ENTER TO EXIT")
    sys.exit()
