##UI파일

import sys

from PyQt6.QtCore import QDate, Qt, QTime
from PyQt6.QtGui import QBrush, QColor, QTextCharFormat
from PyQt6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QDateEdit,
    QDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

#UI에 표현하기 위해 만든거 다 가져오기
from ai_parser_gpt import parse
from calendar_engine import CalendarEngine
from executor import execute
from korean_calendar_utils import get_korean_holidays


class ExpandingCommandInput(QTextEdit): #확대 축소 처리용
    def __init__(self):
        super().__init__()

        self.min_input_height = 48
        self.max_input_height = 140

        self.setObjectName("commandInput")
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setMinimumHeight(self.min_input_height)
        self.setMaximumHeight(self.max_input_height)
        self.setFixedHeight(self.min_input_height)
        self.document().contentsChanged.connect(self.adjust_height)

    def adjust_height(self):
        document_height = int(self.document().size().height()) + 18
        next_height = max(self.min_input_height, min(document_height, self.max_input_height))
        self.setFixedHeight(next_height)


class ManualEventDialog(QDialog): #이벤트 직접추가 버튼 누르면 나오는 요소들
    def __init__(self, selected_date, parent=None):
        super().__init__(parent)

        self.setWindowTitle("일정 직접 추가")
        self.setModal(True)
        self.setMinimumWidth(360)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("제목")

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(selected_date)

        self.start_time_input = QTimeEdit()
        self.start_time_input.setDisplayFormat("HH:mm")
        self.start_time_input.setTime(QTime(9, 0))

        self.end_time_input = QTimeEdit()
        self.end_time_input.setDisplayFormat("HH:mm")
        self.end_time_input.setTime(QTime(10, 0))

        self.error_label = QLabel()
        self.error_label.setObjectName("dialogError")

        self.cancel_button = QPushButton("취소")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("저장")
        self.save_button.clicked.connect(self.accept)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(12)
        form_layout.addRow("제목", self.title_input)
        form_layout.addRow("날짜", self.date_input)
        form_layout.addRow("시작", self.start_time_input)
        form_layout.addRow("종료", self.end_time_input)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def event_data(self):
        title = self.title_input.text().strip()
        if not title:
            raise ValueError("제목을 입력해주세요")

        start_time = self.start_time_input.time()
        end_time = self.end_time_input.time()
        start_minutes = (start_time.hour() * 60) + start_time.minute()
        end_minutes = (end_time.hour() * 60) + end_time.minute()
        duration = end_minutes - start_minutes

        if duration <= 0:
            raise ValueError("종료 시간은 시작 시간보다 늦어야 합니다")

        return {
            "title": title,
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "time": start_time.toString("HH:mm"),
            "duration": duration,
        }

    def accept(self):
        try:
            self.event_data()
        except ValueError as err:
            self.error_label.setText(str(err))
            return

        super().accept()


