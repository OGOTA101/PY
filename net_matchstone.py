import pygame, sys, socket, threading, traceback, time, random

# -------------------------------
# グローバル例外ハンドラ（エラーダイアログ表示）
# -------------------------------
def global_excepthook(exc_type, exc_value, exc_tb):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(error_msg)
    pygame.init()
    error_screen = pygame.display.set_mode((800,600))
    pygame.display.set_caption("Unhandled Exception")
    font = pygame.font.SysFont("Arial", 20)
    clock = pygame.time.Clock()
    while True:
        error_screen.fill((0,0,0))
        y = 10
        for line in error_msg.splitlines():
            text = font.render(line, True, (255,0,0))
            error_screen.blit(text, (10, y))
            y += 25
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        clock.tick(10)

sys.excepthook = global_excepthook

# -------------------------------
# 定数
# -------------------------------
BOARD_SIZE = 15        # 15x15の盤面
CELL_SIZE = 30         # 各セルのサイズ
BOARD_WIDTH = BOARD_SIZE * CELL_SIZE
BOARD_HEIGHT = BOARD_SIZE * CELL_SIZE
MARGIN = 50            # 画面外側の余白

HOST_PORT = 50007      # デフォルトポート

# 色
WHITE = (255,255,255)
BLACK = (0,0,0)
RED   = (255,0,0)
BLUE  = (0,0,255)
GREEN = (0,255,0)

# ゲーム状態
STATE_MENU = "MENU"
STATE_WAIT = "WAIT"       # 部屋作成待ち or 参加待ち
STATE_GAME = "GAME"
STATE_GAMEOVER = "GAMEOVER"

# -------------------------------
# グローバル変数
# -------------------------------
state = STATE_MENU
is_host = False
connection = None  # ネットワーク接続用ソケット（両側で使用）
board = [[0]*BOARD_SIZE for _ in range(BOARD_SIZE)]  # 0:空, 1:黒, 2:白
turn = 1   # 1:ホスト(黒)のターン, 2:参加(白)のターン
winner = None

# ネットワークメッセージのロック
net_lock = threading.Lock()

# -------------------------------
# ヘルパー関数：テキストを中央に描画
# -------------------------------
def draw_text_center(surface, text, font, color, x, y):
    txt_obj = font.render(text, True, color)
    txt_rect = txt_obj.get_rect(center=(x,y))
    surface.blit(txt_obj, txt_rect)

# -------------------------------
# 勝利判定（5子連続）
# -------------------------------
def check_win(board, player):
    # 盤面内の各セルについて、水平、垂直、斜め（右下、右上）をチェック
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] != player:
                continue
            # 水平
            if x <= BOARD_SIZE - 5 and all(board[y][x+i]==player for i in range(5)):
                return True
            # 垂直
            if y <= BOARD_SIZE - 5 and all(board[y+i][x]==player for i in range(5)):
                return True
            # 右下斜め
            if x <= BOARD_SIZE - 5 and y <= BOARD_SIZE - 5 and all(board[y+i][x+i]==player for i in range(5)):
                return True
            # 右上斜め
            if x <= BOARD_SIZE - 5 and y >= 4 and all(board[y-i][x+i]==player for i in range(5)):
                return True
    return False

# -------------------------------
# ネットワーク受信スレッド
# -------------------------------
def network_listener(conn):
    global board, turn, state, winner
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            # 複数メッセージが来る場合も改行で分割
            messages = data.strip().split("\n")
            for msg in messages:
                parts = msg.split()
                if parts[0] == "MOVE":
                    # MOVE x y
                    x = int(parts[1])
                    y = int(parts[2])
                    # 相手の手番で受信したので、自動で盤面更新
                    with net_lock:
                        board[y][x] = 2 if is_host else 1
                        turn = 1 if turn==2 else 2
                    # 勝利判定
                    if check_win(board, 2 if is_host else 1):
                        winner = 2 if is_host else 1
                        state = STATE_GAMEOVER
                elif parts[0] == "NEWGAME":
                    reset_game()
    except Exception as e:
        print("Network error:", e)
    finally:
        conn.close()

# -------------------------------
# ゲーム再設定
# -------------------------------
def reset_game():
    global board, turn, winner
    board = [[0]*BOARD_SIZE for _ in range(BOARD_SIZE)]
    turn = 1  # ホスト先手
    winner = None

