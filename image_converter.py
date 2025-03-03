import sys, os, traceback
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, QVBoxLayout, 
    QHBoxLayout, QCheckBox, QListWidget, QLineEdit, QSlider, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QPixmap
from PIL import Image, ImageEnhance, ImageFilter

# -------------------------------
# グローバル例外ハンドラ
# -------------------------------
def global_excepthook(exc_type, exc_value, exc_tb):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Unhandled Exception")
    msg_box.setText("予期せぬエラーが発生しました。")
    msg_box.setDetailedText(error_msg)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.exec_()

sys.excepthook = global_excepthook

# -------------------------------
# 画像編集＆変換ツールクラス
# -------------------------------
class ImageConverterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("画像編集＆変換ツール")
        self.resize(800, 600)
        self.file_paths = []  # 追加された画像ファイルのパスリスト
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        # プレビューエリア（ウィンドウ最上部）
        self.preview_label = QLabel("プレビュー領域")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedHeight(200)
        main_layout.addWidget(self.preview_label)

        # 説明ラベル
        instruct_label = QLabel("画像をドラッグ＆ドロップまたはファイル選択で追加してください。")
        instruct_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(instruct_label)

        # 追加された画像ファイルのパスを表示するリスト
        self.listWidget = QListWidget()
        main_layout.addWidget(self.listWidget)

        # 出力形式選択：チェックボックス（初期状態はPNGのみチェック）
        format_layout = QHBoxLayout()
        format_label = QLabel("変換先の形式:")
        format_label.setFixedWidth(120)
        format_layout.addWidget(format_label)
        self.formats = ["png", "jpeg", "bmp", "gif", "tiff", "webp", "ico", "pdf", "svg", "hdr", "psd"]
        self.format_checkboxes = []
        for fmt in self.formats:
            cb = QCheckBox(fmt.upper())
            cb.setChecked(True if fmt == "png" else False)
            self.format_checkboxes.append(cb)
            format_layout.addWidget(cb)
        main_layout.addLayout(format_layout)

        # 画像調整用スライダー群
        adjust_layout = QVBoxLayout()
        adjust_title = QLabel("画像調整")
        adjust_title.setAlignment(Qt.AlignCenter)
        adjust_layout.addWidget(adjust_title)
        
        # ヘルパー関数：ラベル、スライダー、数値表示ラベルを水平に配置して返す
        def create_slider(label_text, min_val, max_val, init_val):
            layout = QHBoxLayout()
            lbl = QLabel(f"{label_text}:")
            lbl.setFixedWidth(80)
            layout.addWidget(lbl)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(init_val)
            slider.setFixedHeight(15)
            slider.setFixedWidth(200)
            layout.addWidget(slider)
            value_label = QLabel(str(init_val))
            value_label.setFixedWidth(40)
            layout.addWidget(value_label)
            # 変更時に値表示を更新し、プレビューも更新
            slider.valueChanged.connect(lambda v: (value_label.setText(str(v)), self.update_preview()))
            layout.setContentsMargins(10, 2, 10, 2)
            return slider, layout

        # 各調整スライダーを作成し、インスタンス属性に格納
        self.slider_brightness, bright_layout = create_slider("明るさ", 50, 150, 100)
        adjust_layout.addLayout(bright_layout)
        self.slider_contrast, contrast_layout = create_slider("コントラスト", 50, 150, 100)
        adjust_layout.addLayout(contrast_layout)
        self.slider_sharpness, sharp_layout = create_slider("鮮明度", 50, 150, 100)
        adjust_layout.addLayout(sharp_layout)
        self.slider_blur, blur_layout = create_slider("ぼかし", 0, 20, 0)
        adjust_layout.addLayout(blur_layout)
        self.slider_hue, hue_layout = create_slider("色相", -180, 180, 0)
        adjust_layout.addLayout(hue_layout)
        
        # フィルター選択：モノクロ、セピア
        filter_layout = QHBoxLayout()
        self.cb_monochrome = QCheckBox("モノクロ")
        self.cb_monochrome.stateChanged.connect(self.update_preview)
        filter_layout.addWidget(self.cb_monochrome)
        self.cb_sepia = QCheckBox("セピア")
        self.cb_sepia.stateChanged.connect(self.update_preview)
        filter_layout.addWidget(self.cb_sepia)
        filter_layout.addStretch()
        adjust_layout.addLayout(filter_layout)
        main_layout.addLayout(adjust_layout)

        # 追加の文字列入力欄（ファイル名に付与する文字列）
        suffix_layout = QHBoxLayout()
        suffix_label = QLabel("付与文字列:")
        suffix_label.setFixedWidth(120)
        suffix_layout.addWidget(suffix_label)
        self.suffix_line = QLineEdit()
        self.suffix_line.textChanged.connect(self.update_preview)
        suffix_layout.addWidget(self.suffix_line)
        main_layout.addLayout(suffix_layout)

        # ボタン群：ファイル選択、変換実行
        button_layout = QHBoxLayout()
        self.btn_select = QPushButton("ファイル選択")
        self.btn_select.clicked.connect(self.open_file_dialog)
        button_layout.addWidget(self.btn_select)
        self.btn_convert = QPushButton("変換")
        self.btn_convert.clicked.connect(self.convert_images)
        button_layout.addWidget(self.btn_convert)
        main_layout.addLayout(button_layout)

        # ステータス表示ラベル
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)
        self.setAcceptDrops(True)

    # -------------------------------
    # ドラッグ＆ドロップ処理
    # -------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            self.file_paths.append(file_path)
            self.listWidget.addItem(file_path)
        self.status_label.setText("")
        event.acceptProposedAction()
        self.update_preview()

    # -------------------------------
    # ファイル選択ダイアログから画像追加
    # -------------------------------
    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "画像ファイルを選択", "", "All Files (*)")
        if files:
            for f in files:
                self.file_paths.append(f)
                self.listWidget.addItem(f)
            self.status_label.setText("")
            self.update_preview()

    # -------------------------------
    # 出力形式の取得（複数形式）
    # -------------------------------
    def get_target_formats(self):
        selected = []
        for cb, fmt in zip(self.format_checkboxes, self.formats):
            if cb.isChecked():
                selected.append(fmt)
        return selected

    # -------------------------------
    # 画像調整処理：各スライダー・フィルターを適用
    # -------------------------------
    def apply_adjustments(self, img):
        # 明るさ調整（1.0がデフォルト）
        brightness = self.slider_brightness.value() / 100.0
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)
        # コントラスト調整
        contrast = self.slider_contrast.value() / 100.0
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)
        # 鮮明度（シャープネス）調整
        sharpness = self.slider_sharpness.value() / 100.0
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpness)
        # ぼかし処理
        blur_radius = self.slider_blur.value()
        if blur_radius > 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        # 色相調整：画像をHSVに変換し、H成分にオフセットを加算してRGBに戻す
        hue_shift = self.slider_hue.value()
        if hue_shift != 0:
            hsv = img.convert("HSV")
            h, s, v = hsv.split()
            shift = int(hue_shift * 255 / 360)
            h = h.point(lambda p: (p + shift) % 256)
            hsv = Image.merge("HSV", (h, s, v))
            img = hsv.convert("RGB")
        # モノクロフィルター
        if self.cb_monochrome.isChecked():
            img = img.convert("L").convert("RGB")
        # セピアフィルター
        if self.cb_sepia.isChecked():
            img = self.apply_sepia(img)
        return img

    # -------------------------------
    # セピアフィルターの適用
    # -------------------------------
    def apply_sepia(self, img):
        width, height = img.size
        pixels = img.load()
        for py in range(height):
            for px in range(width):
                r, g, b = img.getpixel((px, py))
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                pixels[px, py] = (min(255, tr), min(255, tg), min(255, tb))
        return img

    # -------------------------------
    # プレビュー更新：最初の画像に調整を即時反映して表示
    # -------------------------------
    def update_preview(self):
        if not self.file_paths:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText("画像が追加されていません！")
            return
        try:
            img = Image.open(self.file_paths[0])
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"画像の読み込みに失敗しました: {str(e)}")
            return
        img = self.apply_adjustments(img)
        preview_img = img.copy()
        preview_img.thumbnail((self.preview_label.width(), self.preview_label.height()))
        temp_file = "temp_preview.png"
        preview_img.save(temp_file)
        pix = QPixmap(temp_file)
        self.preview_label.setPixmap(pix)
        os.remove(temp_file)
        self.status_label.setText("プレビュー更新完了！")

    # -------------------------------
    # 画像変換処理：各画像に調整を適用し、選択された各形式に変換
    # -------------------------------
    def convert_images(self):
        target_formats = self.get_target_formats()
        if not target_formats:
            self.status_label.setStyleSheet("color: red;")
            self.status_label.setText("画像形式を選択してください！")
            return
        else:
            self.status_label.setStyleSheet("color: black;")
        user_suffix = self.suffix_line.text().strip()
        errors = []
        same_format_flag = False
        for file_path in self.file_paths:
            try:
                img = Image.open(file_path)
            except Exception as e:
                errors.append(f"{file_path}: 画像の読み込みに失敗 ({str(e)})")
                continue
            img = self.apply_adjustments(img)
            dir_name = os.path.dirname(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            original_ext = os.path.splitext(file_path)[1].lower().replace(".", "")
            for fmt in target_formats:
                if fmt == original_ext:
                    same_format_flag = True
                    continue  # 同じ形式はスキップ
                new_file = os.path.join(dir_name, f"{base_name}{user_suffix}.{fmt}")
                try:
                    if fmt == "pdf":
                        img.convert("RGB").save(new_file, "PDF")
                    else:
                        img.save(new_file, fmt.upper())
                except Exception as e:
                    errors.append(f"{file_path} -> {fmt.upper()}: {str(e)}")
                    continue
        if errors:
            QMessageBox.warning(self, "変換エラー", "以下のファイル変換に失敗しました:\n" + "\n".join(errors))
        else:
            success_msg = "変換成功！"
            if same_format_flag:
                success_msg += " （同じ形式が選択されているファイルがありました）"
            self.status_label.setText(success_msg)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageConverterApp()
    ex.show()
    sys.exit(app.exec_())