##UI파일

import sys

from PyQt6.QtCore import QDate, QRectF, QThread, Qt, QTime, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QTextCharFormat
from PyQt6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QDateEdit,
    QDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

#UI에 표현하기 위해 만든거 다 가져오기
from ai_parser_gpt import parse
from calendar_engine import DEFAULT_EVENT_COLOR, CalendarEngine
from executor import execute
from holiday_updater import get_korean_holidays, update_holiday_cache


EVENT_COLORS = [
    DEFAULT_EVENT_COLOR,
    "#2DBE78",
    "#F59F00",
    "#E03131",
    "#9C36B5",
    "#15AABF",
    "#7048E8",
]
HOLIDAY_COLOR = "#E03131"


class HolidayUpdateThread(QThread):
    updated = pyqtSignal(object)

    def __init__(self, years, parent=None):
        super().__init__(parent)
        self.years = years

    def run(self):
        result = update_holiday_cache(self.years)
        self.updated.emit(result)


class MarkerCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.marker_provider = None
        self.max_markers = 3

    def set_marker_provider(self, provider):
        self.marker_provider = provider

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)

        if self.marker_provider is None:
            return

        markers = self.marker_provider(date)
        if not markers:
            return

        visible_markers = markers[: self.max_markers]
        hidden_count = len(markers) - len(visible_markers)
        if hidden_count > 0:
            visible_markers[-1] = {
                "title": f"+{hidden_count + 1}",
                "color": "#6B7280",
                "continues_before": False,
                "continues_after": False,
                "show_title": True,
            }

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bar_height = 11
        gap = 2
        bottom_margin = 5
        total_height = (bar_height * len(visible_markers)) + (gap * (len(visible_markers) - 1))
        y = rect.bottom() - bottom_margin - total_height + 1

        for marker in visible_markers:
            continues_before = marker.get("continues_before", False)
            continues_after = marker.get("continues_after", False)
            left_margin = 2 if not continues_before else 0
            right_margin = 2 if not continues_after else 0
            x = rect.x() + left_margin
            width = max(8, rect.width() - left_margin - right_margin)
            bar_rect = QRectF(x, y, width, bar_height)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(marker.get("color", DEFAULT_EVENT_COLOR)))
            painter.drawRoundedRect(bar_rect, 3, 3)

            if marker.get("show_title", True):
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(
                    bar_rect.adjusted(4, 0, -3, 0),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    marker.get("title", ""),
                )

            y += bar_height + gap

        painter.restore()


