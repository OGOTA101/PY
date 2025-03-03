import sys
import os
import traceback
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, QVBoxLayout, 
    QHBoxLayout, QSpinBox, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QPainter, QPen
from PIL import Image

class ImagePreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.original_pix = None
        self.h_splits = 1
        self.v_splits = 1

    def setImage(self, image_path):
        self.original_pix = QPixmap(image_path)
        self.updatePixmap()
        
    def updatePixmap(self):
        if self.original_pix:
            # ウィンドウサイズに合わせてアスペクト比を維持しながらスケール
            scaled_pix = self.original_pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled_pix)
            self.update()

    def updateSplits(self, h_splits, v_splits):
        self.h_splits = h_splits
        self.v_splits = v_splits
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updatePixmap()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pixmap() is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.red, 2)
        painter.setPen(pen)

        # 描画されている画像のサイズ（scaledContentsの場合はウィジェット全体ではなく、画像自体のサイズ）
        widget_width = self.width()
        widget_height = self.height()
        scaled_pix = self.pixmap()
        pix_width = scaled_pix.width()
        pix_height = scaled_pix.height()
        # 中央に描画されるのでオフセットを計算
        x_offset = (widget_width - pix_width) / 2
        y_offset = (widget_height - pix_height) / 2

        # 横分割ガイド
        if self.h_splits > 1:
            step_x = pix_width / self.h_splits
            for i in range(1, self.h_splits):
                x = x_offset + i * step_x
                painter.drawLine(int(x), int(y_offset), int(x), int(y_offset + pix_height))
        # 縦分割ガイド
        if self.v_splits > 1:
            step_y = pix_height / self.v_splits
            for j in range(1, self.v_splits):
                y = y_offset + j * step_y
                painter.drawLine(int(x_offset), int(y), int(x_offset + pix_width), int(y))
        painter.end()

