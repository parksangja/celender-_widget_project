##UI파일

import sys
from datetime import datetime
from time import perf_counter

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QTextCharFormat
from PyQt6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from calendar_engine import DEFAULT_EVENT_COLOR, CalendarEngine
from executor import execute
from holiday_updater import (
    get_api_key as get_holiday_api_key,
    get_korean_holidays,
    is_cache_fresh,
    load_holiday_cache,
)
from openai_calendar_client import get_openai_model, is_openai_configured
from ui_styles import main_style_sheet
from ui_support import (
    AICommandThread,
    CompactIconButton,
    ConnectionStatusButton,
    EventEditDialog,
    ExpandingCommandInput,
    HOLIDAY_COLOR,
    HolidayUpdateThread,
    ManualEventDialog,
    MarkerCalendar,
    SettingsDialog,
    apply_runtime_env,
    is_ai_confirmation_acceptance,
    is_ai_confirmation_rejection,
    recurrence_label,
    save_env_values,
)


class ResizeBorder(QWidget):#UI크기 조절
    MAX_WIDGET_SIZE = 16777215

    CURSORS = {
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
    }

    def __init__(self, target, edge):
        super().__init__(target)

        self.target = target
        self.edge = edge
        self.drag_start_pos = None
        self.drag_start_geometry = None

        self.setObjectName("resizeBorder")
        self.setCursor(self.CURSORS[edge])
        self.setToolTip("위젯 크기 조절")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.globalPosition().toPoint()
            self.drag_start_geometry = self.target.geometry()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_start_pos is not None:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            self.apply_resize_delta(delta.x(), delta.y())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = None
            self.drag_start_geometry = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def apply_resize_delta(self, width_delta, height_delta):
        start_geometry = self.drag_start_geometry or self.target.geometry()
        next_x = start_geometry.x()
        next_y = start_geometry.y()
        next_width = start_geometry.width()
        next_height = start_geometry.height()

        if "left" in self.edge:
            next_x = start_geometry.x() + width_delta
            next_width = start_geometry.width() - width_delta
        elif "right" in self.edge:
            next_width = start_geometry.width() + width_delta

        if "top" in self.edge:
            next_y = start_geometry.y() + height_delta
            next_height = start_geometry.height() - height_delta
        elif "bottom" in self.edge:
            next_height = start_geometry.height() + height_delta

        max_width = self.target.maximumWidth()
        max_height = self.target.maximumHeight()

        next_x, next_width = self.clamp_axis(
            next_x,
            next_width,
            start_geometry.x(),
            start_geometry.width(),
            self.target.minimumWidth(),
            max_width,
            "left" in self.edge,
        )
        next_y, next_height = self.clamp_axis(
            next_y,
            next_height,
            start_geometry.y(),
            start_geometry.height(),
            self.target.minimumHeight(),
            max_height,
            "top" in self.edge,
        )

        self.target.setGeometry(next_x, next_y, next_width, next_height)

    def clamp_axis(self, next_pos, next_size, start_pos, start_size, min_size, max_size, anchored_at_start):
        if next_size < min_size:
            next_size = min_size
            if anchored_at_start:
                next_pos = start_pos + start_size - min_size

        if max_size < self.MAX_WIDGET_SIZE and next_size > max_size:
            next_size = max_size
            if anchored_at_start:
                next_pos = start_pos + start_size - max_size

        return next_pos, next_size