class ColorPicker(QWidget):
    def __init__(self, selected_color=DEFAULT_EVENT_COLOR, parent=None):
        super().__init__(parent)
        self._selected_color = selected_color or DEFAULT_EVENT_COLOR
        self.buttons = []

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for color in EVENT_COLORS:
            button = QPushButton()
            button.setFixedSize(24, 24)
            button.setToolTip(color)
            button.clicked.connect(lambda _checked=False, value=color: self.set_color(value))
            self.buttons.append((button, color))
            layout.addWidget(button)

        layout.addStretch(1)
        self.setLayout(layout)
        self.refresh_buttons()

    def color(self):
        return self._selected_color

    def set_color(self, color):
        self._selected_color = color or DEFAULT_EVENT_COLOR
        self.refresh_buttons()

    def refresh_buttons(self):
        for button, color in self.buttons:
            border = "#FFFFFF" if color == self._selected_color else "#343B47"
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border: 2px solid {border};
                    border-radius: 12px;
                    padding: 0;
                }}
                """
            )


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

        self.period_checkbox = QCheckBox("기간 일정")
        self.period_checkbox.toggled.connect(self.update_mode_widgets)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setDate(selected_date)

        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.end_date_input.setDate(selected_date)

        self.no_end_checkbox = QCheckBox("종료일 없음")
        self.no_end_checkbox.setChecked(True)
        self.no_end_checkbox.toggled.connect(self.update_mode_widgets)

        self.start_time_input = QTimeEdit()
        self.start_time_input.setDisplayFormat("HH:mm")
        self.start_time_input.setTime(QTime(9, 0))

        self.end_time_input = QTimeEdit()
        self.end_time_input.setDisplayFormat("HH:mm")
        self.end_time_input.setTime(QTime(10, 0))

        self.color_picker = ColorPicker()

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

        self.date_label = QLabel("날짜")
        self.start_time_label = QLabel("시작")
        self.end_time_label = QLabel("종료")
        self.no_end_label = QLabel("")
        self.end_date_label = QLabel("종료일")

        form_layout.addRow("제목", self.title_input)
        form_layout.addRow("", self.period_checkbox)
        form_layout.addRow(self.date_label, self.date_input)
        form_layout.addRow(self.start_time_label, self.start_time_input)
        form_layout.addRow(self.end_time_label, self.end_time_input)
        form_layout.addRow(self.no_end_label, self.no_end_checkbox)
        form_layout.addRow(self.end_date_label, self.end_date_input)
        form_layout.addRow("색상", self.color_picker)

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
        self.update_mode_widgets()

    def update_mode_widgets(self):
        is_period = self.period_checkbox.isChecked()
        self.date_label.setText("시작일" if is_period else "날짜")

        for widget in [
            self.start_time_label,
            self.start_time_input,
            self.end_time_label,
            self.end_time_input,
        ]:
            widget.setVisible(not is_period)

        for widget in [
            self.no_end_label,
            self.no_end_checkbox,
            self.end_date_label,
            self.end_date_input,
        ]:
            widget.setVisible(is_period)

        self.end_date_input.setEnabled(is_period and not self.no_end_checkbox.isChecked())

    def event_data(self):
        title = self.title_input.text().strip()
        if not title:
            raise ValueError("제목을 입력해주세요")

        if self.period_checkbox.isChecked():
            start_date = self.date_input.date().toString("yyyy-MM-dd")
            end_date = None if self.no_end_checkbox.isChecked() else self.end_date_input.date().toString("yyyy-MM-dd")

            if end_date is not None and end_date < start_date:
                raise ValueError("종료일은 시작일보다 빠를 수 없습니다")

            return {
                "type": "period",
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "color": self.color_picker.color(),
            }

        start_time = self.start_time_input.time()
        end_time = self.end_time_input.time()
        start_minutes = (start_time.hour() * 60) + start_time.minute()
        end_minutes = (end_time.hour() * 60) + end_time.minute()
        duration = end_minutes - start_minutes

        if duration <= 0:
            raise ValueError("종료 시간은 시작 시간보다 늦어야 합니다")

        return {
            "type": "timed",
            "title": title,
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "time": start_time.toString("HH:mm"),
            "duration": duration,
            "color": self.color_picker.color(),
        }

    def accept(self):
        try:
            self.event_data()
        except ValueError as err:
            self.error_label.setText(str(err))
            return

        super().accept()


class EventEditDialog(QDialog):
    def __init__(self, event, parent=None):
        super().__init__(parent)

        self.event = event
        self.requested_delete = False
        self.event_type = event.get("type", "timed")

        self.setWindowTitle("일정 수정")
        self.setModal(True)
        self.setMinimumWidth(380)

        self.title_input = QLineEdit(event.get("title", ""))
        self.color_picker = ColorPicker(event.get("color", DEFAULT_EVENT_COLOR))
        self.error_label = QLabel()
        self.error_label.setObjectName("dialogError")

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(12)
        form_layout.addRow("제목", self.title_input)

        if self.event_type == "period":
            self.start_date_input = QDateEdit()
            self.start_date_input.setCalendarPopup(True)
            self.start_date_input.setDisplayFormat("yyyy-MM-dd")
            self.start_date_input.setDate(QDate.fromString(event["start_date"], "yyyy-MM-dd"))

            self.no_end_checkbox = QCheckBox("종료일 없음")
            self.no_end_checkbox.setChecked(event.get("end_date") is None)

            self.end_date_input = QDateEdit()
            self.end_date_input.setCalendarPopup(True)
            self.end_date_input.setDisplayFormat("yyyy-MM-dd")
            end_date = event.get("end_date") or event["start_date"]
            self.end_date_input.setDate(QDate.fromString(end_date, "yyyy-MM-dd"))
            self.end_date_input.setEnabled(not self.no_end_checkbox.isChecked())
            self.no_end_checkbox.toggled.connect(self.end_date_input.setDisabled)

            form_layout.addRow("시작일", self.start_date_input)
            form_layout.addRow("", self.no_end_checkbox)
            form_layout.addRow("종료일", self.end_date_input)
        else:
            self.date_input = QDateEdit()
            self.date_input.setCalendarPopup(True)
            self.date_input.setDisplayFormat("yyyy-MM-dd")
            self.date_input.setDate(QDate.fromString(event["date"], "yyyy-MM-dd"))

            self.start_time_input = QTimeEdit()
            self.start_time_input.setDisplayFormat("HH:mm")
            self.start_time_input.setTime(QTime.fromString(event["time"], "HH:mm"))

            start_minutes = (self.start_time_input.time().hour() * 60) + self.start_time_input.time().minute()
            end_minutes = start_minutes + int(event.get("duration", 60))
            self.end_time_input = QTimeEdit()
            self.end_time_input.setDisplayFormat("HH:mm")
            self.end_time_input.setTime(QTime((end_minutes // 60) % 24, end_minutes % 60))

            form_layout.addRow("날짜", self.date_input)
            form_layout.addRow("시작", self.start_time_input)
            form_layout.addRow("종료", self.end_time_input)

        form_layout.addRow("색상", self.color_picker)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.request_delete)

        self.cancel_button = QPushButton("취소")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("저장")
        self.save_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch(1)
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

        if self.event_type == "period":
            start_date = self.start_date_input.date().toString("yyyy-MM-dd")
            end_date = None if self.no_end_checkbox.isChecked() else self.end_date_input.date().toString("yyyy-MM-dd")

            if end_date is not None and end_date < start_date:
                raise ValueError("종료일은 시작일보다 빠를 수 없습니다")

            return {
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "color": self.color_picker.color(),
            }

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
            "color": self.color_picker.color(),
        }

    def request_delete(self):
        answer = QMessageBox.question(
            self,
            "일정 삭제",
            "이 일정을 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.requested_delete = True
        super().accept()

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
        self.holiday_update_thread = None

        self.init_ui()
        self.refresh_events()
        self.start_holiday_update()

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

        self.calendar = MarkerCalendar()
        self.calendar.set_marker_provider(self.calendar_markers_for_date)
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
        self.event_list.itemClicked.connect(self.open_event_editor)

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

            QPushButton#dangerButton {
                background-color: #B42318;
                color: #FFFFFF;
            }

            QPushButton#dangerButton:hover {
                background-color: #D92D20;
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

            QCheckBox {
                color: #DDE3EE;
                spacing: 8px;
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
        self.start_holiday_update([year - 1, year, year + 1])

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

    def calendar_markers_for_date(self, date):
        date_str = date.toString("yyyy-MM-dd")
        markers = []

        for holiday_name in self.holidays_for_date(date_str):
            markers.append({
                "title": holiday_name,
                "color": HOLIDAY_COLOR,
                "continues_before": False,
                "continues_after": False,
                "show_title": True,
            })

        for event in self.engine.list_events(date_str):
            color = event.get("color") or DEFAULT_EVENT_COLOR

            if event.get("type") == "period":
                start_date = event["start_date"]
                end_date = event.get("end_date")
                markers.append({
                    "title": event["title"],
                    "color": color,
                    "continues_before": date_str > start_date,
                    "continues_after": end_date is None or date_str < end_date,
                    "show_title": date_str == start_date,
                })
                continue

            markers.append({
                "title": event["title"],
                "color": color,
                "continues_before": False,
                "continues_after": False,
                "show_title": True,
            })

        return markers

    def years_for_holiday_update(self):
        current_year = QDate.currentDate().year()
        shown_year = self.calendar.yearShown()
        selected_year = self.selected_date.year()
        return sorted(
            {
                current_year - 1,
                current_year,
                current_year + 1,
                shown_year - 1,
                shown_year,
                shown_year + 1,
                selected_year,
            }
        )

    def start_holiday_update(self, years=None):
        if self.holiday_update_thread and self.holiday_update_thread.isRunning():
            return

        update_years = years or self.years_for_holiday_update()
        self.holiday_update_thread = HolidayUpdateThread(update_years, self)
        self.holiday_update_thread.updated.connect(self.on_holiday_update_finished)
        self.holiday_update_thread.finished.connect(self.clear_holiday_update_thread)
        self.holiday_update_thread.start()

    def on_holiday_update_finished(self, result):
        if not getattr(result, "updated", False):
            return

        self.holiday_cache.clear()
        self.apply_holiday_styles()
        self.refresh_events()

    def clear_holiday_update_thread(self):
        self.holiday_update_thread = None

    def apply_holiday_styles(self, year=None):
        if year is None:
            year = self.calendar.yearShown()

        holiday_format = QTextCharFormat()
        holiday_format.setForeground(QBrush(QColor(HOLIDAY_COLOR)))
        holiday_format.setFontWeight(700)

        for target_year in [year - 1, year, year + 1]:
            for date_str in self.holidays_for_year(target_year):
                qdate = QDate.fromString(date_str, "yyyy-MM-dd")
                self.calendar.setDateTextFormat(qdate, holiday_format)

        self.calendar.updateCells()

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
            if data["type"] == "period":
                result = self.engine.add_period_event(
                    data["title"],
                    data["start_date"],
                    data["end_date"],
                    color=data["color"],
                )
            else:
                result = self.engine.add_event(
                    data["title"],
                    data["date"],
                    data["time"],
                    data["duration"],
                    color=data["color"],
                )
        except Exception as err:
            self.show_result(f"실패: {err}")
            return

        if result.get("type") == "period":
            self.selected_date = QDate.fromString(result["start_date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            self.show_result(f"기간 직접 추가됨\n{result['title']}")
            self.refresh_events()
            return

        self.selected_date = QDate.fromString(result["date"], "yyyy-MM-dd")
        self.calendar.setSelectedDate(self.selected_date)
        self.show_result(f"직접 추가됨\n{result['time']} | {result['title']}")
        self.refresh_events()

    def open_event_editor(self, item):
        event_id = item.data(Qt.ItemDataRole.UserRole)
        if event_id is None:
            return

        try:
            event = self.engine.get_event(event_id)
        except Exception as err:
            self.show_result(f"실패: {err}")
            return

        dialog = EventEditDialog(event, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            if dialog.requested_delete:
                self.engine.delete_event(event_id)
                self.show_result(f"삭제됨\n{event['title']}")
            else:
                data = dialog.event_data()
                result = self.engine.update_event(event_id, **data)
                if result.get("type") == "period":
                    self.selected_date = QDate.fromString(result["start_date"], "yyyy-MM-dd")
                    self.show_result(f"수정됨\n{result['title']}")
                else:
                    self.selected_date = QDate.fromString(result["date"], "yyyy-MM-dd")
                    self.show_result(f"수정됨\n{result['time']} | {result['title']}")

                self.calendar.setSelectedDate(self.selected_date)
        except Exception as err:
            self.show_result(f"실패: {err}")
            return

        self.refresh_events()

    def refresh_events(self):
        date_str = self.selected_date.toString("yyyy-MM-dd")
        events = self.engine.list_events(date_str)
        holidays = self.holidays_for_date(date_str)

        self.events_title.setText(self.event_title_text())
        self.event_list.clear()

        for holiday_name in holidays:
            item = QListWidgetItem(f"휴일 | {holiday_name}")
            item.setForeground(QBrush(QColor(HOLIDAY_COLOR)))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.event_list.addItem(item)

        if not events and not holidays:
            item = QListWidgetItem("일정 없음")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.event_list.addItem(item)
            self.calendar.updateCells()
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
            item.setForeground(QBrush(QColor(event.get("color") or DEFAULT_EVENT_COLOR)))
            item.setData(Qt.ItemDataRole.UserRole, event["id"])
            item.setToolTip("클릭하여 수정/삭제")
            self.event_list.addItem(item)

        self.calendar.updateCells()

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
