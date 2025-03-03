import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter
from PIL import Image, ImageOps

def pil2pixmap(pil_image):
    """PillowのImageオブジェクトをQPixmapに変換"""
    rgb_image = pil_image.convert("RGB")
    data = rgb_image.tobytes("raw", "RGB")
    qimage = QImage(data, rgb_image.width, rgb_image.height, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage)

class ImageCutterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.original_image = None  # Pillow Imageオブジェクト
        self.image_path = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("画像加工アプリ")
        self.setFixedSize(800, 600)  # ウィンドウサイズは常に一定
        main_layout = QVBoxLayout()

        # プレビュー領域（固定サイズ：400×300）
        self.preview_label = QLabel("プレビュー", self)
        self.preview_label.setFixedSize(400, 300)
        self.preview_label.setAlignment(Qt.AlignCenter)
        # 背景は透過（※スタイルシートで設定する場合、ウィジェット自体の背景色にはならないのでQPixmap側で処理）
        self.preview_label.setStyleSheet("border: 1px solid #CCC;")
        main_layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)

        # 操作パネル（カット量と拡大縮小）
        control_layout = QGridLayout()

        control_layout.addWidget(QLabel("上辺カット(px):"), 0, 0)
        self.top_spin = QSpinBox()
        self.top_spin.setRange(0, 1000)
        self.top_spin.valueChanged.connect(self.update_preview)
        control_layout.addWidget(self.top_spin, 0, 1)

        control_layout.addWidget(QLabel("下辺カット(px):"), 0, 2)
        self.bottom_spin = QSpinBox()
        self.bottom_spin.setRange(0, 1000)
        self.bottom_spin.valueChanged.connect(self.update_preview)
        control_layout.addWidget(self.bottom_spin, 0, 3)

        control_layout.addWidget(QLabel("左辺カット(px):"), 1, 0)
        self.left_spin = QSpinBox()
        self.left_spin.setRange(0, 1000)
        self.left_spin.valueChanged.connect(self.update_preview)
        control_layout.addWidget(self.left_spin, 1, 1)

        control_layout.addWidget(QLabel("右辺カット(px):"), 1, 2)
        self.right_spin = QSpinBox()
        self.right_spin.setRange(0, 1000)
        self.right_spin.valueChanged.connect(self.update_preview)
        control_layout.addWidget(self.right_spin, 1, 3)

        control_layout.addWidget(QLabel("拡大縮小(%):"), 2, 0)
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(1, 500)
        self.scale_spin.setValue(100)
        self.scale_spin.valueChanged.connect(self.update_preview)
        control_layout.addWidget(self.scale_spin, 2, 1)

        main_layout.addLayout(control_layout)

        # ボタン群：ファイル選択と決定
        button_layout = QHBoxLayout()
        self.select_button = QPushButton("ファイル選択")
        self.select_button.clicked.connect(self.open_file_dialog)
        button_layout.addWidget(self.select_button)

        self.process_button = QPushButton("決定")
        self.process_button.clicked.connect(self.process_image)
        self.process_button.setEnabled(False)
        button_layout.addWidget(self.process_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_files = [f for f in files if f.lower().endswith((
            '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'
        ))]
        if valid_files:
            self.load_image(valid_files[0])
        else:
            QMessageBox.warning(self, "エラー", "有効な画像ファイルをドロップしてください。")

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "画像ファイルを選択", "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, path):
        try:
            self.original_image = Image.open(path)
            self.image_path = path
            self.process_button.setEnabled(True)
            self.update_preview()
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"画像読み込みに失敗しました:\n{e}")

    def update_preview(self):
        if self.original_image is None:
            self.preview_label.setText("画像が読み込まれていません")
            return

        img = self.original_image.copy()
        orig_width, orig_height = img.size

        # カット値を画像サイズに合わせてクランプする
        top = min(self.top_spin.value(), orig_height)
        left = min(self.left_spin.value(), orig_width)
        bottom = min(self.bottom_spin.value(), max(0, orig_height - top))
        right = min(self.right_spin.value(), max(0, orig_width - left))

        crop_box = (left, top, orig_width - right, orig_height - bottom)
        if crop_box[0] >= crop_box[2] or crop_box[1] >= crop_box[3]:
            cropped = img  # カット範囲が無効なら元画像のまま
        else:
            cropped = img.crop(crop_box)

        # 拡大縮小適用
        scale_percent = self.scale_spin.value()
        new_width = int(cropped.width * scale_percent / 100)
        new_height = int(cropped.height * scale_percent / 100)
        processed_img = cropped.resize((new_width, new_height), Image.LANCZOS)

        # QPixmapに変換
        pixmap = pil2pixmap(processed_img)

        # プレビュー領域（400×300）に合わせて縦横比を保ちつつ拡縮、余白は透過
        preview_size = QSize(400, 300)
        # 背景は透明なQPixmap
        preview_pixmap = QPixmap(preview_size)
        preview_pixmap.fill(Qt.transparent)

        scaled_pixmap = pixmap.scaled(preview_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter = QPainter(preview_pixmap)
        x = (preview_size.width() - scaled_pixmap.width()) // 2
        y = (preview_size.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

        self.preview_label.setPixmap(preview_pixmap)

    def process_image(self):
        if self.original_image is None:
            return

        orig_width, orig_height = self.original_image.size
        top = min(self.top_spin.value(), orig_height)
        left = min(self.left_spin.value(), orig_width)
        bottom = min(self.bottom_spin.value(), max(0, orig_height - top))
        right = min(self.right_spin.value(), max(0, orig_width - left))

        crop_box = (left, top, orig_width - right, orig_height - bottom)
        if crop_box[0] >= crop_box[2] or crop_box[1] >= crop_box[3]:
            cropped = self.original_image
        else:
            cropped = self.original_image.crop(crop_box)

        scale_percent = self.scale_spin.value()
        new_width = int(cropped.width * scale_percent / 100)
        new_height = int(cropped.height * scale_percent / 100)
        processed_img = cropped.resize((new_width, new_height), Image.LANCZOS)

        # 出力先は実行ファイル（または.pyファイル）と同じフォルダに保存
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        base, ext = os.path.splitext(os.path.basename(self.image_path))
        output_name = f"{base}_1{ext}"
        output_path = os.path.join(base_path, output_name)
        counter = 1
        while os.path.exists(output_path):
            counter += 1
            output_name = f"{base}_{counter}{ext}"
            output_path = os.path.join(base_path, output_name)

        try:
            processed_img.save(output_path)
            QMessageBox.information(self, "完了", f"画像を保存しました:\n{output_path}")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"画像の保存に失敗しました:\n{e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageCutterApp()
    window.show()
    sys.exit(app.exec_())
