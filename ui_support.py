#UI보조 요소 파일

from PyQt6.QtCore import QDate, QRectF, QThread, Qt, QTime, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QPainter
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

import os

from calendar_engine import (
    DEFAULT_EVENT_COLOR,
    RECURRENCE_MONTHLY,
    RECURRENCE_NONE,
    RECURRENCE_WEEKLY,
    RECURRENCE_YEARLY,
)
from holiday_updater import (
    API_KEY_ENV as HOLIDAY_API_KEY_ENV,
    ENV_FILE,
    get_api_key as get_holiday_api_key,
    update_holiday_cache,
)
from korean_datetime_parser import lunar_to_solar
from openai_calendar_client import (
    DEFAULT_OPENAI_MODEL,
    OPENAI_API_KEY_ENV,
    OPENAI_MODEL_ENV,
    get_openai_api_key,
    get_openai_model,
    parse_calendar_command,
)

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
RECURRENCE_OPTIONS = [
    ("반복 없음", RECURRENCE_NONE),
    ("매주", RECURRENCE_WEEKLY),
    ("매달", RECURRENCE_MONTHLY),
    ("매년", RECURRENCE_YEARLY),
]
RECURRENCE_LABELS = {
    RECURRENCE_NONE: "",
    RECURRENCE_WEEKLY: "매주",
    RECURRENCE_MONTHLY: "매달",
    RECURRENCE_YEARLY: "매년",
}
AI_CONFIRM_ACCEPT_WORDS = {
    "네",
    "예",
    "응",
    "ㅇㅇ",
    "좋아",
    "그래",
    "실행",
    "실행해",
    "실행해줘",
    "확인",
    "진행",
    "진행해",
    "해",
    "해줘",
    "yes",
    "y",
    "ok",
    "okay",
}
AI_CONFIRM_REJECT_WORDS = {
    "아니",
    "아니오",
    "아니요",
    "ㄴㄴ",
    "싫어",
    "취소",
    "취소해",
    "취소해줘",
    "중단",
    "중단해",
    "하지마",
    "안해",
    "no",
    "n",
    "cancel",
}


def recurrence_label(value): #반복/AI 확인 관련 상수와 helper
    return RECURRENCE_LABELS.get(value or RECURRENCE_NONE, "")


def normalize_ai_confirmation_reply(text):
    return text.strip().lower().replace(" ", "")


def is_ai_confirmation_acceptance(text):
    return normalize_ai_confirmation_reply(text) in AI_CONFIRM_ACCEPT_WORDS


def is_ai_confirmation_rejection(text):
    return normalize_ai_confirmation_reply(text) in AI_CONFIRM_REJECT_WORDS


class HolidayUpdateThread(QThread):
    updated = pyqtSignal(object)

    def __init__(self, years, parent=None):
        super().__init__(parent)
        self.years = years

    def run(self):
        result = update_holiday_cache(self.years)
        self.updated.emit(result)


class AICommandThread(QThread):
    parsed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text

    def run(self):
        try:
            result = parse_calendar_command(self.text) #입력 받은 텍스트를 parse_calendar_command에 보냄
        except Exception as err:
            self.failed.emit(str(err))
            return

        self.parsed.emit(result)


class ConnectionStatusButton(QPushButton):
    hovered = pyqtSignal()

    def enterEvent(self, event):
        self.hovered.emit()
        super().enterEvent(event)


class CompactIconButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)


def save_env_values(values, env_path=ENV_FILE):
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    remaining = dict(values)
    next_lines = []
    for raw_line in lines:
        line = raw_line.strip()
        key = line.split("=", 1)[0].strip() if "=" in line and not line.startswith("#") else None

        if key in remaining:
            value = remaining.pop(key).strip()
            if value:
                next_lines.append(f"{key}={value}\n")
            continue

        next_lines.append(raw_line)

    for key, value in remaining.items():
        value = value.strip()
        if value:
            next_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(next_lines)


def apply_runtime_env(values):
    for key, value in values.items():
        value = value.strip()
        if value:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)


