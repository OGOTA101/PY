import sys
import os
import traceback
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QFileDialog, QLineEdit, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt, QSize, QTimer, QMimeData, QPoint
from PyQt5.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QPainter, QPen, QImage
from PIL import Image

# Pillow のバージョンに応じたリサイズフィルタを設定
try:
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    resample_filter = Image.LANCZOS

# -------------------------------------------------------
# PIL Image を QPixmap に変換するヘルパー関数
# ※RGBA形式に変換し、QImage経由でQPixmapを作成する
# -------------------------------------------------------
def pil2pixmap(im):
    im = im.convert("RGBA")
    data = im.tobytes("raw", "RGBA")
    qimage = QImage(data, im.size[0], im.size[1], QImage.Format_RGBA8888)
    pixmap = QPixmap.fromImage(qimage)
    return pixmap

# -------------------------------------------------------
# 各フレーム用ウィジェット
# ・サムネイル画像（固定サイズ100x100）を表示
# ・下部にフレーム数指定用スピンボックス（デフォルト60＝1秒相当）
# ・削除ボタン「×」
# -------------------------------------------------------
class FrameItemWidget(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        
        # 縦方向レイアウトの設定
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # サムネイル画像表示用ラベル（固定サイズ100x100）
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(100, 100)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        pix = QPixmap(file_path)
        if not pix.isNull():
            # アスペクト比を維持してリサイズ
            pix = pix.scaled(self.thumb_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(pix)
        layout.addWidget(self.thumb_label)
        
        # 下部：スピンボックスと削除ボタン
        h_layout = QHBoxLayout()
        self.spin_box = QSpinBox()
        self.spin_box.setRange(1, 10000)  # フレーム数の範囲
        self.spin_box.setValue(60)        # デフォルトは60（1秒相当、60fps換算）
        h_layout.addWidget(self.spin_box)
        
        self.remove_button = QPushButton("×")
        self.remove_button.setFixedSize(20, 20)
        h_layout.addWidget(self.remove_button)
        layout.addLayout(h_layout)
        
        self.setLayout(layout)

# -------------------------------------------------------
# QListWidget のサブクラス
# ・アイコンモードでグリッド表示（横並び、折り返し）
# ・内部ドラッグ＆ドロップで並べ替え可能
# ・マウスイベントをオーバーライドし、クリックだけの場合はドラッグを発生させない
# -------------------------------------------------------
class FrameListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(True)
        self.setGridSize(QSize(110, 150))
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDropIndicatorShown(True)
        self._start_pos = None  # マウス押下時の位置を記憶
        
    def mousePressEvent(self, event):
        self._start_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            distance = (event.pos() - self._start_pos).manhattanLength()
            # 一定距離以上移動しない場合はドラッグと判定しない
            if distance >= QApplication.startDragDistance():
                super().mouseMoveEvent(event)
            else:
                event.ignore()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._start_pos = None
        
    def dropEvent(self, event: QDropEvent):
        super().dropEvent(event)
        self.doItemsLayout()  # 並べ替え後に再レイアウト
        self.repaint()

# -------------------------------------------------------
# メインウィジェット：GIF 作成ツール
# ・画像追加、削除、並べ替え、出力ファイル名入力、書出し、プレビュー機能を提供
# -------------------------------------------------------
class GIFCreatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GIF画像作成ツール")
        self.setGeometry(100, 100, 800, 700)
        self.max_frames = 120  # 最大登録枚数
        self.preview_frames = []      # プレビュー用の QPixmap リスト
        self.preview_durations = []   # 各フレームの表示時間（ミリ秒）
        self.preview_index = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_preview_frame)
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 画像一覧表示用リストウィジェット（グリッド表示）
        self.listWidget = FrameListWidget(self)
        main_layout.addWidget(self.listWidget)
        
        # 下部：出力ファイル名入力欄、書出しボタン、プレビューボタン
        bottom_layout = QHBoxLayout()
        self.name_line = QLineEdit()
        self.name_line.setPlaceholderText("出力ファイル名")
        bottom_layout.addWidget(self.name_line)
        self.export_button = QPushButton("書出し")
        self.export_button.clicked.connect(self.export_gif)
        bottom_layout.addWidget(self.export_button)
        self.preview_button = QPushButton("プレビュー")
        self.preview_button.clicked.connect(self.preview_gif)
        bottom_layout.addWidget(self.preview_button)
        main_layout.addLayout(bottom_layout)
        
        # GIF プレビュー表示用ラベル（GIF風再生領域）
        self.gif_preview_label = QLabel("プレビュー領域", self)
        self.gif_preview_label.setAlignment(Qt.AlignCenter)
        self.gif_preview_label.setFixedHeight(200)
        main_layout.addWidget(self.gif_preview_label)
        
        # 画像追加ボタン（ファイル選択）
        self.add_button = QPushButton("画像を追加")
        self.add_button.clicked.connect(self.open_file_dialog)
        main_layout.addWidget(self.add_button)
        
        self.setLayout(main_layout)
        self.setAcceptDrops(True)
        
    # --- ドラッグ＆ドロップによる画像追加 ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_images(files)
            event.acceptProposedAction()
            
    # --- ファイル選択による画像追加 ---
    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "画像ファイルを選択", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        self.add_images(files)
        
    def add_images(self, files):
        # 対応拡張子のみを抽出
        valid_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not valid_files:
            return
        current_count = self.listWidget.count()
        for f in valid_files:
            if current_count >= self.max_frames:
                break
            self.add_frame_item(f)
            current_count += 1
        # 初回追加の場合、出力ファイル名の初期値を1枚目の画像名（拡張子除く）に設定
        if self.listWidget.count() > 0 and not self.name_line.text():
            first_item = self.listWidget.item(0)
            widget = self.listWidget.itemWidget(first_item)
            base = os.path.splitext(os.path.basename(widget.file_path))[0]
            self.name_line.setText(base)
            
    def add_frame_item(self, file_path):
        # QListWidgetItem とカスタムウィジェットの組み合わせでアイテムを追加
        item = QListWidgetItem()
        widget = FrameItemWidget(file_path)
        # 削除ボタン押下時、該当アイテムを削除し再レイアウト
        widget.remove_button.clicked.connect(lambda: self.remove_frame_item(item))
        item.setSizeHint(widget.sizeHint())
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, widget)
        
    def remove_frame_item(self, item):
        row = self.listWidget.row(item)
        self.listWidget.takeItem(row)
        self.listWidget.doItemsLayout()
        self.listWidget.repaint()
        
    # --- GIF 書出し ---
    def export_gif(self):
        count = self.listWidget.count()
        if count == 0:
            QMessageBox.information(self, "情報", "画像が登録されていません。")
            return
        # 1枚目の画像サイズを基準とする
        first_item = self.listWidget.item(0)
        widget = self.listWidget.itemWidget(first_item)
        try:
            base_image = Image.open(widget.file_path)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"1枚目の画像の読み込みに失敗しました: {str(e)}")
            return
        target_size = base_image.size
        
        # 画像サイズの不一致があれば警告（処理は続行）
        size_mismatch = False
        for i in range(count):
            item = self.listWidget.item(i)
            widget = self.listWidget.itemWidget(item)
            try:
                img = Image.open(widget.file_path)
                if img.size != target_size:
                    size_mismatch = True
                    break
            except Exception:
                continue
        if size_mismatch:
            QMessageBox.warning(
                self, "警告",
                "登録されている画像のサイズが異なります。\nすべて1枚目の画像サイズにリサイズしてGIFを作成します。"
            )
        frames = []
        durations = []
        # 各画像を読み込み、必要ならリサイズしてフレームリストに追加
        for i in range(count):
            item = self.listWidget.item(i)
            widget = self.listWidget.itemWidget(item)
            try:
                img = Image.open(widget.file_path)
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"画像の読み込みに失敗しました: {str(e)}")
                return
            if img.size != target_size:
                img = img.resize(target_size, resample_filter)
            frames.append(img.convert("RGB"))
            spin_value = widget.spin_box.value()
            duration_ms = int((spin_value / 60.0) * 1000)  # 60fps換算でミリ秒に変換
            durations.append(duration_ms)
        
        # 出力ファイル名は、一番最初の画像のフォルダに保存する
        folder = os.path.dirname(widget.file_path)
        out_name = self.name_line.text().strip()
        if not out_name:
            out_name = os.path.splitext(os.path.basename(widget.file_path))[0]
        if not out_name.lower().endswith(".gif"):
            out_name += ".gif"
        out_path = os.path.join(folder, out_name)
        try:
            frames[0].save(
                out_path, save_all=True, append_images=frames[1:], duration=durations, loop=0
            )
            QMessageBox.information(self, "成功", f"GIF画像を書出しました: {out_path}")
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"GIF書出しに失敗しました: {str(e)}")
            
    # --- GIF プレビュー ---
    def preview_gif(self):
        """
        プレビューボタン押下時の処理。
        ・既にプレビュー中の場合は停止（タイマーを停止してプレビュー領域にテキストを表示）。
        ・プレビュー中でなければ、登録画像からGIF用フレームと表示時間を生成し、
          タイマーでループ再生を開始する。
        """
        # すでにタイマーが動作中なら停止し、プレビュー領域に「プレビュー領域」と表示して終了
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            self.gif_preview_label.setText("プレビュー領域")
            return
        
        count = self.listWidget.count()
        if count == 0:
            QMessageBox.information(self, "情報", "画像が登録されていません。")
            return
        # 基準サイズは1枚目の画像サイズ
        first_item = self.listWidget.item(0)
        widget = self.listWidget.itemWidget(first_item)
        try:
            base_image = Image.open(widget.file_path)
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"1枚目の画像の読み込みに失敗しました: {str(e)}")
            return
        target_size = base_image.size
        
        self.preview_frames = []
        self.preview_durations = []
        # 登録画像からGIF用のフレームと表示時間のリストを作成
        for i in range(count):
            item = self.listWidget.item(i)
            widget = self.listWidget.itemWidget(item)
            try:
                img = Image.open(widget.file_path)
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"画像の読み込みに失敗しました: {str(e)}")
                return
            if img.size != target_size:
                img = img.resize(target_size, resample_filter)
            # PIL Image を QPixmap に変換（ヘルパー関数pil2pixmapを使用）
            pix = pil2pixmap(img)
            self.preview_frames.append(pix)
            spin_value = widget.spin_box.value()
            duration_ms = int((spin_value / 60.0) * 1000)
            self.preview_durations.append(duration_ms)
        if not self.preview_frames:
            return
        
        # 初回フレームを表示
        self.preview_index = 0
        self.gif_preview_label.setPixmap(self.preview_frames[0].scaled(
            self.gif_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        # タイマー開始
        self.animation_timer.start(self.preview_durations[0])
        
    def update_preview_frame(self):
        """タイマー更新時に次のフレームを表示し、タイマーを再設定する。"""
        if not self.preview_frames:
            return
        self.preview_index = (self.preview_index + 1) % len(self.preview_frames)
        pix = self.preview_frames[self.preview_index].scaled(
            self.gif_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.gif_preview_label.setPixmap(pix)
        self.animation_timer.start(self.preview_durations[self.preview_index])

# -------------------------------------------------------
# 未処理例外発生時にエラーダイアログを表示するグローバル例外ハンドラ
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

# -------------------------------------------------------
# アプリケーションエントリポイント
# -------------------------------------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GIFCreatorApp()
    ex.show()
    sys.exit(app.exec_())
