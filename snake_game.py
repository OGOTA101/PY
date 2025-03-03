import pygame
import random
import sys

# 初期化
pygame.init()

# 画面サイズと色の定義
WIDTH, HEIGHT = 600, 400
game_window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game")

# 色の定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# ゲーム設定
snake_block = 20      # スネークのブロックサイズ
snake_speed = 10      # ゲームのスピード

clock = pygame.time.Clock()

# フォント
font_style = pygame.font.SysFont(None, 50)

def message(msg, color):
    """メッセージ描画用関数"""
    mesg = font_style.render(msg, True, color)
    game_window.blit(mesg, [WIDTH / 6, HEIGHT / 3])

def gameLoop():
    game_over = False
    game_close = False

    # スネークの初期位置
    x = WIDTH / 2
    y = HEIGHT / 2
    x_change = 0
    y_change = 0

    snake_list = []       # スネークの各ブロックの位置
    length_of_snake = 1   # スネークの初期長さ

    # 食べ物の初期位置（グリッドに合わせる）
    food_x = round(random.randrange(0, WIDTH - snake_block) / snake_block) * snake_block
    food_y = round(random.randrange(0, HEIGHT - snake_block) / snake_block) * snake_block

    while not game_over:

        # ゲームオーバー時の処理
        while game_close:
            game_window.fill(BLACK)
            message("Game Over! C-Play Again or Q-Quit", RED)
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        game_close = False
                    if event.key == pygame.K_c:
                        gameLoop()

        # イベント処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    x_change = -snake_block
                    y_change = 0
                elif event.key == pygame.K_RIGHT:
                    x_change = snake_block
                    y_change = 0
                elif event.key == pygame.K_UP:
                    y_change = -snake_block
                    x_change = 0
                elif event.key == pygame.K_DOWN:
                    y_change = snake_block
                    x_change = 0

        # 画面外に出たらゲームオーバー
        if x >= WIDTH or x < 0 or y >= HEIGHT or y < 0:
            game_close = True

        x += x_change
        y += y_change
        game_window.fill(BLACK)

        # 食べ物を描画
        pygame.draw.rect(game_window, GREEN, [food_x, food_y, snake_block, snake_block])

        # スネークの体の処理
        snake_head = []
        snake_head.append(x)
        snake_head.append(y)
        snake_list.append(snake_head)
        if len(snake_list) > length_of_snake:
            del snake_list[0]

        # 自分自身に衝突したらゲームオーバー
        for segment in snake_list[:-1]:
            if segment == snake_head:
                game_close = True

        # スネークを描画
        for segment in snake_list:
            pygame.draw.rect(game_window, WHITE, [segment[0], segment[1], snake_block, snake_block])

        pygame.display.update()

        # 食べ物を食べたら、食べ物を新しい位置に移動、スネークの長さを増加
        if x == food_x and y == food_y:
            food_x = round(random.randrange(0, WIDTH - snake_block) / snake_block) * snake_block
            food_y = round(random.randrange(0, HEIGHT - snake_block) / snake_block) * snake_block
            length_of_snake += 1

        clock.tick(snake_speed)

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    gameLoop()