class CalendarWidget(QWidget): #메인 UI 구현
    def __init__(self):
        super().__init__()

        self.engine = CalendarEngine()
        self.selected_date = QDate.currentDate()
        self.old_pos = None
        self.ai_panel_collapsed = False
        self.expanded_minimum_width = 820
        self.minimum_widget_height = 500
        self.expanded_stretches = (3, 4, 2)
        self.collapsed_stretches = (2, 11, 5)
        self.ai_collapse_progress = 0.0
        self.ai_panel_width = 260
        self.ai_panel_animation_duration = 140
        self.ai_panel_animation_timer = QTimer(self)
        self.ai_panel_animation_timer.setInterval(16)
        self.ai_panel_animation_timer.timeout.connect(self.update_ai_panel_animation_frame)
        self.ai_animation_start_time = 0.0
        self.ai_animation_start_progress = 0.0
        self.ai_animation_end_progress = 0.0
        self.ai_animation_target_collapsed = False
        self.holiday_cache = {}
        self.holiday_update_thread = None
        self.ai_command_thread = None
        self.pending_ai_text = ""
        self.pending_confirmation_command = None
        self.pending_confirmation_prefix = ""
        self.openai_connection_status = self.initial_openai_connection_status()
        self.holiday_connection_status = self.initial_holiday_connection_status()

        self.init_ui()
        self.refresh_connection_status_icon()
        self.refresh_events()
        self.start_holiday_update()

    def init_ui(self): #초기 설정
        self.setWindowTitle("Mini Calendar Widget")
        self.setMinimumSize(self.expanded_minimum_width, self.minimum_widget_height)
        self.resize(960, 600)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )

        window_layout = QVBoxLayout()
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)

        self.title_bar = self._build_title_bar()

        body = QWidget()
        body.setObjectName("body")
        self.body = body

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)
        self.body_layout = root_layout

        self.ai_panel = self._build_ai_panel()
        self.ai_slot = self._build_ai_slot()
        self.ai_panel.setParent(self.ai_slot)
        self.status_panel = self._build_status_panel()
        self.calendar_panel = self._build_calendar_panel()
        self.events_panel = self._build_events_panel()

        root_layout.addWidget(self.ai_slot, 3)
        root_layout.addWidget(self.status_panel)
        root_layout.addWidget(self.calendar_panel, 4)
        root_layout.addWidget(self.events_panel, 2)
        self.set_panel_stretches(0.0)

        body.setLayout(root_layout)
        window_layout.addWidget(self.title_bar)
        window_layout.addWidget(body, 1)

        self.setLayout(window_layout)
        self.setStyleSheet(self._style_sheet())

        self.resize_border_size = 8
        self.resize_corner_size = 18
        self.resize_borders = self.create_resize_borders()
        self.position_resize_borders()

        self.show()
        self.apply_ai_panel_progress(0.0)

    def _build_title_bar(self):
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(30)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(8)

        title = QLabel("Mini Calendar Widget")
        title.setObjectName("windowTitle")

        close_button = QPushButton("X")
        close_button.setObjectName("windowCloseButton")
        close_button.setFixedSize(22, 22)
        close_button.clicked.connect(self.close)

        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(close_button)
        title_bar.setLayout(layout)

        title_bar.mousePressEvent = self.mousePressEvent
        title_bar.mouseMoveEvent = self.mouseMoveEvent
        title_bar.mouseReleaseEvent = self.mouseReleaseEvent
        title.mousePressEvent = self.mousePressEvent
        title.mouseMoveEvent = self.mouseMoveEvent
        title.mouseReleaseEvent = self.mouseReleaseEvent
        return title_bar

    def _build_ai_slot(self):
        slot = QFrame()
        slot.setObjectName("aiSlot")
        slot.setMinimumWidth(self.ai_panel_width)
        return slot

    def _build_ai_panel(self): #UI에 있는 3개 구역 중, 첫번째 구역인 AI입력 구역 붙이는 함수
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(self.ai_panel_width)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("AI 입력")
        title.setObjectName("sectionTitle")

        self.result_box = QTextEdit()
        self.result_box.setObjectName("resultBox")
        self.result_box.setReadOnly(True)
        self.result_box.setText("대기 중")

        self.command_input = ExpandingCommandInput() #AI창에 입력
        self.command_input.setPlaceholderText("일정을 입력하세요") #입력하는 곳에 뜨는 메세지
        self.command_input.submitted.connect(self.run_command) #입력을 run_command함수에 보냄

        self.confirmation_action_area = QFrame()
        confirmation_layout = QHBoxLayout()
        confirmation_layout.setContentsMargins(0, 0, 0, 0)
        confirmation_layout.setSpacing(8)

        self.confirm_execute_button = QPushButton("실행")
        self.confirm_execute_button.clicked.connect(self.accept_pending_ai_command)

        self.confirm_cancel_button = QPushButton("취소")
        self.confirm_cancel_button.setObjectName("secondaryButton")
        self.confirm_cancel_button.clicked.connect(self.reject_pending_ai_command)

        confirmation_layout.addWidget(self.confirm_cancel_button)
        confirmation_layout.addWidget(self.confirm_execute_button)
        self.confirmation_action_area.setLayout(confirmation_layout)
        self.confirmation_action_area.setVisible(False)

        layout.addWidget(title)
        layout.addWidget(self.result_box, 1)
        layout.addWidget(self.command_input)
        layout.addWidget(self.confirmation_action_area)

        panel.setLayout(layout)
        return panel

    def _build_status_panel(self):
        panel = QFrame()
        panel.setObjectName("statusRail")
        panel.setFixedWidth(28)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(0)

        self.ai_toggle_button = CompactIconButton("≡")
        self.ai_toggle_button.setObjectName("aiToggleIcon")
        self.ai_toggle_button.setFixedSize(24, 24)
        self.ai_toggle_button.setToolTip("AI 입력창 접기")
        self.ai_toggle_button.clicked.connect(self.toggle_ai_panel)

        self.connection_status_button = ConnectionStatusButton("i")
        self.connection_status_button.setObjectName("connectionStatusIcon")
        self.connection_status_button.setFixedSize(12, 12)
        self.connection_status_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connection_status_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.connection_status_button.hovered.connect(self.refresh_connection_status_from_sources)
        self.connection_status_button.clicked.connect(self.open_settings_dialog)

        layout.addWidget(self.ai_toggle_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(self.connection_status_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        panel.setLayout(layout)
        return panel

    def _build_calendar_panel(self): #2번째 구역, 캘린더 붙이는 함수
        panel = QFrame()
        panel.setObjectName("calendarPanel")
        panel.setMinimumWidth(300)

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
        panel.setMinimumWidth(170)

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
        return main_style_sheet()

    def create_resize_borders(self):
        borders = {}
        for edge in [
            "left",
            "right",
            "top",
            "bottom",
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
        ]:
            borders[edge] = ResizeBorder(self, edge)
        return borders

    def position_resize_borders(self):
        if not hasattr(self, "resize_borders"):
            return

        width = self.width()
        height = self.height()
        border = self.resize_border_size
        corner = self.resize_corner_size
        title_height = self.title_bar.height()
        title_button_guard_width = 52
        horizontal_length = max(0, width - (corner * 2))
        safe_top_horizontal_length = max(0, width - corner - title_button_guard_width)
        vertical_length = max(0, height - title_height - corner)

        self.resize_borders["top_left"].setGeometry(0, 0, corner, corner)
        self.resize_borders["top_right"].setGeometry(0, 0, 0, 0)
        self.resize_borders["bottom_left"].setGeometry(0, height - corner, corner, corner)
        self.resize_borders["bottom_right"].setGeometry(
            width - corner,
            height - corner,
            corner,
            corner,
        )
        self.resize_borders["top"].setGeometry(corner, 0, safe_top_horizontal_length, border)
        self.resize_borders["bottom"].setGeometry(
            corner,
            height - border,
            horizontal_length,
            border,
        )
        self.resize_borders["left"].setGeometry(0, title_height, border, vertical_length)
        self.resize_borders["right"].setGeometry(
            width - border,
            title_height,
            border,
            vertical_length,
        )

        for resize_border in self.resize_borders.values():
            resize_border.raise_()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None

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
        self.holiday_connection_status = (
            f"공휴일 API: 업데이트 확인 중 ({self.year_range_text(update_years)})"
        )
        self.refresh_connection_status_icon()
        self.holiday_update_thread = HolidayUpdateThread(update_years, self)
        self.holiday_update_thread.updated.connect(self.on_holiday_update_finished)
        self.holiday_update_thread.finished.connect(self.clear_holiday_update_thread)
        self.holiday_update_thread.start()

    def on_holiday_update_finished(self, result):
        self.holiday_connection_status = self.format_holiday_connection_status(result)
        self.refresh_connection_status_icon()

        if not getattr(result, "updated", False):
            return

        self.holiday_cache.clear()
        self.apply_holiday_styles()
        self.refresh_events()

    def clear_holiday_update_thread(self):
        self.holiday_update_thread = None

    def clear_ai_command_thread(self):
        self.ai_command_thread = None #채팅창 내용을 비움
        self.pending_ai_text = "" #입력창을 비움
        self.command_input.setEnabled(True) #입력창에 쓸 수 있게 만듬.

    def refresh_connection_status_from_sources(self):
        if self.ai_command_thread and self.ai_command_thread.isRunning():
            self.openai_connection_status = "OpenAI API: 요청 처리 중"
        elif self.openai_connection_status.startswith("OpenAI API: 키 없음") or (
            not is_openai_configured()
        ):
            self.openai_connection_status = self.initial_openai_connection_status()

        if self.holiday_update_thread and self.holiday_update_thread.isRunning():
            pass
        else:
            self.holiday_connection_status = self.initial_holiday_connection_status()

        self.refresh_connection_status_icon()

    def initial_openai_connection_status(self):
        if not is_openai_configured():
            return "OpenAI API: 키 없음, 로컬 파서 사용"

        return f"OpenAI API: 키 설정됨, 호출 전 ({get_openai_model()})"

    def initial_holiday_connection_status(self):
        if not get_holiday_api_key():
            return "공휴일 API: 키 없음, 저장된 캐시만 사용"

        cache = load_holiday_cache()
        updated_at = cache.get("updated_at")
        if is_cache_fresh(cache):
            return f"공휴일 API: 캐시 최신 ({self.format_cache_time(updated_at)})"

        if updated_at:
            return f"공휴일 API: 캐시 있음, 업데이트 필요 ({self.format_cache_time(updated_at)})"

        return "공휴일 API: 키 설정됨, 첫 업데이트 전"

    def format_cache_time(self, updated_at):
        if not updated_at:
            return "업데이트 기록 없음"

        try:
            return datetime.fromisoformat(updated_at).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return updated_at

    def year_range_text(self, years):
        years = sorted({int(year) for year in years})
        if not years:
            return "대상 연도 없음"
        if len(years) == 1:
            return f"{years[0]}년"

        return f"{years[0]}~{years[-1]}년"

    def format_holiday_connection_status(self, result):
        years = self.year_range_text(getattr(result, "years", []))
        reason = getattr(result, "reason", "")
        error = getattr(result, "error", "")

        if getattr(result, "updated", False):
            message = f"공휴일 API: 업데이트 완료 ({years})"
            if error:
                message += f"\n일부 연도 오류: {self.short_status_text(error)}"
            return message

        if reason == "fresh_cache":
            return f"공휴일 API: 캐시 최신, API 호출 생략 ({years})"
        if reason == "missing_api_key":
            return "공휴일 API: 키 없음, 저장된 캐시만 사용"
        if reason == "fetch_failed":
            message = "공휴일 API: 업데이트 실패, 저장된 캐시 사용"
            if error:
                message += f"\n오류: {self.short_status_text(error)}"
            return message

        return f"공휴일 API: 상태 확인됨 ({reason or '알 수 없음'})"

    def update_openai_connection_status(self, ai_result):
        source = getattr(ai_result, "source", "")
        message = getattr(ai_result, "message", "")

        if source == "openai":
            self.openai_connection_status = f"OpenAI API: 정상 연결됨 ({get_openai_model()})"
        elif source == "local":
            self.openai_connection_status = "OpenAI API: 키 없음, 로컬 파서 사용"
        elif "사용 한도" in message:
            self.openai_connection_status = "OpenAI API: 사용 한도 부족, 로컬 파서 사용"
        elif source == "local_fallback":
            self.openai_connection_status = (
                f"OpenAI API: 호출 실패, 로컬 파서 사용\n{self.short_status_text(message)}"
            )
        else:
            self.openai_connection_status = "OpenAI API: 상태 확인 필요"

        self.refresh_connection_status_icon()

    def short_status_text(self, text, limit=90):
        text = " ".join(str(text).split())
        if len(text) <= limit:
            return text

        return f"{text[:limit - 3]}..."

    def connection_status_state(self):
        status_text = f"{self.openai_connection_status}\n{self.holiday_connection_status}"
        if "확인 중" in status_text or "요청 처리 중" in status_text:
            return "checking"

        warning_words = ["없음", "실패", "부족", "확인 필요", "오류"]
        if any(word in status_text for word in warning_words):
            return "warning"

        return "ok"

    def connection_status_tooltip(self):
        return (
            "연결 상태\n"
            f"{self.openai_connection_status}\n"
            f"{self.holiday_connection_status}"
        )

    def refresh_connection_status_icon(self):
        if not hasattr(self, "connection_status_button"):
            return

        self.connection_status_button.setToolTip(self.connection_status_tooltip())
        self.connection_status_button.setProperty("state", self.connection_status_state())
        self.connection_status_button.style().unpolish(self.connection_status_button)
        self.connection_status_button.style().polish(self.connection_status_button)
        self.connection_status_button.update()

    def open_settings_dialog(self):
        self.refresh_connection_status_from_sources()
        dialog = SettingsDialog(self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        settings = dialog.settings_data()
        try:
            save_env_values(settings)
            apply_runtime_env(settings)
        except Exception as err:
            QMessageBox.warning(self, "설정 저장 실패", str(err))
            return

        self.openai_connection_status = self.initial_openai_connection_status()
        self.holiday_cache.clear()
        self.holiday_connection_status = self.initial_holiday_connection_status()
        self.refresh_connection_status_icon()
        self.apply_holiday_styles()
        self.refresh_events()
        self.start_holiday_update()
        self.show_result("설정 저장됨\nAPI 연결 상태가 갱신되었습니다.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_resize_borders()
        self.apply_ai_panel_progress(self.ai_collapse_progress)

    def clamp_ai_progress(self, progress):
        return max(0.0, min(1.0, float(progress)))

    def interpolated_stretches(self, progress):
        progress = self.clamp_ai_progress(progress)
        return tuple(
            expanded + (collapsed - expanded) * progress
            for expanded, collapsed in zip(self.expanded_stretches, self.collapsed_stretches)
        )

    def set_panel_stretches(self, progress):
        ai_stretch, calendar_stretch, events_stretch = self.interpolated_stretches(progress)
        scale = 100
        self.body_layout.setStretch(0, max(1, int(round(ai_stretch * scale))))
        self.body_layout.setStretch(1, 0)
        self.body_layout.setStretch(2, max(1, int(round(calendar_stretch * scale))))
        self.body_layout.setStretch(3, max(1, int(round(events_stretch * scale))))
        self.ai_slot.setMinimumWidth(max(0, int(round(self.ai_panel_width * (1.0 - progress)))))
        self.body_layout.invalidate()
        self.body_layout.activate()

    def apply_ai_panel_progress(self, progress):
        if not hasattr(self, "ai_panel") or not hasattr(self, "ai_slot"):
            return

        progress = self.clamp_ai_progress(progress)
        self.ai_collapse_progress = progress
        self.set_panel_stretches(progress)

        panel_width = max(self.ai_panel_width, self.ai_slot.width())
        x = -int(round(panel_width * progress))
        self.ai_panel.setGeometry(
            x,
            0,
            panel_width,
            self.ai_slot.height(),
        )
        self.ai_slot.update()
        self.body.update()

    def repaint_after_panel_toggle(self):
        self.body_layout.invalidate()
        self.body_layout.activate()
        QApplication.processEvents()

        for widget in [
            self,
            self.title_bar,
            self.body,
            self.ai_slot,
            self.ai_panel,
            self.status_panel,
            self.calendar_panel,
            self.events_panel,
            self.calendar,
            self.event_list,
        ]:
            widget.updateGeometry()
            widget.update()
            widget.repaint()

        QApplication.processEvents()

    def set_ai_toggle_visual_state(self):
        self.ai_toggle_button.setToolTip(
            "AI 입력창 펼치기" if self.ai_panel_collapsed else "AI 입력창 접기"
        )
        self.ai_toggle_button.setProperty(
            "collapsed",
            "true" if self.ai_panel_collapsed else "false",
        )
        self.ai_toggle_button.style().unpolish(self.ai_toggle_button)
        self.ai_toggle_button.style().polish(self.ai_toggle_button)
        self.ai_toggle_button.update()

    def toggle_ai_panel(self):
        if self.ai_panel_animation_timer.isActive():
            return

        self.ai_animation_target_collapsed = not self.ai_panel_collapsed
        self.ai_animation_start_progress = self.ai_collapse_progress
        self.ai_animation_end_progress = 1.0 if self.ai_animation_target_collapsed else 0.0
        self.ai_animation_start_time = perf_counter()
        self.ai_toggle_button.setEnabled(False)
        self.update_ai_panel_animation_frame()
        self.ai_panel_animation_timer.start()

    def eased_ai_animation_progress(self, progress):
        progress = self.clamp_ai_progress(progress)
        return 1.0 - ((1.0 - progress) ** 3)

    def update_ai_panel_animation_frame(self):
        elapsed_ms = (perf_counter() - self.ai_animation_start_time) * 1000
        raw_progress = min(1.0, elapsed_ms / self.ai_panel_animation_duration)
        eased_progress = self.eased_ai_animation_progress(raw_progress)
        current_progress = (
            self.ai_animation_start_progress
            + (self.ai_animation_end_progress - self.ai_animation_start_progress) * eased_progress
        )
        self.apply_ai_panel_progress(current_progress)

        if raw_progress >= 1.0:
            self.ai_panel_animation_timer.stop()
            self.ai_panel_collapsed = self.ai_animation_target_collapsed
            self.apply_ai_panel_progress(self.ai_animation_end_progress)
            self.set_ai_toggle_visual_state()
            self.ai_toggle_button.setEnabled(True)
            self.repaint_after_panel_toggle()

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

    def run_command(self):#명령 실행 함수
        text = self.command_input.toPlainText().strip() #사용자 입력을 받아옴
        if self.has_pending_ai_confirmation():          #AI 명령 실행 전 사용자 확인 답변을 기다리는 중이면
            self.handle_pending_ai_confirmation_reply(text) #실행/취소 답변 대기
            return

        if not text: #입력 받은게 없다면
            self.show_result("입력 없음") #채팅창에 "입력 없음" 띄우고 다시 입력 대기
            return

        if self.ai_command_thread is not None and self.ai_command_thread.isRunning():#명령에 대한 ai의 실행이 있고 계속되고 있다면
            self.show_result("AI 해석이 진행 중입니다. 잠시만 기다려주세요.")#채팅창에 옆에 메세지 띄움
            return

        self.pending_ai_text = text
        self.command_input.setEnabled(False) #처리 전까지 채팅 입력 막음
        self.openai_connection_status = "OpenAI API: 요청 처리 중"
        self.refresh_connection_status_icon()
        self.show_result(f"입력\n{text}\n\n해석 중...")

        self.ai_command_thread = AICommandThread(text, self) #명령을 ui_support.py에 있는 클래스에 보냄
        self.ai_command_thread.parsed.connect(self.on_ai_command_parsed) #ai로 처리한 데이터를 on_ai_command_parsed로 보냄
        self.ai_command_thread.failed.connect(self.on_ai_command_failed) #ai로 처리 실패 시 on_ai_command_failed로 보냄
        self.ai_command_thread.finished.connect(self.clear_ai_command_thread) #위 함수가 끝났다면 clear_ai_command_thread로 보냄
        self.ai_command_thread.start() #다시 입력 대기

    def on_ai_command_parsed(self, ai_result):
        self.update_openai_connection_status(ai_result)

        text = self.pending_ai_text #사용자 입력
        command = ai_result.command #ai로 해석한 명령
        prefix = self.ai_result_prefix(text, ai_result, command)#접두사? -> 채팅창 앞에 나오는거

        if command.get("action") == "unknown": #명령이 unknown이면 명령 해석 실패로 간주
            self.show_result(f"{prefix}\n\n실행 결과\n명령을 이해하지 못했습니다.")
            return

        if self.command_requires_confirmation(command): #명령 목록에 있으면
            self.wait_for_ai_confirmation(command, prefix) #실행 확인 대기
            return
        
        self.execute_ai_command(command, prefix) #실행 확인이 되었다면, executor 실행

    def on_ai_command_failed(self, error_message):
        self.openai_connection_status = (
            f"OpenAI API: 처리 실패\n{self.short_status_text(error_message)}"
        )
        self.refresh_connection_status_icon()

        text = self.pending_ai_text
        self.show_result(f"입력\n{text}\n\nAI 출력\n실패: {error_message}")

    def ai_result_prefix(self, text, ai_result, command):
        return (
            f"입력\n{text}\n\n"
            f"AI 출력\n{ai_result.message}\n"
            f"{self.command_summary(command)}"
        )

    def command_summary(self, command):
        action = command.get("action")

        if action == "add":
            repeat = recurrence_label(command.get("recurrence"))
            repeat_text = f", 반복: {repeat}" if repeat else ""
            return (
                f"일정 추가: {command.get('date')} {command.get('time')} "
                f"{command.get('title')}{repeat_text}"
            )

        if action == "add_period":
            end_date = command.get("end_date") or "무기한"
            return f"기간 추가: {command.get('start_date')}~{end_date} {command.get('title')}"

        if action == "list":
            return f"일정 조회: {command.get('date')}"

        if action == "delete":
            return f"일정 삭제 조건: {command.get('condition', {})}"
        if action == "skip_occurrence":
            return f"회차 건너뛰기: {command.get('occurrence_date')} {command.get('condition', {})}"
        if action == "update_occurrence":
            return (
                f"이 회차만 수정: {command.get('occurrence_date')} "
                f"{command.get('updates', {})}"
            )
        if action == "update_recurrence_end":
            return (
                f"반복 종료일 수정: {command.get('recurrence_end')} "
                f"{command.get('condition', {})}"
            )

        return "알 수 없는 명령"

    def command_requires_confirmation(self, command):
        return command.get("action") in {
            "add",
            "add_period",
            "delete",
            "skip_occurrence",
            "update_occurrence",
            "update_recurrence_end",
        }

    def has_pending_ai_confirmation(self): #AI명령 확인 함수
        return self.pending_confirmation_command is not None #입력 없으면 False, 입력 있으면 True

    def set_ai_confirmation_mode(self, active):
        self.confirmation_action_area.setVisible(active)
        self.command_input.setEnabled(True)

    def wait_for_ai_confirmation(self, command, prefix):
        self.pending_confirmation_command = command
        self.pending_confirmation_prefix = prefix
        self.command_input.clear()
        self.set_ai_confirmation_mode(True)
        self.show_pending_ai_confirmation()

    def show_pending_ai_confirmation(self, extra_message=None):
        if not self.has_pending_ai_confirmation():
            return

        command = self.pending_confirmation_command
        prefix = self.pending_confirmation_prefix
        message = (
            f"{prefix}\n\n"
            f"확인\n{self.confirmation_message(command)}\n"
            f"{self.confirmation_detail(command)}\n\n"
            "답변\n실행 또는 취소를 입력하거나 아래 버튼을 선택해주세요."
        )
        if extra_message:
            message += f"\n{extra_message}"
        self.show_result(message)

    def handle_pending_ai_confirmation_reply(self, text):
        if not text:
            self.show_pending_ai_confirmation("아직 답변이 입력되지 않았습니다.")
            return

        if is_ai_confirmation_acceptance(text):
            self.accept_pending_ai_command()
            return

        if is_ai_confirmation_rejection(text):
            self.reject_pending_ai_command()
            return

        self.command_input.clear()
        self.show_pending_ai_confirmation("답변을 이해하지 못했습니다.")

    def clear_pending_ai_confirmation(self):
        self.pending_confirmation_command = None
        self.pending_confirmation_prefix = ""
        self.set_ai_confirmation_mode(False)

    def accept_pending_ai_command(self):
        if not self.has_pending_ai_confirmation():
            return

        command = self.pending_confirmation_command
        prefix = self.pending_confirmation_prefix
        self.clear_pending_ai_confirmation()
        self.execute_ai_command(command, prefix)

    def reject_pending_ai_command(self):
        if not self.has_pending_ai_confirmation():
            return

        prefix = self.pending_confirmation_prefix
        self.clear_pending_ai_confirmation()
        self.command_input.clear()
        self.show_result(f"{prefix}\n\n실행 결과\n사용자가 실행을 취소했습니다.")

    def execute_ai_command(self, command, prefix):
        try:
            result = execute(command, self.engine) #명령을 executor.py에 있는 execute함수에 넣어 실행, 결과 반환
            self.command_input.clear()             #입력창을 비움
            self.apply_command_result(command, result, prefix) #명령에 따른 결과 메세지들과 아까 만든 접두사를 띄움
        except Exception as err: #만약 실행 실패시 아래 오류 메세지 띄움
            self.show_result(f"{prefix}\n\n실행 결과\n실패: {err}")

    def confirmation_message(self, command):
        action = command.get("action")
        if action == "add":
            return "이 일정으로 추가할까요?"
        if action == "add_period":
            return "이 기간 일정으로 추가할까요?"
        if action == "delete":
            return "이 조건으로 삭제할까요?"
        if action == "skip_occurrence":
            return "이 회차만 건너뛸까요?"
        if action == "update_occurrence":
            return "이 회차만 수정할까요?"
        if action == "update_recurrence_end":
            return "반복 종료일을 수정할까요?"

        return "이 명령을 실행할까요?"

    def confirmation_detail(self, command):
        detail = self.command_summary(command)
        if command.get("action") == "delete":
            return f"{detail}\n삭제하면 되돌릴 수 없습니다."

        return detail

    def apply_command_result(self, command, result, message_prefix=None):
        action = command.get("action")
        message = ""

        if action == "add":
            self.selected_date = QDate.fromString(result["date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            message = f"추가됨\n{result['time']} | {result['title']}"

        elif action == "add_period":
            self.selected_date = QDate.fromString(result["start_date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            message = f"기간 추가됨\n{result['title']}"

        elif action == "list":
            self.selected_date = QDate.fromString(command["date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            message = f"조회됨\n{len(result)}개 일정"

        elif action == "delete":
            message = f"삭제됨\n{len(result)}개 일정"

        elif action == "skip_occurrence":
            self.selected_date = QDate.fromString(command["occurrence_date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            message = f"회차 건너뜀\n{result['title']} ({command['occurrence_date']})"

        elif action == "update_occurrence":
            self.selected_date = QDate.fromString(result["date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            message = f"회차 수정됨\n{result['time']} | {result['title']}"

        elif action == "update_recurrence_end":
            self.selected_date = QDate.fromString(result["date"], "yyyy-MM-dd")
            self.calendar.setSelectedDate(self.selected_date)
            end_text = result.get("recurrence_end") or "없음"
            message = f"반복 종료일 수정됨\n{result['title']} | {end_text}"

        if message_prefix:
            self.show_result(f"{message_prefix}\n\n실행 결과\n{message}")
        else:
            self.show_result(message)

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
                    recurrence=data["recurrence"],
                    recurrence_end=data["recurrence_end"],
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
        event = item.data(Qt.ItemDataRole.UserRole)
        if event is None:
            return

        event_id = event["id"]
        occurrence_date = event.get("occurrence_date") or event.get("date")

        dialog = EventEditDialog(event, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            if dialog.requested_skip:
                result = self.engine.skip_occurrence(event_id, occurrence_date)
                self.show_result(f"건너뜀\n{result['title']} ({occurrence_date})")
            elif dialog.requested_delete:
                self.engine.delete_event(event_id)
                self.show_result(f"삭제됨\n{event['title']}")
            else:
                data = dialog.event_data()
                scope = data.pop("scope", "all")
                if scope == "occurrence":
                    result = self.engine.update_occurrence(event_id, occurrence_date, **data)
                else:
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
                repeat_text = recurrence_label(event.get("recurrence"))
                prefix = f"{event['time']} | "
                text = f"{prefix}{event['title']}"
                if repeat_text:
                    text = f"{text} ({repeat_text})"

            item = QListWidgetItem(text)
            item.setForeground(QBrush(QColor(event.get("color") or DEFAULT_EVENT_COLOR)))
            item.setData(Qt.ItemDataRole.UserRole, event)
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