def qdate_to_storage_date(qdate, use_lunar=False, leap_month=False):
    if not use_lunar:
        return qdate.toString("yyyy-MM-dd")

    try:
        solar_date = lunar_to_solar(qdate.year(), qdate.month(), qdate.day(), leap_month)
    except ValueError as err:
        raise ValueError("유효하지 않은 음력 날짜입니다") from err

    return solar_date.strftime("%Y-%m-%d")


class MarkerCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.marker_provider = None
        self.max_markers = 3

    def set_marker_provider(self, provider):
        self.marker_provider = provider

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)

        if date.month() != self.monthShown() or date.year() != self.yearShown():
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(16, 17, 20, 155))
            painter.drawRect(rect)
            painter.restore()

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
        marker_font = painter.font()
        if marker_font.pointSizeF() > 0:
            marker_font.setPointSizeF(marker_font.pointSizeF() * 0.95)
        elif marker_font.pixelSize() > 0:
            marker_font.setPixelSize(max(1, round(marker_font.pixelSize() * 0.95)))
        marker_metrics = QFontMetrics(marker_font)

        bar_height = max(13, marker_metrics.height() + 1)
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
                painter.setFont(marker_font)
                painter.setPen(QColor("#FFFFFF"))
                text_rect = bar_rect.adjusted(4, 0, -3, 0)
                text_left = int(text_rect.left())
                text_baseline = int(
                    round(
                        bar_rect.top()
                        + ((bar_height - marker_metrics.height()) / 2)
                        + marker_metrics.ascent()
                    )
                )
                painter.save()
                painter.setClipRect(text_rect)
                painter.drawText(text_left, text_baseline, marker.get("title", ""))
                painter.restore()

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
    submitted = pyqtSignal()

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

    def keyPressEvent(self, event):
        is_enter = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        if is_enter and not is_shift:
            event.accept()
            self.submitted.emit()
            return

        super().keyPressEvent(event)


def lock_dialog_size_to_content(dialog, minimum_width=0):
    dialog.setSizeGripEnabled(False)
    dialog.setMinimumSize(0, 0)
    dialog.setMaximumSize(16777215, 16777215)

    layout = dialog.layout()
    if layout is not None:
        layout.invalidate()
        layout.activate()

    dialog.adjustSize()
    size = dialog.sizeHint()
    size.setWidth(max(size.width(), minimum_width))
    dialog.setFixedSize(size)


MINUTES_PER_DAY = 24 * 60


def qtime_to_minutes(value):
    return (value.hour() * 60) + value.minute()


def duration_between_times(start_time, end_time):
    start_minutes = qtime_to_minutes(start_time)
    end_minutes = qtime_to_minutes(end_time)
    if end_minutes < start_minutes:
        end_minutes += MINUTES_PER_DAY
    return end_minutes - start_minutes


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("설정")
        self.setModal(True)
        self.fixed_minimum_width = 430
        self.setMinimumWidth(self.fixed_minimum_width)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("API 설정")
        title.setObjectName("sectionTitle")

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)

        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_input.setText(get_openai_api_key() or "")
        self.openai_key_input.setPlaceholderText("OPENAI_API_KEY")

        self.openai_model_input = QLineEdit()
        self.openai_model_input.setText(get_openai_model() or DEFAULT_OPENAI_MODEL)
        self.openai_model_input.setPlaceholderText(DEFAULT_OPENAI_MODEL)

        self.holiday_key_input = QLineEdit()
        self.holiday_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.holiday_key_input.setText(get_holiday_api_key() or "")
        self.holiday_key_input.setPlaceholderText("KOREA_HOLIDAY_API_KEY")

        self.show_keys_checkbox = QCheckBox("키 표시")
        self.show_keys_checkbox.toggled.connect(self.toggle_key_visibility)

        form_layout.addRow("OpenAI API 키", self.openai_key_input)
        form_layout.addRow("OpenAI 모델", self.openai_model_input)
        form_layout.addRow("공휴일 API 키", self.holiday_key_input)
        form_layout.addRow("", self.show_keys_checkbox)

        self.error_label = QLabel()
        self.error_label.setObjectName("dialogError")

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        cancel_button = QPushButton("취소")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("저장")
        save_button.clicked.connect(self.accept)

        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.error_label)
        layout.addLayout(button_row)

        self.setLayout(layout)
        lock_dialog_size_to_content(self, self.fixed_minimum_width)

    def toggle_key_visibility(self, checked):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.openai_key_input.setEchoMode(mode)
        self.holiday_key_input.setEchoMode(mode)

    def settings_data(self):
        return {
            OPENAI_API_KEY_ENV: self.openai_key_input.text().strip(),
            OPENAI_MODEL_ENV: self.openai_model_input.text().strip() or DEFAULT_OPENAI_MODEL,
            HOLIDAY_API_KEY_ENV: self.holiday_key_input.text().strip(),
        }

    def accept(self):
        data = self.settings_data()
        if not data[OPENAI_MODEL_ENV]:
            self.error_label.setText("OpenAI 모델명을 입력해주세요")
            return

        super().accept()


