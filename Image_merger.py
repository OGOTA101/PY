import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PIL import Image, ImageOps

class ImageMergerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.image_paths = []

    def initUI(self):
        self.setWindowTitle("Image Merger with Drag and Drop")
        self.setGeometry(100, 100, 400, 300)

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

        # ドラッグアンドドロップ機能を有効化
        self.setAcceptDrops(True)

        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  # ドラッグされたファイルを許可
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.image_paths = [file_path for file_path in files if file_path.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if len(self.image_paths) > 1:
            self.merge_images()
        else:
            print("複数枚の画像をドラッグ＆ドロップしてください。")

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "画像ファイルを選択", "", "Image Files (*.png *.jpg *.jpeg)")
        self.image_paths = files
        if len(self.image_paths) > 1:
            self.merge_images()
        else:
            print("複数枚の画像を選択してください。")

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
            merged_image = Image.new('RGB', (total_width, max_height), color=(255, 255, 255))
            x_offset = 0
            for img in images:
                # 画像の高さが最大高さと異なる場合、白い余白でパディング
                padded_img = ImageOps.pad(img, (img.width, max_height), color=(255, 255, 255))
                merged_image.paste(padded_img, (x_offset, 0))
                x_offset += img.width
        else:  # 縦方向に連結
            total_height = sum(img.height for img in images)
            merged_image = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))
            y_offset = 0
            for img in images:
                # 画像の幅が最大幅と異なる場合、白い余白でパディング
                padded_img = ImageOps.pad(img, (max_width, img.height), color=(255, 255, 255))
                merged_image.paste(padded_img, (0, y_offset))
                y_offset += img.height

        # 保存先のパスを決定（最初の画像のフォルダに保存）
        save_dir = os.path.dirname(self.image_paths[0])
        save_filename = os.path.join(save_dir, f"merged_image_{len(self.image_paths)}.jpg")
        merged_image.save(save_filename)
        
        print(f"画像を連結して保存しました: {save_filename}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageMergerApp()
    ex.show()
    sys.exit(app.exec_())
