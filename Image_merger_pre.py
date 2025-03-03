import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from PIL import Image, ImageOps

class ImageMergerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.image_paths = []
        self.merged_image = None  # 連結後の画像を保存

    def initUI(self):
        self.setWindowTitle("Image Merger with Preview")
        self.setGeometry(100, 100, 500, 400)

        layout = QVBoxLayout()

        # 説明ラベル
        self.label = QLabel('画像をドラッグ＆ドロップしてください。複数枚を結合します。', self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # 結合方向の選択
        hbox_direction = QHBoxLayout()
        hbox_direction.addWidget(QLabel("結合方法:", self))
        
        self.direction_group = QButtonGroup(self)
        btn_horizontal = QRadioButton("横方向", self)
        btn_horizontal.setChecked(True)
        self.direction_group.addButton(btn_horizontal, 0)
        hbox_direction.addWidget(btn_horizontal)

        btn_vertical = QRadioButton("縦方向", self)
        self.direction_group.addButton(btn_vertical, 1)
        hbox_direction.addWidget(btn_vertical)

        layout.addLayout(hbox_direction)

        # ファイル選択ボタン
        self.btn_select = QPushButton('ファイルを選択', self)
        self.btn_select.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.btn_select)

        # プレビュー表示用ラベル
        self.preview_label = QLabel('プレビュー表示', self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        # 決定ボタン
        self.btn_save = QPushButton('決定して画像を保存', self)
        self.btn_save.clicked.connect(self.save_image)
        self.btn_save.setEnabled(False)  # 最初は無効
        layout.addWidget(self.btn_save)

        # ドラッグアンドドロップ機能を有効化
        self.setAcceptDrops(True)

        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.image_paths = [file_path for file_path in files if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'))]
        if len(self.image_paths) > 1:
            self.merge_images()
        else:
            QMessageBox.warning(self, "エラー", "複数枚の画像をドラッグ＆ドロップしてください。")

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "画像ファイルを選択", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)")
        self.image_paths = files
        if len(self.image_paths) > 1:
            self.merge_images()
        else:
            QMessageBox.warning(self, "エラー", "複数枚の画像を選択してください。")

    def merge_images(self):
        # 連結方向の取得
        direction = self.direction_group.checkedId()

        # 画像を読み込む
        images = [Image.open(img_path) for img_path in self.image_paths]
        
        # 最大の幅と高さを取得
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)

        # 連結する方向に応じてサイズを計算
        if direction == 0:  # 横方向に連結
            total_width = sum(img.width for img in images)
            self.merged_image = Image.new('RGB', (total_width, max_height), color=(255, 255, 255))
            x_offset = 0
            for img in images:
                padded_img = ImageOps.pad(img, (img.width, max_height), color=(255, 255, 255))
                self.merged_image.paste(padded_img, (x_offset, 0))
                x_offset += img.width
        else:  # 縦方向に連結
            total_height = sum(img.height for img in images)
            self.merged_image = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))
            y_offset = 0
            for img in images:
                padded_img = ImageOps.pad(img, (max_width, img.height), color=(255, 255, 255))
                self.merged_image.paste(padded_img, (0, y_offset))
                y_offset += img.height

        # 画像をプレビュー表示
        self.show_preview()
        self.btn_save.setEnabled(True)  # 決定ボタンを有効化

    def show_preview(self):
        # PillowのImageからQtのQImageに変換
        qimage = self.pil_to_qimage(self.merged_image)
        pixmap = QPixmap.fromImage(qimage)
        self.preview_label.setPixmap(pixmap.scaled(400, 300, Qt.KeepAspectRatio))

    def pil_to_qimage(self, pil_image):
        """PillowのImageをQtのQImageに変換"""
        pil_image = pil_image.convert('RGB')
        data = pil_image.tobytes("raw", "RGB")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGB888)
        return qimage

    def save_image(self):
        if self.merged_image:
            # 保存先のパスを決定（最初の画像のフォルダに保存）
            save_dir = os.path.dirname(self.image_paths[0])
            save_filename = os.path.join(save_dir, f"merged_image_{len(self.image_paths)}.jpg")
            self.merged_image.save(save_filename)
            QMessageBox.information(self, "保存完了", f"画像を保存しました: {save_filename}")
        else:
            QMessageBox.warning(self, "エラー", "結合された画像がありません。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageMergerApp()
    ex.show()
    sys.exit(app.exec_())
