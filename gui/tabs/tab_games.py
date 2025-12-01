# gui/tabs/tab_games.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QMessageBox, QDateEdit, QLineEdit
)
from PySide6.QtCore import Qt, QDate

from gui.dataframes import DataFrameModel


class GamesTab(QWidget):
    """
    GUI tab for viewing game dates and managing excluded games.
    """

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # -------------------------------------------------------------
        # GAME DATES TABLE
        # -------------------------------------------------------------
        layout.addWidget(QLabel("All Game Dates"))
        self.table_dates = QTableView()
        self.model_dates = DataFrameModel()
        self.table_dates.setModel(self.model_dates)
        layout.addWidget(self.table_dates)

        # -------------------------------------------------------------
        # EXCLUDED GAMES TABLE
        # -------------------------------------------------------------
        layout.addWidget(QLabel("Excluded Games"))
        self.table_excluded = QTableView()
        self.model_excluded = DataFrameModel()
        self.table_excluded.setModel(self.model_excluded)
        layout.addWidget(self.table_excluded)

        # -------------------------------------------------------------
        # CONTROLS
        # -------------------------------------------------------------
        control_layout = QHBoxLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        control_layout.addWidget(self.date_edit)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Reason for exclusion")
        control_layout.addWidget(self.reason_edit)

        btn_add = QPushButton("Exclude Game")
        btn_add.clicked.connect(self.exclude_game)
        control_layout.addWidget(btn_add)

        btn_remove = QPushButton("Remove Exclusion")
        btn_remove.clicked.connect(self.remove_exclusion)
        control_layout.addWidget(btn_remove)

        layout.addLayout(control_layout)

        self.setLayout(layout)

        # Initial load
        self.refresh_all()

    # ------------------------------------------------------------------
    def refresh_all(self):
        self.refresh_dates()
        self.refresh_excluded()

    # ------------------------------------------------------------------
    def refresh_dates(self):
        dates = self.manager.game_repo.get_all_game_dates()
        df = None
        if dates:
            df = DataFrameModel._build_dataframe(["GameDate"], dates)
        else:
            df = DataFrameModel._build_dataframe(["GameDate"], [])

        self.model_dates.setDataFrame(df)

    # ------------------------------------------------------------------
    def refresh_excluded(self):
        df = self.manager.game_repo.get_excluded_games_table()
        self.model_excluded.setDataFrame(df)

    # ------------------------------------------------------------------
    def exclude_game(self):
        game_date = self.date_edit.date().toPython()
        reason = self.reason_edit.text().strip()

        if not reason:
            QMessageBox.warning(self, "Error", "Reason must be provided.")
            return

        try:
            self.manager.game_repo.add_excluded_game(game_date, reason)
            QMessageBox.information(self, "Success", "Game excluded.")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------------------------------------------------------
    def remove_exclusion(self):
        game_date = self.date_edit.date().toPython()

        try:
            self.manager.game_repo.remove_excluded_game(game_date)
            QMessageBox.information(self, "Success", "Exclusion removed.")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
