import sys
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QMimeData, QUrl, QEvent
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QScrollArea, QGridLayout, QLabel)
from PyQt6.QtGui import QPixmap, QImage, QKeySequence, QShortcut


class ImageCard(QLabel):
    def __init__(self, image_path, width, parent=None):
        super().__init__(parent)
        self.image_path = str(Path(image_path).resolve())
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
        self.update_display_size(width)

    def update_display_size(self, width):
        self.setFixedSize(width, int(width * 0.25))
        self.load_thumbnail()

    def load_thumbnail(self):
        pix = QPixmap(self.image_path)
        if not pix.isNull():
            scaled = pix.scaled(
                self.width(),
                self.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.copy_to_clipboard()

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        url = QUrl.fromLocalFile(self.image_path)
        mime_data.setUrls([url])
        clipboard.setMimeData(mime_data)

        self.window().reset_selections()
        self.setStyleSheet("""
            QLabel {
                background-color: #e6f7ff;
                border: 3px solid #1890ff;
                border-radius: 5px;
            }
        """)

        filename = os.path.basename(self.image_path)
        self.window().statusBar().showMessage(f"파일 복사 완료! (Ctrl+V): {filename}", 2000)


class ViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatImg Viewer")
        self.resize(1400, 800)
        self.root_dir = Path("./chatimg")

        self.current_img_width = 380
        self.min_width = 100
        self.max_width = 1200
        self.zoom_step = 40

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

        self.statusBar().showMessage(f"저장 경로: {self.root_dir.resolve()}")

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
        if self.current_img_width < self.max_width:
            self.current_img_width += self.zoom_step
            self.apply_zoom()

    def zoom_out(self):
        if self.current_img_width > self.min_width:
            self.current_img_width -= self.zoom_step
            self.apply_zoom()

    def apply_zoom(self):
        self.lbl_info.setText(f"🔍 줌 레벨: {self.current_img_width}px")
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, ImageCard):
                widget.update_display_size(self.current_img_width)

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
            card = ImageCard(img_path, self.current_img_width)
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