# -------------------------------
# サーバー起動（部屋作成）  
# -------------------------------
def start_server():
    global connection, is_host
    is_host = True
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("", HOST_PORT))
    server_sock.listen(1)
    print("待機中...（ポート", HOST_PORT, "）")
    conn, addr = server_sock.accept()
    print("接続:", addr)
    connection = conn
    threading.Thread(target=network_listener, args=(connection,), daemon=True).start()

# -------------------------------
# クライアント接続（部屋参加）
# -------------------------------
def connect_to_server(host_ip, port):
    global connection, is_host
    is_host = False
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((host_ip, port))
    connection = conn
    threading.Thread(target=network_listener, args=(connection,), daemon=True).start()

# -------------------------------
# 描画：盤面描画
# -------------------------------
def draw_board(surface):
    # 背景
    surface.fill(WHITE)
    # 盤面枠の左上座標
    start_x = (SCREEN_WIDTH - BOARD_WIDTH) // 2
    start_y = (SCREEN_HEIGHT - BOARD_HEIGHT) // 2
    # グリッド描画
    for i in range(BOARD_SIZE + 1):
        pygame.draw.line(surface, BLACK, (start_x, start_y + i*CELL_SIZE), (start_x + BOARD_WIDTH, start_y + i*CELL_SIZE))
        pygame.draw.line(surface, BLACK, (start_x + i*CELL_SIZE, start_y), (start_x + i*CELL_SIZE, start_y + BOARD_HEIGHT))
    # 石描画
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if board[y][x] != 0:
                center = (start_x + x*CELL_SIZE + CELL_SIZE//2, start_y + y*CELL_SIZE + CELL_SIZE//2)
                if board[y][x] == 1:
                    pygame.draw.circle(surface, BLACK, center, CELL_SIZE//2 - 2)
                else:
                    pygame.draw.circle(surface, WHITE, center, CELL_SIZE//2 - 2)
                    pygame.draw.circle(surface, BLACK, center, CELL_SIZE//2 - 2, 2)
    # ターン表示
    font = pygame.font.SysFont("Arial", 24)
    turn_text = "黒の番" if turn == 1 else "白の番"
    draw_text_center(surface, turn_text, font, RED, SCREEN_WIDTH//2, 30)

# -------------------------------
# メインゲームループ（Gomoku）
# -------------------------------
import socket
import threading

def game_loop():
    global state, board, turn, winner
    reset_game()
    game_running = True
    font = pygame.font.SysFont("Arial", 24)
    while game_running and state == STATE_GAME:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 盤面クリック処理（自分のターンのみ）
                if (is_host and turn == 1) or (not is_host and turn == 2):
                    mx, my = event.pos
                    start_x = (SCREEN_WIDTH - BOARD_WIDTH) // 2
                    start_y = (SCREEN_HEIGHT - BOARD_HEIGHT) // 2
                    if start_x <= mx <= start_x + BOARD_WIDTH and start_y <= my <= start_y + BOARD_HEIGHT:
                        cell_x = (mx - start_x) // CELL_SIZE
                        cell_y = (my - start_y) // CELL_SIZE
                        if board[cell_y][cell_x] == 0:
                            # 自分の色を置く
                            board[cell_y][cell_x] = 1 if is_host else 2
                            # 送信
                            msg = f"MOVE {cell_x} {cell_y}\n"
                            try:
                                connection.sendall(msg.encode())
                            except Exception as e:
                                print("Send error:", e)
                            # ターン交代
                            turn = 2 if turn == 1 else 1
                            if check_win(board, 1 if is_host else 2):
                                winner = 1 if is_host else 2
                                state = STATE_GAMEOVER
        draw_board(screen)
        pygame.display.flip()
        if winner is not None:
            state = STATE_GAMEOVER
        clock.tick(FPS)

# -------------------------------
# タイトル＆部屋選択画面
# -------------------------------
def menu_loop():
    global state, connection
    menu_running = True
    font_large = pygame.font.SysFont("Arial", 48)
    font_small = pygame.font.SysFont("Arial", 24)
    input_active = False
    input_text = ""
    mode = None  # "host" or "join"
    join_ip = ""
    while state == STATE_MENU:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                host_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, 200, 300, 50)
                join_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, 280, 300, 50)
                if host_rect.collidepoint(mx, my):
                    mode = "host"
                    state = STATE_WAIT
                elif join_rect.collidepoint(mx, my):
                    mode = "join"
                    input_active = True
        screen.fill(WHITE)
        draw_text_center(screen, "オンライン五目並べ", font_large, BLACK, SCREEN_WIDTH//2, 100)
        pygame.draw.rect(screen, GREEN, (SCREEN_WIDTH//2 - 150, 200, 300, 50))
        draw_text_center(screen, "部屋を作る（ホスト）", font_small, BLACK, SCREEN_WIDTH//2, 225)
        pygame.draw.rect(screen, GREEN, (SCREEN_WIDTH//2 - 150, 280, 300, 50))
        draw_text_center(screen, "部屋に入る（参加）", font_small, BLACK, SCREEN_WIDTH//2, 305)
        if input_active:
            draw_text_center(screen, "接続先IPアドレスを入力（例: 192.168.1.100）", font_small, BLACK, screen, SCREEN_WIDTH//2, 370)
            ip_box = pygame.Rect(SCREEN_WIDTH//2 - 150, 400, 300, 40)
            pygame.draw.rect(screen, WHITE, ip_box)
            pygame.draw.rect(screen, BLACK, ip_box, 2)
            ip_font = pygame.font.SysFont("Arial", 24)
            ip_text = ip_font.render(input_text, True, BLACK)
            screen.blit(ip_text, (ip_box.x+5, ip_box.y+5))
        pygame.display.flip()
        for event in pygame.event.get():
            if input_active and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    join_ip = input_text
                    input_active = False
                    state = STATE_WAIT
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode
        clock.tick(FPS)
    # 部屋待機画面へ進む
    if state == STATE_WAIT:
        waiting_loop(mode, join_ip)

# -------------------------------
# 部屋待機画面：ホストは待機、参加は接続
# -------------------------------
def waiting_loop(mode, join_ip):
    global state, connection
    waiting = True
    font_small = pygame.font.SysFont("Arial", 24)
    if mode == "host":
        threading.Thread(target=start_server, daemon=True).start()
        status_text = "部屋を作成中...相手の参加を待っています。"
    else:
        try:
            threading.Thread(target=connect_to_server, args=(join_ip, HOST_PORT), daemon=True).start()
            status_text = f"{join_ip} に接続中..."
        except Exception as e:
            status_text = f"接続に失敗しました: {e}"
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        screen.fill(WHITE)
        draw_text_center(screen, status_text, font_small, BLACK, SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        pygame.display.flip()
        # 接続が確立すれば次の画面へ
        if connection is not None:
            waiting = False
        clock.tick(FPS)
    # 接続後、ゲームループへ
    game_loop()

# -------------------------------
# ゲームオーバー画面
# -------------------------------
def game_over_loop():
    global state
    font_large = pygame.font.SysFont("Arial", 48)
    font_small = pygame.font.SysFont("Arial", 24)
    while state == STATE_GAMEOVER:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                state = STATE_MENU
        screen.fill(WHITE)
        if winner is not None:
            if winner == (1 if is_host else 2):
                result = "あなたの勝ち！"
            else:
                result = "あなたの負け！"
        else:
            result = "引き分け"
        draw_text_center(screen, "ゲームオーバー", font_large, BLACK, SCREEN_WIDTH//2, 150)
        draw_text_center(screen, result, font_small, RED, SCREEN_WIDTH//2, 250)
        draw_text_center(screen, "クリックでタイトルに戻る", font_small, BLACK, SCREEN_WIDTH//2, 350)
        pygame.display.flip()
        clock.tick(FPS)

# -------------------------------
# メインプログラム
# -------------------------------
pygame.init()
screen = pygame.display.set_mode((800,600))
pygame.display.set_caption("オンライン五目並べ")
clock = pygame.time.Clock()

# 初期状態
state = STATE_MENU
is_host = False
connection = None
player_score = 0
winner = None

while True:
    if state == STATE_MENU:
        menu_loop()
    elif state == STATE_GAME:
        game_loop()
    elif state == STATE_GAMEOVER:
        game_over_loop()
