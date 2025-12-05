# gui/tabs/tab_games.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from datetime import date


class GamesTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # Title
        title = QLabel("Manage Game Dates")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)

        # Dates list
        self.lst_dates = QListWidget()
        layout.addWidget(self.lst_dates)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("Add Game Date")
        btn_add.clicked.connect(self.add_game_date)
        btn_layout.addWidget(btn_add)

        btn_exclude = QPushButton("Exclude Selected")
        btn_exclude.clicked.connect(self.exclude_selected)
        btn_layout.addWidget(btn_exclude)

        btn_include = QPushButton("Include Selected")
        btn_include.clicked.connect(self.include_selected)
        btn_layout.addWidget(btn_include)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Initial load
        self.refresh_dates()

    # -------------------------------------------------------
    # Refresh list
    # -------------------------------------------------------
    def refresh_dates(self):
        """Load all game dates and mark excluded ones."""
        self.lst_dates.clear()

        # FIX: correct repo name
        all_dates = self.manager.games_repo.get_all_game_dates()
        excluded = set(self.manager.games_repo.get_excluded_game_dates())

        for d in all_dates:
            text = str(d)
            item = QListWidgetItem(text)

            if d in excluded:
                item.setForeground(Qt.red)
                item.setText(f"{text}   (Excluded)")

            self.lst_dates.addItem(item)

    # -------------------------------------------------------
    # Helpers
    # -------------------------------------------------------
    def _get_selected_date(self):
        item = self.lst_dates.currentItem()
        if not item:
            return None

        text = item.text().replace("(Excluded)", "").strip()

        try:
            return date.fromisoformat(text)
        except Exception:
            return None

    # -------------------------------------------------------
    # Add new date
    # -------------------------------------------------------
    def add_game_date(self):
        """Popup date picker and add a game date."""
        picker = QDateEdit()
        picker.setCalendarPopup(True)
        picker.setDate(QDate.currentDate())

        msg = QMessageBox(self)
        msg.setWindowTitle("Add Game Date")
        msg.setText("Select the game date, then click OK.")
        msg.layout().addWidget(picker)
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        if msg.exec() == QMessageBox.Ok:
            py_date = picker.date().toPython()

            # not excluded by default
            self.manager.games_repo.add_game_date(py_date)
            self.refresh_dates()

    # -------------------------------------------------------
    # Exclude date
    # -------------------------------------------------------
    def exclude_selected(self):
        d = self._get_selected_date()
        if not d:
            QMessageBox.warning(self, "No Selection", "Please select a date to exclude.")
            return

        self.manager.games_repo.exclude_game_date(d)
        self.refresh_dates()

    # -------------------------------------------------------
    # Include date
    # -------------------------------------------------------
    def include_selected(self):
        d = self._get_selected_date()
        if not d:
            QMessageBox.warning(self, "No Selection", "Please select a date to include.")
            return

        self.manager.games_repo.include_game_date(d)
        self.refresh_dates()
