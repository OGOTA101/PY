import pygame
import sys
import random

# 初期化
pygame.init()

# 画面サイズ設定
WIDTH, HEIGHT = 400, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird Clone")

clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 40)

# 鳥の設定
bird_x = 50
bird_y = HEIGHT // 2
bird_radius = 20
bird_vel = 0
gravity = 0.5
jump_strength = -10

# パイプの設定
pipe_width = 70
pipe_gap = 150  # パイプの隙間の高さ
pipe_speed = 3
pipe_list = []  # 各パイプは [x, gap_y] の形式（gap_y: 上側パイプの高さ）
pipe_spawn_interval = 1500  # ミリ秒
last_pipe_time = pygame.time.get_ticks()

score = 0

def draw_bird():
    pygame.draw.circle(screen, (255, 255, 0), (int(bird_x), int(bird_y)), bird_radius)

def draw_pipes():
    for pipe in pipe_list:
        x, gap_y = pipe
        # 上側パイプ
        pygame.draw.rect(screen, (0, 255, 0), (x, 0, pipe_width, gap_y))
        # 下側パイプ
        pygame.draw.rect(screen, (0, 255, 0), (x, gap_y + pipe_gap, pipe_width, HEIGHT - (gap_y + pipe_gap)))

def reset_balloon():
    global bird_y, bird_vel
    bird_y = HEIGHT // 2
    bird_vel = 0

def reset_pipes():
    global pipe_list, last_pipe_time
    pipe_list = []
    last_pipe_time = pygame.time.get_ticks()

def reset_game():
    global score
    reset_balloon()
    reset_pipes()
    score = 0

def check_collision():
    # 画面上端または下端に衝突
    if bird_y - bird_radius <= 0 or bird_y + bird_radius >= HEIGHT:
        return True
    # 各パイプとの衝突チェック
    for pipe in pipe_list:
        x, gap_y = pipe
        if bird_x + bird_radius > x and bird_x - bird_radius < x + pipe_width:
            if bird_y - bird_radius < gap_y or bird_y + bird_radius > gap_y + pipe_gap:
                return True
    return False

# メインループ
running = True
game_over = False

while running:
    clock.tick(60)  # 60FPS
    screen.fill((135, 206, 235))  # 空の色（スカイブルー）

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # スペースキーで上昇
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not game_over:
                bird_vel = jump_strength
            if event.key == pygame.K_r and game_over:
                reset_game()
                game_over = False

    if not game_over:
        # 鳥の物理計算
        bird_vel += gravity
        bird_y += bird_vel

        # パイプのスポーン
        current_time = pygame.time.get_ticks()
        if current_time - last_pipe_time > pipe_spawn_interval:
            gap_y = random.randint(50, HEIGHT - 50 - pipe_gap)
            pipe_list.append([WIDTH, gap_y])
            last_pipe_time = current_time

        # パイプを左に移動
        for pipe in pipe_list:
            pipe[0] -= pipe_speed

        # 画面外のパイプは削除
        pipe_list = [pipe for pipe in pipe_list if pipe[0] + pipe_width > 0]

        # 衝突チェック
        if check_collision():
            game_over = True

        # パイプを通過したらスコアを加算
        for pipe in pipe_list:
            x, gap_y = pipe
            # パイプの右端が鳥のx座標を通過したとき
            if x + pipe_width < bird_x and pipe[0] != -100:
                score += 1
                # スコア済みマークとして、x座標に -100 をセット
                pipe[0] = -100

    draw_bird()
    draw_pipes()

    # スコア描画
    score_text = font.render(f"Score: {score}", True, (0, 0, 0))
    screen.blit(score_text, (10, 10))

    if game_over:
        over_text = font.render("Game Over! Press R to Restart", True, (255, 0, 0))
        screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2 - over_text.get_height() // 2))

    pygame.display.flip()

pygame.quit()
sys.exit()