class CalendarWidget(QWidget): #메인 UI 구현
    def __init__(self):
        super().__init__()

        self.engine = CalendarEngine()
        self.selected_date = QDate.currentDate()
        self.old_pos = None
        self.holiday_cache = {}

        self.init_ui()
        self.refresh_events()

    def init_ui(self): #초기 설정
        self.setWindowTitle("Mini Calendar Widget")
        self.setMinimumSize(900, 600)
        self.resize(960, 600)
        self.setWindowFlags(Qt.WindowType.Tool)

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        self.ai_panel = self._build_ai_panel()
        self.calendar_panel = self._build_calendar_panel()
        self.events_panel = self._build_events_panel()

        root_layout.addWidget(self.ai_panel, 3)
        root_layout.addWidget(self.calendar_panel, 4)
        root_layout.addWidget(self.events_panel, 2)

        self.setLayout(root_layout)
        self.setStyleSheet(self._style_sheet())
        self.show()

    def _build_ai_panel(self): #UI에 있는 3개 구역 중, 첫번째 구역인 AI입력 구역 붙이는 함수
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(280)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("AI 입력")
        title.setObjectName("sectionTitle")

        self.result_box = QTextEdit()
        self.result_box.setObjectName("resultBox")
        self.result_box.setReadOnly(True)
        self.result_box.setText("대기 중")

        input_area = QFrame()
        input_area.setObjectName("inputArea")
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.command_input = ExpandingCommandInput()
        self.command_input.setPlaceholderText("일정을 입력하세요")

        self.run_button = QPushButton("실행")
        self.run_button.clicked.connect(self.run_command)

        input_layout.addWidget(self.command_input)
        input_layout.addWidget(self.run_button)
        input_area.setLayout(input_layout)

        layout.addWidget(title)
        layout.addWidget(self.result_box, 1)
        layout.addWidget(input_area)

        panel.setLayout(layout)
        return panel

    def _build_calendar_panel(self): #2번째 구역, 캘린더 붙이는 함수
        panel = QFrame()
        panel.setObjectName("calendarPanel")
        panel.setMinimumWidth(380)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        self.month_label = QLabel()
        self.month_label.setObjectName("monthTitle")

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.clicked.connect(self.on_date_clicked)
        self.calendar.currentPageChanged.connect(self.on_page_changed)

        layout.addWidget(self.month_label)
        layout.addWidget(self.calendar, 1)

        panel.setLayout(layout)
        self.update_month_label()
        self.apply_holiday_styles()
        return panel

    def _build_events_panel(self): #3번째 구역, 이벤트 리스트 있는 구역 붙이는 함수
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(210)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.events_title = QLabel()
        self.events_title.setObjectName("sectionTitle")

        self.event_list = QListWidget()
        self.event_list.setObjectName("eventList")

        add_button_row = QHBoxLayout()
        add_button_row.addStretch(1)

        self.add_event_button = QPushButton("+")
        self.add_event_button.setObjectName("addEventButton")
        self.add_event_button.setToolTip("일정 직접 추가")
        self.add_event_button.setFixedSize(36, 36)
        self.add_event_button.clicked.connect(self.open_manual_event_dialog)

        add_button_row.addWidget(self.add_event_button)

        layout.addWidget(self.events_title)
        layout.addWidget(self.event_list, 1)
        layout.addLayout(add_button_row)

        panel.setLayout(layout)
        return panel

    def _style_sheet(self): #UI디자인
        return """
            QWidget {
                background-color: #101114;
                color: #F2F4F8;
                font-family: Malgun Gothic;
                font-size: 13px;
                letter-spacing: 0px;
            }

            QFrame#panel,
            QFrame#calendarPanel {
                background-color: #181A1F;
                border: 1px solid #2D313A;
                border-radius: 8px;
            }

            QLabel#sectionTitle {
                color: #F2F4F8;
                font-size: 17px;
                font-weight: 700;
            }

            QLabel#monthTitle {
                color: #DDE3EE;
                font-size: 18px;
                font-weight: 700;
            }

            QTextEdit#commandInput {
                background-color: #0F1115;
                border: 1px solid #3A414E;
                border-radius: 6px;
                padding: 10px 12px;
                selection-background-color: #3D7EFF;
            }

            QTextEdit#commandInput:focus {
                border-color: #5B8CFF;
            }

            QPushButton {
                background-color: #2F6FED;
                border: 0;
                border-radius: 6px;
                color: white;
                font-weight: 700;
                padding: 10px 12px;
            }

            QPushButton:hover {
                background-color: #3E7CFA;
            }

            QPushButton:pressed {
                background-color: #235BC6;
            }

            QPushButton#secondaryButton {
                background-color: #2A2F39;
                color: #DDE3EE;
            }

            QPushButton#secondaryButton:hover {
                background-color: #343B47;
            }

            QPushButton#addEventButton {
                background-color: #2F6FED;
                border-radius: 18px;
                font-size: 22px;
                font-weight: 700;
                padding: 0;
            }

            QPushButton#addEventButton:hover {
                background-color: #3E7CFA;
            }

            QTextEdit#resultBox,
            QListWidget#eventList {
                background-color: #0F1115;
                border: 1px solid #2D313A;
                border-radius: 6px;
                padding: 8px;
            }

            QLineEdit,
            QDateEdit,
            QTimeEdit {
                background-color: #0F1115;
                border: 1px solid #3A414E;
                border-radius: 6px;
                color: #F2F4F8;
                padding: 8px 10px;
                selection-background-color: #3D7EFF;
            }

            QLineEdit:focus,
            QDateEdit:focus,
            QTimeEdit:focus {
                border-color: #5B8CFF;
            }

            QLabel#dialogError {
                color: #FF8A8A;
            }

            QListWidget#eventList::item {
                border-bottom: 1px solid #242832;
                padding: 9px 4px;
            }

            QListWidget#eventList::item:selected {
                background-color: #243A66;
                color: #FFFFFF;
            }

            QCalendarWidget {
                background-color: #181A1F;
                color: #F2F4F8;
                border: 0;
            }

            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #181A1F;
            }

            QCalendarWidget QToolButton {
                background-color: #20242C;
                border: 1px solid #313846;
                border-radius: 5px;
                color: #F2F4F8;
                margin: 3px;
                padding: 6px;
            }

            QCalendarWidget QToolButton:hover {
                background-color: #29303B;
            }

            QCalendarWidget QMenu {
                background-color: #181A1F;
                border: 1px solid #313846;
                color: #F2F4F8;
            }

            QCalendarWidget QSpinBox {
                background-color: #0F1115;
                border: 1px solid #313846;
                border-radius: 4px;
                color: #F2F4F8;
                padding: 4px;
            }

            QCalendarWidget QAbstractItemView {
                background-color: #111318;
                border: 1px solid #2D313A;
                border-radius: 6px;
                color: #DDE3EE;
                gridline-color: #252A33;
                selection-background-color: #2F6FED;
                selection-color: #FFFFFF;
                outline: 0;
            }
        """

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def on_page_changed(self, year, month):
        self.update_month_label(year, month)
        self.apply_holiday_styles(year)

    def update_month_label(self, year=None, month=None):
        if year is None or month is None:
            year = self.calendar.yearShown()
            month = self.calendar.monthShown()

        self.month_label.setText(f"{year}년 {month}월")

    def holidays_for_year(self, year):
        if year not in self.holiday_cache:
            self.holiday_cache[year] = get_korean_holidays(year)

        return self.holiday_cache[year]

    def holidays_for_date(self, date_str):
        year = int(date_str[:4])
        return self.holidays_for_year(year).get(date_str, [])

    def apply_holiday_styles(self, year=None):
        if year is None:
            year = self.calendar.yearShown()

        holiday_format = QTextCharFormat()
        holiday_format.setForeground(QBrush(QColor("#FF8A8A")))
        holiday_format.setBackground(QBrush(QColor("#261A21")))
        holiday_format.setFontWeight(700)

        for target_year in [year - 1, year, year + 1]:
            for date_str in self.holidays_for_year(target_year):
                qdate = QDate.fromString(date_str, "yyyy-MM-dd")
                self.calendar.setDateTextFormat(qdate, holiday_format)

    def on_date_clicked(self, date):
        self.selected_date = date
        self.refresh_events()

    def run_command(self):
        text = self.command_input.toPlainText().strip()
        if not text:
            self.show_result("입력 없음")
            return

        try:
            command = parse(text)
            result = execute(command, self.engine)
            self.command_input.clear()
            self.apply_command_result(command, result)
        except Exception as err:
            self.show_result(f"실패: {err}")

    def apply_command_result(self, command, result):
        action = command.get("action")

        if action == "add":
            self.selected_date = QDate.fromString(result["date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            self.show_result(f"추가됨\n{result['time']} | {result['title']}")

        elif action == "add_period":
            self.selected_date = QDate.fromString(result["start_date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            self.show_result(f"기간 추가됨\n{result['title']}")

        elif action == "list":
            self.selected_date = QDate.fromString(command["date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            self.show_result(f"조회됨\n{len(result)}개 일정")

        elif action == "delete":
            self.show_result(f"삭제됨\n{len(result)}개 일정")

        self.refresh_events()

    def open_manual_event_dialog(self):
        dialog = ManualEventDialog(self.selected_date, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            data = dialog.event_data()
            result = self.engine.add_event(
                data["title"],
                data["date"],
                data["time"],
                data["duration"],
            )
        except Exception as err:
            self.show_result(f"실패: {err}")
            return

        self.selected_date = QDate.fromString(result["date"], "yyyy-MM-dd")
        self.calendar.setSelectedDate(self.selected_date)
        self.show_result(f"직접 추가됨\n{result['time']} | {result['title']}")
        self.refresh_events()

    def refresh_events(self):
        date_str = self.selected_date.toString("yyyy-MM-dd")
        events = self.engine.list_events(date_str)
        holidays = self.holidays_for_date(date_str)

        self.events_title.setText(self.event_title_text())
        self.event_list.clear()

        for holiday_name in holidays:
            item = QListWidgetItem(f"휴일 | {holiday_name}")
            item.setForeground(QBrush(QColor("#FF9B9B")))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.event_list.addItem(item)

        if not events and not holidays:
            item = QListWidgetItem("일정 없음")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.event_list.addItem(item)
            return

        for event in events:
            if event.get("type") == "period":
                if event.get("end_date"):
                    text = f"기간 | {event['title']} ({event['start_date']}~{event['end_date']})"
                else:
                    text = f"기간 | {event['title']} (무기한)"
            else:
                text = f"{event['time']} | {event['title']}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, event["id"])
            self.event_list.addItem(item)

    def event_title_text(self):
        today = QDate.currentDate()
        date_text = self.selected_date.toString("MM월 dd일")

        if self.selected_date == today:
            return "오늘 일정"

        return f"{date_text} 일정"

    def show_result(self, message):
        self.result_box.setText(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = CalendarWidget()
    sys.exit(app.exec())