class ImageSplitterApp(QWidget):
    def __init__(self):
        super().__init__()
        self.file_paths = []  # 読み込んだ画像ファイルのリスト
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Image Splitter with Drag and Drop")
        self.setGeometry(100, 100, 600, 700)
        layout = QVBoxLayout()

        # プレビューウィジェット（ウィンドウサイズに合わせて拡縮）
        self.preview = ImagePreviewWidget(self)
        # 最小サイズだけ指定（レイアウトで拡大可能）
        self.preview.setMinimumSize(400, 300)
        layout.addWidget(self.preview)

        # 読み込み画像数表示ラベル
        self.count_label = QLabel("読み込み画像数: 0", self)
        self.count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.count_label)

        # 説明ラベル
        self.label = QLabel('ドラッグ＆ドロップまたはファイル選択で画像を追加してください。', self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # 横方向の分割数（1～999、1の場合は分割なし）
        hbox_horizontal = QHBoxLayout()
        hbox_horizontal.addWidget(QLabel("横方向の分割数:", self))
        self.h_spin = QSpinBox(self)
        self.h_spin.setRange(1, 999)
        self.h_spin.setValue(1)
        hbox_horizontal.addWidget(self.h_spin)
        layout.addLayout(hbox_horizontal)

        # 縦方向の分割数
        hbox_vertical = QHBoxLayout()
        hbox_vertical.addWidget(QLabel("縦方向の分割数:", self))
        self.v_spin = QSpinBox(self)
        self.v_spin.setRange(1, 999)
        self.v_spin.setValue(1)
        hbox_vertical.addWidget(self.v_spin)
        layout.addLayout(hbox_vertical)

        # カスタム接尾辞入力
        hbox_suffix = QHBoxLayout()
        hbox_suffix.addWidget(QLabel("カスタム接尾辞:", self))
        self.suffix_line = QLineEdit(self)
        hbox_suffix.addWidget(self.suffix_line)
        layout.addLayout(hbox_suffix)

        # ファイル選択ボタン
        self.btn_select = QPushButton('ファイルを選択', self)
        self.btn_select.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.btn_select)

        # 分割実行ボタン
        self.btn_split = QPushButton('画像を分割', self)
        self.btn_split.clicked.connect(self.execute_split)
        layout.addWidget(self.btn_split)

        # ステータスラベル（分割成功メッセージ等）
        self.status_label = QLabel("", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # 分割数変更時にプレビューのガイド線を更新
        self.h_spin.valueChanged.connect(self.update_preview_splits)
        self.v_spin.valueChanged.connect(self.update_preview_splits)

        # ドラッグ＆ドロップ有効化
        self.setAcceptDrops(True)
        self.setLayout(layout)

    def update_preview_splits(self):
        h_val = self.h_spin.value()
        v_val = self.v_spin.value()
        self.preview.updateSplits(h_val, v_val)

    def updateCountLabel(self):
        count = len(self.file_paths)
        self.count_label.setText(f"読み込み画像数: {count}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  # ドラッグされたファイルを受け入れる
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        valid_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if valid_files:
            self.file_paths = valid_files  # 複数の場合はすべて保持
            self.updateCountLabel()
            # 複数ファイルの場合は最初の画像のみプレビュー表示
            self.preview.setImage(self.file_paths[0])
            # 新規読み込み時はステータスメッセージをクリア
            self.status_label.setText("")
            print(f"{len(self.file_paths)} 個の画像を読み込みました。")
        else:
            print("対応していないファイル形式です。")

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "画像ファイルを選択", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if files:
            self.file_paths = files
            self.updateCountLabel()
            self.preview.setImage(self.file_paths[0])
            self.status_label.setText("")
            print(f"{len(self.file_paths)} 個の画像を読み込みました。")

    def execute_split(self):
        if not self.file_paths:
            QMessageBox.information(self, "情報", "画像が読み込まれていません。")
            return

        # 分割数が両方とも1の場合はエラー表示
        if self.h_spin.value() == 1 and self.v_spin.value() == 1:
            QMessageBox.warning(self, "警告", "分割数を2以上にしてください。")
            return

        # 複数画像の場合は確認ダイアログを表示
        if len(self.file_paths) > 1:
            reply = QMessageBox.question(
                self, "確認", "現在の設定ですべての画像分割を行いますか？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # 各画像に対して分割処理を実行
        for file_path in self.file_paths:
            self.split_image(file_path)
        # 分割成功メッセージを表示（数秒後に自動クリア）
        self.status_label.setText("分割成功！")
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

    def split_image(self, file_path):
        h_splits = self.h_spin.value()
        v_splits = self.v_spin.value()

        # PILを使用して画像を読み込み、画像サイズで等分割（余白は考慮しない）
        img = Image.open(file_path)
        width, height = img.size

        # 画像のディレクトリとファイル名取得
        img_dir = os.path.dirname(file_path)
        img_name, img_ext = os.path.splitext(os.path.basename(file_path))

        h_step = width // h_splits
        v_step = height // v_splits

        custom_suffix = self.suffix_line.text().strip()

        counter = 1
        for v in range(v_splits):
            for h in range(h_splits):
                left = h * h_step
                upper = v * v_step
                # 最終行・最終列は余りを含める
                right = (h + 1) * h_step if h != h_splits - 1 else width
                lower = (v + 1) * v_step if v != v_splits - 1 else height

                cropped_img = img.crop((left, upper, right, lower))
                suffix_part = f"{custom_suffix}" if custom_suffix else ""
                new_filename = f"{img_name}_{suffix_part}{counter}{img_ext}"
                save_path = os.path.join(img_dir, new_filename)
                cropped_img.save(save_path)
                print(f"保存: {save_path}")
                counter += 1

        print(f"画像 {file_path} を {h_splits} x {v_splits} に分割して保存しました！")

# -------------------------------------------------------
# グローバル例外ハンドラ
# 未処理例外が発生した場合にエラーダイアログを表示し、ウィンドウがすぐ閉じないようにする
# -------------------------------------------------------
def excepthook(exc_type, exc_value, exc_tb):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Unhandled Exception")
    msg_box.setText("予期せぬエラーが発生しました。")
    msg_box.setDetailedText(error_msg)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.exec_()

sys.excepthook = excepthook

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageSplitterApp()
    ex.show()
    sys.exit(app.exec_())
