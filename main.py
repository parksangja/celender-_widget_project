import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtWidgets import QListWidgetItem
from calendar_engine import CalendarEngine
from PyQt6.QtCore import Qt


class CalendarWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.engine = CalendarEngine()

        #
        try:
            self.engine.add_event("회의", "2026-04-10", "15:00", 60)
            self.engine.add_event("운동", "2026-04-10", "18:00", 60)
        except:
            pass
        #

        self.init_ui()

    def init_ui(self): #프로그램 실행 시 기본 ui
        from PyQt6.QtWidgets import QVBoxLayout, QCalendarWidget
        from PyQt6.QtWidgets import QListWidget
        # 기본 사이즈 지정
        self.setMinimumSize(250, 200)
        self.resize(300, 300)

        self.setWindowFlags(
            Qt.WindowType.Tool #위젯을 윈도우 설정 상 Tool로 지정
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

        layout = QVBoxLayout()

        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.on_date_clicked)

        self.event_list = QListWidget()

        layout.addWidget(self.calendar)
        layout.addWidget(self.event_list)
        
        self.setLayout(layout)

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

    def on_date_clicked(self, date):
        date_str = date.toString("yyyy-MM-dd")

        events = self.engine.list_events(date_str)

        self.event_list.clear()

        for event in events:
            text = f"{event['time']} | {event['title']}"
            item = QListWidgetItem(text)

        # 🔥 id 저장 (나중에 삭제/수정용)
            item.setData(1, event["id"])

            self.event_list.addItem(item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = CalendarWidget()
    sys.exit(app.exec())