class ManualEventDialog(QDialog): #이벤트 직접추가 버튼 누르면 나오는 요소들
    def __init__(self, selected_date, parent=None):
        super().__init__(parent)

        self.setWindowTitle("일정 직접 추가")
        self.setModal(True)
        self.fixed_minimum_width = 360
        self.setMinimumWidth(self.fixed_minimum_width)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("제목")

        self.period_checkbox = QCheckBox("기간 일정")
        self.period_checkbox.toggled.connect(self.update_mode_widgets)

        self.lunar_checkbox = QCheckBox("음력으로 입력")
        self.lunar_checkbox.toggled.connect(self.update_mode_widgets)
        self.lunar_leap_checkbox = QCheckBox("윤달")

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

        self.recurrence_input = QComboBox()
        for label, value in RECURRENCE_OPTIONS:
            self.recurrence_input.addItem(label, value)
        self.recurrence_input.currentIndexChanged.connect(self.update_mode_widgets)

        self.recurrence_end_checkbox = QCheckBox("반복 종료일 지정")
        self.recurrence_end_checkbox.toggled.connect(self.update_mode_widgets)

        self.recurrence_end_date_input = QDateEdit()
        self.recurrence_end_date_input.setCalendarPopup(True)
        self.recurrence_end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.recurrence_end_date_input.setDate(selected_date.addMonths(1))

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
        self.recurrence_label = QLabel("반복")
        self.recurrence_end_label = QLabel("반복 종료일")
        self.no_end_label = QLabel("")
        self.end_date_label = QLabel("종료일")

        form_layout.addRow("제목", self.title_input)
        form_layout.addRow("", self.period_checkbox)
        form_layout.addRow("", self.lunar_checkbox)
        form_layout.addRow("", self.lunar_leap_checkbox)
        form_layout.addRow(self.date_label, self.date_input)
        form_layout.addRow(self.start_time_label, self.start_time_input)
        form_layout.addRow(self.end_time_label, self.end_time_input)
        form_layout.addRow(self.recurrence_label, self.recurrence_input)
        form_layout.addRow("", self.recurrence_end_checkbox)
        form_layout.addRow(self.recurrence_end_label, self.recurrence_end_date_input)
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
        has_recurrence = self.recurrence_value() != RECURRENCE_NONE
        self.date_label.setText("시작일" if is_period else "날짜")

        for widget in [
            self.start_time_label,
            self.start_time_input,
            self.end_time_label,
            self.end_time_input,
            self.recurrence_label,
            self.recurrence_input,
        ]:
            widget.setVisible(not is_period)

        for widget in [
            self.recurrence_end_checkbox,
            self.recurrence_end_label,
            self.recurrence_end_date_input,
        ]:
            widget.setVisible((not is_period) and has_recurrence)

        for widget in [
            self.no_end_label,
            self.no_end_checkbox,
            self.end_date_label,
            self.end_date_input,
        ]:
            widget.setVisible(is_period)

        self.end_date_input.setEnabled(is_period and not self.no_end_checkbox.isChecked())
        self.recurrence_end_date_input.setEnabled(
            (not is_period) and has_recurrence and self.recurrence_end_checkbox.isChecked()
        )
        self.lunar_leap_checkbox.setVisible(self.lunar_checkbox.isChecked())
        if self.layout() is not None:
            lock_dialog_size_to_content(self, self.fixed_minimum_width)

    def recurrence_value(self):
        return self.recurrence_input.currentData() or RECURRENCE_NONE

    def input_date_string(self, date_input):
        return qdate_to_storage_date(
            date_input.date(),
            self.lunar_checkbox.isChecked(),
            self.lunar_leap_checkbox.isChecked(),
        )

    def event_data(self):
        title = self.title_input.text().strip()
        if not title:
            raise ValueError("제목을 입력해주세요")

        if self.period_checkbox.isChecked():
            start_date = self.input_date_string(self.date_input)
            end_date = None if self.no_end_checkbox.isChecked() else self.input_date_string(self.end_date_input)

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
        duration = duration_between_times(start_time, end_time)

        if duration <= 0:
            raise ValueError("종료 시간은 시작 시간보다 늦어야 합니다")

        recurrence = self.recurrence_value()
        recurrence_end = (
            self.input_date_string(self.recurrence_end_date_input)
            if recurrence != RECURRENCE_NONE and self.recurrence_end_checkbox.isChecked()
            else None
        )
        event_date = self.input_date_string(self.date_input)
        if recurrence_end is not None and recurrence_end < event_date:
            raise ValueError("반복 종료일은 시작일보다 빠를 수 없습니다")

        return {
            "type": "timed",
            "title": title,
            "date": event_date,
            "time": start_time.toString("HH:mm"),
            "duration": duration,
            "color": self.color_picker.color(),
            "recurrence": recurrence,
            "recurrence_end": recurrence_end,
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

        self.requested_delete = False
        self.requested_skip = False
        self.event_type = event.get("type", "timed")
        self.is_recurring_timed = (
            self.event_type != "period"
            and event.get("recurrence", RECURRENCE_NONE) != RECURRENCE_NONE
        )

        self.setWindowTitle("일정 수정")
        self.setModal(True)
        self.fixed_minimum_width = 380
        self.setMinimumWidth(self.fixed_minimum_width)

        self.title_input = QLineEdit(event.get("title", ""))
        self.color_picker = ColorPicker(event.get("color", DEFAULT_EVENT_COLOR))
        self.lunar_checkbox = QCheckBox("음력으로 입력")
        self.lunar_checkbox.toggled.connect(self.update_lunar_widgets)
        self.lunar_leap_checkbox = QCheckBox("윤달")
        self.error_label = QLabel()
        self.error_label.setObjectName("dialogError")

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(12)
        form_layout.addRow("제목", self.title_input)
        form_layout.addRow("", self.lunar_checkbox)
        form_layout.addRow("", self.lunar_leap_checkbox)

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

            self.recurrence_input = QComboBox()
            for label, value in RECURRENCE_OPTIONS:
                self.recurrence_input.addItem(label, value)
            self.set_recurrence_value(event.get("recurrence", RECURRENCE_NONE))
            self.recurrence_input.currentIndexChanged.connect(self.update_recurrence_widgets)

            self.recurrence_end_checkbox = QCheckBox("반복 종료일 지정")
            self.recurrence_end_checkbox.setChecked(event.get("recurrence_end") is not None)
            self.recurrence_end_checkbox.toggled.connect(self.update_recurrence_widgets)

            self.recurrence_end_date_input = QDateEdit()
            self.recurrence_end_date_input.setCalendarPopup(True)
            self.recurrence_end_date_input.setDisplayFormat("yyyy-MM-dd")
            recurrence_end = event.get("recurrence_end") or event["date"]
            self.recurrence_end_date_input.setDate(QDate.fromString(recurrence_end, "yyyy-MM-dd"))

            form_layout.addRow("날짜", self.date_input)
            form_layout.addRow("시작", self.start_time_input)
            form_layout.addRow("종료", self.end_time_input)
            self.recurrence_end_label = QLabel("반복 종료일")
            form_layout.addRow("반복", self.recurrence_input)
            form_layout.addRow("", self.recurrence_end_checkbox)
            form_layout.addRow(self.recurrence_end_label, self.recurrence_end_date_input)

            if self.is_recurring_timed:
                self.scope_input = QComboBox()
                self.scope_input.addItem("전체 반복 일정", "all")
                self.scope_input.addItem("이 회차만 수정", "occurrence")
                if event.get("is_override"):
                    self.scope_input.setCurrentIndex(1)
                form_layout.addRow("적용 범위", self.scope_input)

            self.update_recurrence_widgets()

        form_layout.addRow("색상", self.color_picker)

        self.delete_button = QPushButton("삭제")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.request_delete)

        self.skip_button = QPushButton("이번 회차 건너뛰기")
        self.skip_button.setObjectName("secondaryButton")
        self.skip_button.clicked.connect(self.request_skip)
        self.skip_button.setVisible(self.is_recurring_timed)

        self.cancel_button = QPushButton("취소")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("저장")
        self.save_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.skip_button)
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
        self.update_lunar_widgets()

    def recurrence_value(self):
        if self.event_type == "period":
            return RECURRENCE_NONE
        return self.recurrence_input.currentData() or RECURRENCE_NONE

    def scope_value(self):
        if not self.is_recurring_timed:
            return "all"
        return self.scope_input.currentData() or "all"

    def set_recurrence_value(self, value):
        value = value or RECURRENCE_NONE
        for index in range(self.recurrence_input.count()):
            if self.recurrence_input.itemData(index) == value:
                self.recurrence_input.setCurrentIndex(index)
                return

    def update_lunar_widgets(self):
        self.lunar_leap_checkbox.setVisible(self.lunar_checkbox.isChecked())
        if self.layout() is not None:
            lock_dialog_size_to_content(self, self.fixed_minimum_width)

    def input_date_string(self, date_input):
        return qdate_to_storage_date(
            date_input.date(),
            self.lunar_checkbox.isChecked(),
            self.lunar_leap_checkbox.isChecked(),
        )

    def update_recurrence_widgets(self):
        if self.event_type == "period":
            return

        has_recurrence = self.recurrence_value() != RECURRENCE_NONE
        for widget in [
            self.recurrence_end_checkbox,
            self.recurrence_end_label,
            self.recurrence_end_date_input,
        ]:
            widget.setVisible(has_recurrence)

        self.recurrence_end_date_input.setEnabled(
            has_recurrence and self.recurrence_end_checkbox.isChecked()
        )
        if self.layout() is not None:
            lock_dialog_size_to_content(self, self.fixed_minimum_width)

    def event_data(self):
        title = self.title_input.text().strip()
        if not title:
            raise ValueError("제목을 입력해주세요")

        if self.event_type == "period":
            start_date = self.input_date_string(self.start_date_input)
            end_date = None if self.no_end_checkbox.isChecked() else self.input_date_string(self.end_date_input)

            if end_date is not None and end_date < start_date:
                raise ValueError("종료일은 시작일보다 빠를 수 없습니다")

            return {
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "color": self.color_picker.color(),
                "scope": "all",
            }

        start_time = self.start_time_input.time()
        end_time = self.end_time_input.time()
        duration = duration_between_times(start_time, end_time)

        if duration <= 0:
            raise ValueError("종료 시간은 시작 시간보다 늦어야 합니다")

        recurrence = self.recurrence_value()
        recurrence_end = (
            self.input_date_string(self.recurrence_end_date_input)
            if recurrence != RECURRENCE_NONE and self.recurrence_end_checkbox.isChecked()
            else None
        )
        event_date = self.input_date_string(self.date_input)
        if recurrence_end is not None and recurrence_end < event_date:
            raise ValueError("반복 종료일은 시작일보다 빠를 수 없습니다")

        return {
            "title": title,
            "date": event_date,
            "time": start_time.toString("HH:mm"),
            "duration": duration,
            "color": self.color_picker.color(),
            "recurrence": recurrence,
            "recurrence_end": recurrence_end,
            "scope": self.scope_value(),
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

    def request_skip(self):
        answer = QMessageBox.question(
            self,
            "회차 건너뛰기",
            "이 반복 일정의 선택한 회차만 건너뛸까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.requested_skip = True
        super().accept()

    def accept(self):
        try:
            self.event_data()
        except ValueError as err:
            self.error_label.setText(str(err))
            return

        super().accept()
