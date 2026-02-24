import sys
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QMimeData, QUrl, QEvent
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QScrollArea, QGridLayout, QLabel)
from PyQt6.QtGui import QPixmap, QImage, QKeySequence, QShortcut, QPainter, QPen


class ImageCard(QLabel):
    def __init__(self, emotion_image_path, chatimg_dir: Path, char_name: str, width, scale=0.5, parent=None):
        super().__init__(parent)
        self.emotion_path = Path(emotion_image_path).resolve()
        self.chatimg_dir = Path(chatimg_dir).resolve()
        self.char_name = char_name
        self.scale = float(scale)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0; 
                border: 2px solid #dddddd;
                border-radius: 5px;
            }
            QLabel:hover {
                border: 2px solid #999999;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_display_size(scale)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def update_display_size(self, scale: float):
        pad_x = 0
        base_w, base_h = 370, 185

        s = float(scale)
        img_w = max(1, int(base_w * s))
        img_h = max(1, int(base_h * s))

        self.setFixedSize(img_w + 2 * pad_x, img_h)
        self.load_thumbnail(img_w, img_h, pad_x)

    def load_thumbnail(self, img_w, img_h, pad_x):
        pix = QPixmap(str(self.emotion_path))
        if pix.isNull():
            return

        thumb = pix.scaled(
            img_w, img_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        W, H = self.width(), self.height()

        canvas = QPixmap(W, H)
        canvas.fill(Qt.GlobalColor.transparent)

        painter = QPainter(canvas)

        x = (W - thumb.width()) // 2
        y = (H - thumb.height()) // 2
        painter.drawPixmap(x, y, thumb)

        pen = QPen(Qt.GlobalColor.lightGray)
        pen.setWidth(2)
        painter.setPen(pen)
        x_mid = W // 2
        painter.drawLine(x_mid, 0, x_mid, H)

        painter.end()
        self.setPixmap(canvas)

    def mousePressEvent(self, event):
        x = int(event.position().x())
        side = "right" if x >= (self.width() // 2) else "left"
        self.copy_variant_to_clipboard(side)
        event.accept()
        return

    def copy_variant_to_clipboard(self, side: str):
        stem = self.emotion_path.stem
        suffix = self.emotion_path.suffix

        target = (self.chatimg_dir / self.char_name / f"{stem}_{side}{suffix}").resolve()

        if not target.exists():
            self.window().statusBar().showMessage(f"대상 파일이 없음: {target.name}", 2500)
            return

        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(target))])
        clipboard.setMimeData(mime_data)

        self.window().reset_selections()
        self.setStyleSheet("""
            QLabel {
                background-color: #e6f7ff;
                border: 3px solid #1890ff;
                border-radius: 5px;
            }
        """)
        self.window().statusBar().showMessage(
            f"파일 복사 완료! ({side}) (Ctrl+V): {target.name}", 2000
        )




class ViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatImg Viewer")
        self.resize(1400, 800)
        self.emotion_dir = Path("./emotion")
        self.chatimg_dir = Path("./chatimg")
        self.root_dir = self.emotion_dir

        self.scale = 1.0
        self.min_scale = 0.25
        self.max_scale = 3.0
        self.zoom_step = 0.1

        self.init_ui()
        self.load_character_list()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        left_layout = QVBoxLayout()
        lbl_list = QLabel("📂 캐릭터 목록")
        lbl_list.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(lbl_list)

        self.char_list_widget = QListWidget()
        self.char_list_widget.setFixedWidth(200)
        self.char_list_widget.itemClicked.connect(self.on_character_click)
        left_layout.addWidget(self.char_list_widget)

        right_layout = QVBoxLayout()
        self.lbl_info = QLabel("캐릭터를 선택해주세요.")
        self.lbl_info.setStyleSheet("font-size: 14px; margin-bottom: 5px;")
        right_layout.addWidget(self.lbl_info)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        self.scroll.viewport().installEventFilter(self)

        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_layout.setSpacing(15)

        self.scroll.setWidget(self.scroll_content)
        right_layout.addWidget(self.scroll)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.statusBar().showMessage(
            f"표시: {self.emotion_dir.resolve()} | 복사: {self.chatimg_dir.resolve()}"
        )

    def eventFilter(self, source, event):
        if source == self.scroll.viewport() and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
                return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_in()
            elif event.key() == Qt.Key.Key_Minus:
                self.zoom_out()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def zoom_in(self):
        if self.scale < self.max_scale:
            self.scale = min(self.max_scale, self.scale + self.zoom_step)
            self.apply_zoom()

    def zoom_out(self):
        if self.scale > self.min_scale:
            self.scale = max(self.min_scale, self.scale - self.zoom_step)
            self.apply_zoom()

    def apply_zoom(self):
        self.lbl_info.setText(f"🔍 Scale: {int(self.scale * 100)}%")
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, ImageCard):
                widget.update_display_size(self.scale)

    def load_character_list(self):
        self.char_list_widget.clear()
        if not self.root_dir.exists():
            self.lbl_info.setText(f"오류: {self.root_dir} 폴더가 없습니다.")
            return

        chars = sorted([p.name for p in self.root_dir.iterdir() if p.is_dir()])
        if not chars:
            self.lbl_info.setText("표시할 캐릭터 폴더가 없습니다.")
            return
        self.char_list_widget.addItems(chars)

    def on_character_click(self, item):
        char_name = item.text()
        char_path = self.root_dir / char_name
        self.load_images(char_path)

    def load_images(self, folder_path):
        self.clear_grid()
        valid_ext = {'.png', '.jpg', '.jpeg'}
        images = sorted([p for p in folder_path.iterdir() if p.suffix.lower() in valid_ext], key=lambda x: x.name)

        self.lbl_info.setText(f"📂 {folder_path.name} - {len(images)}개의 이미지")

        cols = 3
        row, col = 0, 0
        for img_path in images:
            card = ImageCard(
                img_path,
                self.chatimg_dir,
                folder_path.name,
                0,
                scale=self.scale,
            )

            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def clear_grid(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def reset_selections(self):
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setStyleSheet("""
                    QLabel {
                        background-color: #f0f0f0; 
                        border: 2px solid #dddddd;
                        border-radius: 5px;
                    }
                    QLabel:hover {
                        border: 2px solid #999999;
                    }
                """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    viewer = ViewerWindow()
    viewer.show()
    sys.exit(app.exec())