import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QDate, QPoint, Qt, QTime
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog

from ai_parser_gpt import parse
from calendar_engine import DEFAULT_EVENT_COLOR, RECURRENCE_NONE, CalendarEngine
from executor import execute
from holiday_updater import get_korean_holidays, save_holiday_cache
from korean_datetime_parser import lunar_to_solar
from ui_support import (
    EventEditDialog,
    ManualEventDialog,
    SettingsDialog,
    is_ai_confirmation_acceptance,
    is_ai_confirmation_rejection,
    qdate_to_storage_date,
)


class CalendarFeatureTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 1, 12, 0)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "events.json"
        self.engine = CalendarEngine(str(self.storage_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lunar_to_solar(self):
        self.assertEqual(lunar_to_solar(2026, 1, 1), date(2026, 2, 17))

    def test_parse_lunar_date(self):
        result = parse("2026년 음력 1월 1일 오후 3시 세배 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "세배")
        self.assertEqual(result["date"], "2026-02-17")
        self.assertEqual(result["time"], "15:00")

    def test_qdate_lunar_input_converts_to_solar_storage_date(self):
        self.assertEqual(
            qdate_to_storage_date(QDate(2026, 1, 1), use_lunar=True),
            "2026-02-17",
        )

    def test_ai_confirmation_reply_words(self):
        self.assertTrue(is_ai_confirmation_acceptance("실행"))
        self.assertTrue(is_ai_confirmation_acceptance("  OK  "))
        self.assertTrue(is_ai_confirmation_rejection("취소"))
        self.assertTrue(is_ai_confirmation_rejection("아니요"))
        self.assertFalse(is_ai_confirmation_acceptance("회의 추가해줘"))
        self.assertFalse(is_ai_confirmation_rejection("회의 추가해줘"))

    def test_direct_delete_from_event_editor(self):
        import main as main_module

        class FakeItem:
            def __init__(self, event):
                self.event = event

            def data(self, _role):
                return self.event

        class FakeDeleteDialog:
            requested_delete = True
            requested_skip = False

            def __init__(self, _event, _parent=None):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

        app = QApplication.instance() or QApplication([])
        original_start_holiday_update = main_module.CalendarWidget.start_holiday_update
        original_event_dialog = main_module.EventEditDialog
        main_module.CalendarWidget.start_holiday_update = lambda self, years=None: None
        main_module.EventEditDialog = FakeDeleteDialog

        try:
            widget = main_module.CalendarWidget()
            self.assertEqual(
                set(widget.resize_borders),
                {
                    "left",
                    "right",
                    "top",
                    "bottom",
                    "top_left",
                    "top_right",
                    "bottom_left",
                    "bottom_right",
                },
            )
            self.assertNotEqual(widget.minimumSize(), widget.maximumSize())

            start_size = widget.size()
            self.assertLess(widget.minimumWidth(), start_size.width())
            self.assertLess(widget.minimumHeight(), start_size.height())

            drag_start_size = widget.size()
            drag_handle = widget.resize_borders["bottom_right"]
            drag_start_pos = QPoint(drag_handle.width() - 2, drag_handle.height() - 2)
            drag_end_pos = drag_start_pos + QPoint(60, 35)
            QTest.mousePress(
                drag_handle,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                drag_start_pos,
            )
            QTest.mouseMove(drag_handle, drag_end_pos)
            QTest.mouseRelease(
                drag_handle,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                drag_end_pos,
            )
            self.assertGreater(widget.width(), drag_start_size.width())
            self.assertGreater(widget.height(), drag_start_size.height())

            before_direct_resize_size = widget.size()
            widget.resize_borders["bottom_right"].apply_resize_delta(80, 40)
            self.assertEqual(widget.width(), before_direct_resize_size.width() + 80)
            self.assertEqual(widget.height(), before_direct_resize_size.height() + 40)

            left_start_width = widget.width()
            widget.resize_borders["left"].apply_resize_delta(-30, 0)
            self.assertEqual(widget.width(), left_start_width + 30)

            top_start_height = widget.height()
            widget.resize_borders["top"].apply_resize_delta(0, -20)
            self.assertEqual(widget.height(), top_start_height + 20)

            widget.resize_borders["bottom_right"].apply_resize_delta(-10000, -10000)
            self.assertEqual(widget.width(), widget.minimumWidth())
            self.assertEqual(widget.height(), widget.minimumHeight())

            widget.engine = self.engine
            event = widget.engine.add_event("회의", "2026-05-01", "15:00")

            widget.open_event_editor(FakeItem(event))

            self.assertEqual(widget.engine.list_events("2026-05-01"), [])
            widget.close()
        finally:
            main_module.EventEditDialog = original_event_dialog
            main_module.CalendarWidget.start_holiday_update = original_start_holiday_update
            app.processEvents()

    def test_dialog_windows_are_not_resizable(self):
        app = QApplication.instance() or QApplication([])
        dialogs = [
            SettingsDialog(),
            ManualEventDialog(QDate(2026, 5, 1)),
            EventEditDialog(
                {
                    "type": "timed",
                    "title": "test",
                    "date": "2026-05-01",
                    "time": "09:00",
                    "duration": 60,
                    "color": DEFAULT_EVENT_COLOR,
                    "recurrence": RECURRENCE_NONE,
                    "recurrence_end": None,
                }
            ),
        ]

        try:
            for dialog in dialogs:
                self.assertEqual(dialog.minimumSize(), dialog.maximumSize())
                self.assertFalse(dialog.isSizeGripEnabled())
        finally:
            for dialog in dialogs:
                dialog.close()
            app.processEvents()

    def test_dialog_time_range_can_cross_midnight(self):
        app = QApplication.instance() or QApplication([])
        event = {
            "type": "timed",
            "title": "야간 작업",
            "date": "2026-05-01",
            "time": "23:30",
            "duration": 90,
            "color": DEFAULT_EVENT_COLOR,
            "recurrence": RECURRENCE_NONE,
            "recurrence_end": None,
        }
        dialogs = [
            ManualEventDialog(QDate(2026, 5, 1)),
            EventEditDialog(event),
        ]

        try:
            manual_dialog, edit_dialog = dialogs
            manual_dialog.title_input.setText("야간 작업")
            manual_dialog.start_time_input.setTime(QTime(23, 30))
            manual_dialog.end_time_input.setTime(QTime(1, 0))

            manual_data = manual_dialog.event_data()
            edit_data = edit_dialog.event_data()

            self.assertEqual(manual_data["duration"], 90)
            self.assertEqual(edit_dialog.end_time_input.time().toString("HH:mm"), "01:00")
            self.assertEqual(edit_data["duration"], 90)
        finally:
            for dialog in dialogs:
                dialog.close()
            app.processEvents()

    def test_korean_holidays(self):
        cache_path = Path(self.temp_dir.name) / "holiday_cache.json"
        save_holiday_cache(
            {
                "updated_at": "2026-05-19T21:30:00",
                "years": {
                    "2026": {
                        "2026-02-17": ["설날"],
                        "2026-05-24": ["부처님오신날"],
                        "2026-05-25": ["부처님오신날 대체공휴일"],
                        "2026-06-03": ["제9회 전국동시지방선거일"],
                    }
                },
            },
            str(cache_path),
        )

        holidays = get_korean_holidays(2026, cache_path=str(cache_path))

        self.assertIn("설날", holidays["2026-02-17"])
        self.assertIn("부처님오신날", holidays["2026-05-24"])
        self.assertIn("부처님오신날 대체공휴일", holidays["2026-05-25"])
        self.assertIn("제9회 전국동시지방선거일", holidays["2026-06-03"])

    def test_parse_indefinite_period(self):
        result = parse("오늘부터 무기한 시험기간 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add_period")
        self.assertEqual(result["title"], "시험기간")
        self.assertEqual(result["start_date"], "2026-05-01")
        self.assertIsNone(result["end_date"])

    def test_period_event_is_active_after_start_date(self):
        command = parse("오늘부터 무기한 시험기간 추가해줘", now=self.now)
        added = execute(command, self.engine)

        before = self.engine.list_events("2026-04-30")
        on_start = self.engine.list_events("2026-05-01")
        later = self.engine.list_events("2026-05-15")

        self.assertEqual(added["type"], "period")
        self.assertEqual(before, [])
        self.assertEqual(on_start[0]["title"], "시험기간")
        self.assertEqual(later[0]["title"], "시험기간")


if __name__ == "__main__":
    unittest.main()
