#UI스타일 시트 중 매우 긴 스타일 시트를 걍 따로 빼놓은 파일
def main_style_sheet():
    return """
            QWidget {
                background-color: #101114;
                color: #F2F4F8;
                font-family: Malgun Gothic;
                font-size: 13px;
                letter-spacing: 0px;
            }

            QWidget#body {
                background-color: #101114;
            }

            QWidget#resizeBorder {
                background-color: transparent;
                border: 0;
            }

            QFrame#aiSlot {
                background-color: transparent;
                border: 0;
            }

            QFrame#titleBar {
                background-color: #20252D;
                border-bottom: 1px solid #303644;
            }

            QLabel#windowTitle {
                background-color: transparent;
                color: #E8EDF5;
                font-size: 12px;
                font-weight: 500;
            }

            QPushButton#windowCloseButton {
                background-color: #9D3B3B;
                border: 0;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }

            QPushButton#windowCloseButton:hover {
                background-color: #C94B4B;
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

            QFrame#statusRail {
                background-color: transparent;
                border: 0;
            }

            QPushButton#connectionStatusIcon,
            QPushButton#aiToggleIcon {
                background-color: #111318;
                border: 1px solid #8B95A7;
                border-radius: 6px;
                color: #DDE3EE;
                font-size: 8px;
                font-weight: 700;
                padding: 0;
            }

            QPushButton#connectionStatusIcon:hover,
            QPushButton#aiToggleIcon:hover {
                background-color: #20242C;
            }

            QPushButton#aiToggleIcon {
                border-color: #343B47;
                color: #AEB7C6;
                border-radius: 6px;
                font-size: 16px;
            }

            QPushButton#aiToggleIcon[collapsed="true"] {
                border-color: #2F6FED;
                color: #8CB2FF;
            }

            QPushButton#connectionStatusIcon[state="ok"] {
                border-color: #2DBE78;
                color: #2DBE78;
            }

            QPushButton#connectionStatusIcon[state="warning"] {
                border-color: #F59F00;
                color: #F59F00;
            }

            QPushButton#connectionStatusIcon[state="checking"] {
                border-color: #15AABF;
                color: #15AABF;
            }

            QToolTip {
                background-color: #111318;
                border: 1px solid #343B47;
                border-radius: 6px;
                color: #F2F4F8;
                padding: 8px;
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
