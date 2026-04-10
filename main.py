import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt


class CalendarWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        # 창 크기
        self.setMinimumSize(250, 200)
        self.resize(300, 300)

        # 항상 위 + 위젯 느낌
        self.setWindowFlags(
            Qt.WindowType.Tool
        )

        # 스타일 (간단한 다크 UI)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 10px;
                color: white;
            }
        """)

        self.setWindowTitle("Mini Calendar Widget")

        self.show()

    # 드래그 이동
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = CalendarWidget()
    sys.exit(app.exec())
