# gui/tabs/tab_games.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QMessageBox, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt

from gui.dataframes import DataFrameModel


class GamesTab(QWidget):
    """
    GUI tab for viewing game dates and managing excluded games.
    Restores the original stable behaviour using combo boxes
    instead of QDateEdit, to ensure consistent ISO string matching.
    """

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # -------------------------------------------------------------
        # ALL GAME DATES TABLE
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
        # CONTROLS (Restored original working behaviour)
        # -------------------------------------------------------------
        control_layout = QHBoxLayout()

        # DROP-DOWN: Select game date to exclude
        self.combo_dates = QComboBox()
        control_layout.addWidget(self.combo_dates)

        # ENTER REASON
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Reason for exclusion")
        control_layout.addWidget(self.reason_edit)

        # BUTTON: Add exclusion
        btn_add = QPushButton("Exclude Selected Game")
        btn_add.clicked.connect(self.exclude_game)
        control_layout.addWidget(btn_add)

        # BUTTON: Remove exclusion
        btn_remove = QPushButton("Remove Selected Exclusion")
        btn_remove.clicked.connect(self.remove_exclusion)
        control_layout.addWidget(btn_remove)

        layout.addLayout(control_layout)
        self.setLayout(layout)

        # Initial refresh
        self.refresh_all()

    # ------------------------------------------------------------------
    def refresh_all(self):
        self.refresh_dates()
        self.refresh_excluded()
        self.refresh_comboboxes()

    # ------------------------------------------------------------------
    def refresh_dates(self):
        dates = self.manager.game_repo.get_all_game_dates()
        df = DataFrameModel._build_dataframe(["GameDate"], dates)
        self.model_dates.setDataFrame(df)

    # ------------------------------------------------------------------
    def refresh_excluded(self):
        df = self.manager.game_repo.get_excluded_games_table()
        self.model_excluded.setDataFrame(df)

    # ------------------------------------------------------------------
    def refresh_comboboxes(self):
        """Refresh the dropdowns for selecting dates."""
        self.combo_dates.clear()

        # Load available game dates
        all_dates = self.manager.game_repo.get_all_game_dates()

        # Convert to strings
        all_dates = [str(d) for d in all_dates]

        # Populate dropdown
        for d in all_dates:
            self.combo_dates.addItem(d)

    # ------------------------------------------------------------------
    def exclude_game(self):
        game_date = self.combo_dates.currentText().strip()
        reason = self.reason_edit.text().strip()

        if not game_date:
            QMessageBox.warning(self, "Error", "No game date selected.")
            return

        if not reason:
            QMessageBox.warning(self, "Error", "A reason is required.")
            return

        try:
            self.manager.game_repo.add_excluded_game(game_date, reason)
            QMessageBox.information(self, "Success", f"Excluded {game_date}")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ------------------------------------------------------------------
    def remove_exclusion(self):
        """Remove exclusion for the currently selected game date in the combo box."""
        game_date = self.combo_dates.currentText().strip()

        if not game_date:
            QMessageBox.warning(self, "Error", "No game date selected.")
            return

        try:
            self.manager.game_repo.remove_excluded_game(game_date)
            QMessageBox.information(self, "Success", f"Exclusion removed for {game_date}")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
