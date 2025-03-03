# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import os, io, cairo

# PyGObjectによるPangoCairoの利用
import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

# ページサイズ（A5相当：1050×1485ピクセル）
PAGE_WIDTH = 1050
PAGE_HEIGHT = 1485

MAX_PAGES = 4  # プレビューで表示するページの上限

# ■ 縦書き用プリセット：段数（＝縦列数）と1段あたりの文字数
VERTICAL_PRESETS = {
    "文字小（2段・40字/段）": {"columns": 2, "chars_per_col": 40},
    "文字中（2段・35字/段）": {"columns": 2, "chars_per_col": 35},
    "文字大（2段・30字/段）": {"columns": 2, "chars_per_col": 30},
}

# ■ フォント選択用：Windows標準の代表的なフォント（その他も追加可能）
FONT_MAP = {
    "MS Gothic":        "C:/Windows/Fonts/msgothic.ttc",
    "Meiryo":           "C:/Windows/Fonts/meiryo.ttc",
    "Yu Gothic":        "C:/Windows/Fonts/YuGothM.ttc",
    "MS Mincho":        "C:/Windows/Fonts/msmincho.ttc",
    "Yu Mincho":        "C:/Windows/Fonts/YuMin-Medium.ttf",
    "Arial Unicode MS": "C:/Windows/Fonts/arialuni.ttf",
    "Calibri":          "C:/Windows/Fonts/calibri.ttf",
}

class ShinshoMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("親書メーカー（縦書き）")
        self.preview_update_job = None
        self.generated_images = []  # PIL.Image形式のページ画像リスト
        self.current_page = 0

        # デフォルト設定
        self.font_path = FONT_MAP["MS Gothic"]
        self.text_color = "#000000"

        # 画面レイアウト：左側パラメータ、右側文章入力＆プレビュー
        self.main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self.param_frame = tk.Frame(self.main_pane, padx=10, pady=10)
        self.main_pane.add(self.param_frame, minsize=350)

        self.right_frame = tk.Frame(self.main_pane, padx=10, pady=10)
        self.main_pane.add(self.right_frame, minsize=500)

        self.setup_parameters()
        self.setup_right_side()
        self.setup_variable_traces()

    # --------------------------------------------------
    # 左側：パラメータ設定（縦書き専用）
    # --------------------------------------------------
    def setup_parameters(self):
        tk.Label(self.param_frame, text="パラメータ設定（縦書き）", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0,5))
        
        # 装飾効果（「二本線」「上下線」「グラデ」）
        deco_frame = tk.LabelFrame(self.param_frame, text="装飾効果", padx=5, pady=5)
        deco_frame.pack(fill="x", pady=5)
        self.deco_style = tk.StringVar(value="二本線")
        for opt in ["二本線", "上下線", "グラデ"]:
            rb = tk.Radiobutton(deco_frame, text=opt, variable=self.deco_style, value=opt,
                                command=self.schedule_preview_update)
            rb.pack(anchor="w")
        # 装飾で使用する色
        color_frame = tk.Frame(deco_frame)
        color_frame.pack(fill="x", pady=5)
        tk.Label(color_frame, text="色１:").grid(row=0, column=0, sticky="w")
        self.color1 = "#000000"
        self.color1_button = tk.Button(color_frame, text="選択", command=self.pick_color1, width=8)
        self.color1_button.grid(row=0, column=1, padx=5)
        tk.Label(color_frame, text="色２:").grid(row=1, column=0, sticky="w")
        self.color2 = "#000000"
        self.color2_button = tk.Button(color_frame, text="選択", command=self.pick_color2, width=8)
        self.color2_button.grid(row=1, column=1, padx=5)

        # 文体編成（縦組プリセット）
        preset_frame = tk.LabelFrame(self.param_frame, text="文体編成（縦組）", padx=5, pady=5)
        preset_frame.pack(fill="x", pady=5)
        tk.Label(preset_frame, text="段数・1段あたりの文字数").pack(anchor="w")
        self.preset_var = tk.StringVar(value=list(VERTICAL_PRESETS.keys())[0])
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var,
                                         values=list(VERTICAL_PRESETS.keys()), state="readonly")
        self.preset_combo.pack(fill="x", pady=2)
        self.preset_combo.bind("<<ComboboxSelected>>", lambda e: self.schedule_preview_update())

        # 自力設定（余白、文字サイズ、行間）
        custom_frame = tk.LabelFrame(self.param_frame, text="自力設定", padx=5, pady=5)
        custom_frame.pack(fill="x", pady=5)
        tk.Label(custom_frame, text="左右余白(mm):").grid(row=0, column=0, sticky="w")
        self.margin_lr = tk.StringVar(value="40")
        tk.Entry(custom_frame, textvariable=self.margin_lr, width=5).grid(row=0, column=1, padx=5, pady=2)
        tk.Label(custom_frame, text="上下余白(mm):").grid(row=1, column=0, sticky="w")
        self.margin_tb = tk.StringVar(value="30")
        tk.Entry(custom_frame, textvariable=self.margin_tb, width=5).grid(row=1, column=1, padx=5, pady=2)
        tk.Label(custom_frame, text="文字サイズ(pt):").grid(row=2, column=0, sticky="w")
        self.font_size = tk.StringVar(value="32")
        tk.Entry(custom_frame, textvariable=self.font_size, width=5).grid(row=2, column=1, padx=5, pady=2)
        tk.Label(custom_frame, text="行間(%):").grid(row=3, column=0, sticky="w")
        # 行間はセルの高さに対する倍率（100でそのまま）
        self.line_spacing = tk.StringVar(value="100")
        tk.Entry(custom_frame, textvariable=self.line_spacing, width=5).grid(row=3, column=1, padx=5, pady=2)

        # 縦組設定：段数（縦列数）と1段あたりの文字数
        vertical_frame = tk.LabelFrame(self.param_frame, text="縦組設定", padx=5, pady=5)
        vertical_frame.pack(fill="x", pady=5)
        tk.Label(vertical_frame, text="段数（列数）:").grid(row=0, column=0, sticky="w")
        self.vert_columns = tk.StringVar(value="2")
        tk.Entry(vertical_frame, textvariable=self.vert_columns, width=5).grid(row=0, column=1, padx=5, pady=2)
        tk.Label(vertical_frame, text="1段あたりの文字数:").grid(row=1, column=0, sticky="w")
        self.vert_chars = tk.StringVar(value="40")
        tk.Entry(vertical_frame, textvariable=self.vert_chars, width=5).grid(row=1, column=1, padx=5, pady=2)

        # フォント＆文字色選択
        font_frame = tk.LabelFrame(self.param_frame, text="フォント・文字色", padx=5, pady=5)
        font_frame.pack(fill="x", pady=5)
        tk.Label(font_frame, text="フォント:").pack(side="left")
        self.font_choice = tk.StringVar(value="MS Gothic")
        self.font_combo = ttk.Combobox(font_frame, textvariable=self.font_choice,
                                       values=list(FONT_MAP.keys()), state="readonly")
        self.font_combo.pack(side="left", padx=5)
        self.font_combo.bind("<<ComboboxSelected>>", self.change_font)
        tk.Label(font_frame, text="文字色:").pack(side="left", padx=(10,0))
        self.text_color_button = tk.Button(font_frame, text="選択", command=self.pick_text_color)
        self.text_color_button.pack(side="left", padx=5)
        self.text_color_label = tk.Label(font_frame, text=self.text_color, bg=self.text_color, width=8)
        self.text_color_label.pack(side="left", padx=5)

        # 出力ボタン
        self.export_button = tk.Button(self.param_frame, text="出力", command=self.output_images)
        self.export_button.pack(pady=10)

    # --------------------------------------------------
    # 右側：文章入力＆プレビュー
    # --------------------------------------------------
    def setup_right_side(self):
        self.right_pane = tk.PanedWindow(self.right_frame, orient=tk.VERTICAL)
        self.right_pane.pack(fill=tk.BOTH, expand=True)

        # 文章入力欄
        input_frame = tk.Frame(self.right_pane, padx=5, pady=5)
        self.right_pane.add(input_frame, minsize=150)
        tk.Label(input_frame, text="文章入力", font=("Arial", 12, "bold")).pack(anchor="w")
        self.text_input = tk.Text(input_frame, width=60, height=10)
        self.text_input.pack(fill=tk.BOTH, expand=True)
        self.text_input.bind("<KeyRelease>", lambda e: self.schedule_preview_update())

        # プレビュー表示領域（1ページずつ表示）
        preview_container = tk.Frame(self.right_pane)
        self.right_pane.add(preview_container, minsize=200)
        tk.Label(preview_container, text="プレビュー", font=("Arial", 12, "bold")).pack(anchor="w")
        self.preview_canvas = tk.Canvas(preview_container, bg="white", height=400)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_frame = tk.Frame(self.preview_canvas)
        self.preview_canvas.create_window((0,0), window=self.preview_frame, anchor="nw")
        self.preview_frame.bind("<Configure>", lambda e: self.preview_canvas.configure(
            scrollregion=self.preview_canvas.bbox("all")))

        # ページ切替ボタン
        self.nav_frame = tk.Frame(self.right_frame)
        self.nav_frame.pack(fill="x", pady=5)
        self.prev_button = tk.Button(self.nav_frame, text="前のページ", command=self.show_prev_page)
        self.prev_button.pack(side="left", padx=5)
        self.page_label = tk.Label(self.nav_frame, text="Page 1/1")
        self.page_label.pack(side="left", padx=5)
        self.next_button = tk.Button(self.nav_frame, text="次のページ", command=self.show_next_page)
        self.next_button.pack(side="left", padx=5)

    def setup_variable_traces(self):
        self.font_size.trace("w", self.schedule_preview_update)
        self.margin_lr.trace("w", self.schedule_preview_update)
        self.margin_tb.trace("w", self.schedule_preview_update)
        self.line_spacing.trace("w", self.schedule_preview_update)
        self.vert_columns.trace("w", self.schedule_preview_update)
        self.vert_chars.trace("w", self.schedule_preview_update)

    def schedule_preview_update(self, *args):
        if self.preview_update_job is not None:
            self.root.after_cancel(self.preview_update_job)
        self.preview_update_job = self.root.after(300, self.update_preview)

    # --------------------------------------------------
    # 色・フォント選択
    # --------------------------------------------------
    def pick_color1(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.color1 = color
            self.schedule_preview_update()

    def pick_color2(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.color2 = color
            self.schedule_preview_update()

    def pick_text_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.text_color = color
            self.text_color_label.configure(text=color, bg=color)
            self.schedule_preview_update()

    def change_font(self, event):
        sel = self.font_choice.get()
        if sel in FONT_MAP:
            self.font_path = FONT_MAP[sel]
            self.schedule_preview_update()

    # --------------------------------------------------
    # プレビュー更新（縦書き専用）
    # --------------------------------------------------
    def update_preview(self):
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            return
        # 改行除去して連続文字列に
        clean_text = "".join(text.splitlines())
        # 縦組プリセットから、段数と1段あたりの文字数を取得
        preset = VERTICAL_PRESETS.get(self.preset_var.get(), list(VERTICAL_PRESETS.values())[0])
        try:
            columns = int(self.vert_columns.get())
        except:
            columns = preset["columns"]
        try:
            chars_per_col = int(self.vert_chars.get())
        except:
            chars_per_col = preset["chars_per_col"]

        capacity = columns * chars_per_col

        # ページごとに分割（最大4ページまで）
        pages = [clean_text[i:i+capacity] for i in range(0, len(clean_text), capacity)]
        pages = pages[:MAX_PAGES]

        self.generated_images = []
        for page_text in pages:
            img = self.generate_page(page_text, columns, chars_per_col)
            if img:
                self.generated_images.append(img)
        if self.generated_images:
            self.current_page = 0
            self.show_current_page()
            self.update_nav_buttons()

    # --------------------------------------------------
    # 1ページ分の画像生成（縦書き：PangoCairo利用）
    # --------------------------------------------------
    def generate_page(self, page_text, columns, chars_per_col):
        try:
            # 各パラメータの取得
            fs = int(self.font_size.get()) if self.font_size.get().isdigit() else 32
            ls_factor = int(self.line_spacing.get()) if self.line_spacing.get().isdigit() else 100
            margin_lr = int(self.margin_lr.get()) if self.margin_lr.get().isdigit() else 40
            margin_tb = int(self.margin_tb.get()) if self.margin_tb.get().isdigit() else 30

            # 利用可能領域
            avail_width = PAGE_WIDTH - 2 * margin_lr
            avail_height = PAGE_HEIGHT - 2 * margin_tb
            col_width = avail_width / columns

            # ページ内のテキストを、各列ごとに分割
            cols_text = []
            for i in range(columns):
                start = i * chars_per_col
                end = start + chars_per_col
                cols_text.append(page_text[start:end])

            # Cairoの画像サーフェス作成
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, PAGE_WIDTH, PAGE_HEIGHT)
            cr = cairo.Context(surface)
            # 背景を白で塗りつぶす
            cr.set_source_rgb(1,1,1)
            cr.paint()

            # 各列を右から左に配置
            for col_index, col_text in enumerate(cols_text):
                # X座標：右端から開始
                x = margin_lr + (columns - 1 - col_index) * col_width
                y = margin_tb

                # PangoCairo レイアウトの作成
                layout = PangoCairo.create_layout(cr)
                layout.set_text(col_text, -1)
                # フォント指定（例："MS Gothic 32"）
                font_desc = Pango.FontDescription(f"{self.font_choice.get()} {fs}")
                layout.set_font_description(font_desc)
                # 縦書き用のオリエンテーション設定
                layout.set_orientation(Pango.Orientation.VERTICAL)
                # 列の幅を設定（Pango単位に変換）
                layout.set_width(int(col_width * Pango.SCALE))
                # レイアウトを描画
                cr.move_to(x, y)
                PangoCairo.show_layout(cr, layout)

            # 装飾効果を描画
            self.draw_deco_pango(cr, PAGE_WIDTH, PAGE_HEIGHT, margin_lr, margin_tb)

            # ページ番号（下中央）もPangoで描画
            page_num = f"{self.current_page+1}"
            num_layout = PangoCairo.create_layout(cr)
            num_layout.set_text(page_num, -1)
            num_font_desc = Pango.FontDescription(f"{self.font_choice.get()} {int(fs*0.8)}")
            num_layout.set_font_description(num_font_desc)
            # ページ番号は横書き（通常）
            # 幅・高さを取得
            ink_rect, logical_rect = num_layout.get_pixel_extents()
            num_w = logical_rect.width
            num_h = logical_rect.height
            num_x = (PAGE_WIDTH - num_w) / 2
            num_y = PAGE_HEIGHT - margin_tb - num_h
            cr.move_to(num_x, num_y)
            cr.set_source_rgb(0.5, 0.5, 0.5)  # 灰色
            PangoCairo.show_layout(cr, num_layout)

            # Cairo SurfaceをPNGデータにしてPIL.Imageに変換
            buf = io.BytesIO()
            surface.write_to_png(buf)
            buf.seek(0)
            from PIL import Image
            pil_img = Image.open(buf)
            # PIL.ImageをRGBに変換（余計なalpha情報除去）
            pil_img = pil_img.convert("RGB")
            return pil_img

        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return None

    # --------------------------------------------------
    # 装飾効果の描画（Cairo）
    # --------------------------------------------------
    def draw_deco_pango(self, cr, img_width, img_height, margin_lr, margin_tb):
        style = self.deco_style.get()
        if style == "二本線":
            top_y = margin_tb / 2
            bottom_y = img_height - margin_tb / 2
            cr.set_line_width(2)
            # 上部2本線
            cr.set_source_rgb(*self.hex_to_rgb_normalized(self.color1))
            cr.move_to(margin_lr, top_y)
            cr.line_to(img_width - margin_lr, top_y)
            cr.stroke()
            cr.move_to(margin_lr, top_y+3)
            cr.line_to(img_width - margin_lr, top_y+3)
            cr.stroke()
            # 下部2本線
            cr.set_source_rgb(*self.hex_to_rgb_normalized(self.color2))
            cr.move_to(margin_lr, bottom_y)
            cr.line_to(img_width - margin_lr, bottom_y)
            cr.stroke()
            cr.move_to(margin_lr, bottom_y-3)
            cr.line_to(img_width - margin_lr, bottom_y-3)
            cr.stroke()
        elif style == "上下線":
            top_y = margin_tb / 2
            bottom_y = img_height - margin_tb / 2
            cr.set_line_width(3)
            cr.set_source_rgb(*self.hex_to_rgb_normalized(self.color1))
            cr.move_to(margin_lr, top_y)
            cr.line_to(img_width - margin_lr, top_y)
            cr.stroke()
            cr.set_source_rgb(*self.hex_to_rgb_normalized(self.color2))
            cr.move_to(margin_lr, bottom_y)
            cr.line_to(img_width - margin_lr, bottom_y)
            cr.stroke()
        elif style == "グラデ":
            grad_height = 10
            # 上部グラデーション：色1 → 白
            for i in range(grad_height):
                ratio = i / grad_height
                r, g, b = self.interpolate_color(self.color1, "#FFFFFF", ratio)
                cr.set_source_rgb(r, g, b)
                cr.move_to(margin_lr, margin_tb/2 + i)
                cr.line_to(img_width - margin_lr, margin_tb/2 + i)
                cr.stroke()
            # 下部グラデーション：白 → 色2
            for i in range(grad_height):
                ratio = i / grad_height
                r, g, b = self.interpolate_color("#FFFFFF", self.color2, ratio)
                cr.set_source_rgb(r, g, b)
                cr.move_to(margin_lr, img_height - margin_tb/2 - i)
                cr.line_to(img_width - margin_lr, img_height - margin_tb/2 - i)
                cr.stroke()

    def hex_to_rgb_normalized(self, hex_color):
        # 0〜1の範囲に正規化
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)

    def interpolate_color(self, hex1, hex2, ratio):
        # 2色の間を補間（ratio: 0〜1）
        hex1 = hex1.lstrip("#")
        hex2 = hex2.lstrip("#")
        r1, g1, b1 = int(hex1[0:2], 16), int(hex1[2:4], 16), int(hex1[4:6], 16)
        r2, g2, b2 = int(hex2[0:2], 16), int(hex2[2:4], 16), int(hex2[4:6], 16)
        r = int(r1 + (r2 - r1) * ratio) / 255.0
        g = int(g1 + (g2 - g1) * ratio) / 255.0
        b = int(b1 + (b2 - b1) * ratio) / 255.0
        return (r, g, b)

    # --------------------------------------------------
    # ページ切替・プレビュー表示
    # --------------------------------------------------
    def show_current_page(self):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        img = self.generated_images[self.current_page]
        img_tk = ImageTk.PhotoImage(img)
        lbl = tk.Label(self.preview_frame, image=img_tk, bd=2, relief="groove")
        lbl.image = img_tk
        lbl.pack()
        self.page_label.configure(text=f"Page {self.current_page+1}/{len(self.generated_images)}")

    def show_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_current_page()
            self.update_nav_buttons()

    def show_next_page(self):
        if self.current_page < len(self.generated_images) - 1:
            self.current_page += 1
            self.show_current_page()
            self.update_nav_buttons()

    def update_nav_buttons(self):
        self.prev_button.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.current_page < len(self.generated_images)-1 else "disabled")

    # --------------------------------------------------
    # 画像出力
    # --------------------------------------------------
    def output_images(self):
        if not self.generated_images:
            messagebox.showwarning("注意", "プレビュー画像がありません。")
            return
        save_dir = filedialog.askdirectory(title="画像の保存先を選択")
        if not save_dir:
            return
        fmt = "PNG"
        for idx, img in enumerate(self.generated_images):
            file_path = os.path.join(save_dir, f"output_page_{idx+1}.{fmt.lower()}")
            img.save(file_path, fmt)
        messagebox.showinfo("完了", f"{len(self.generated_images)} 枚の画像を保存しました。")

# --------------------------------------------------
# メイン処理
# --------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ShinshoMakerApp(root)
    root.mainloop()
