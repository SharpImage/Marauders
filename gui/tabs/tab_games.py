# gui/tabs/tab_games.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QMessageBox, QComboBox, QLineEdit
)
from gui.dataframes import DataFrameModel


class GamesTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        layout.addWidget(QLabel("All Game Dates"))
        self.table_dates = QTableView()
        self.model_dates = DataFrameModel()
        self.table_dates.setModel(self.model_dates)

        # Scroll-friendly
        self.table_dates.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table_dates.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table_dates.horizontalHeader().setStretchLastSection(True)
        self.table_dates.verticalHeader().setVisible(False)

        layout.addWidget(self.table_dates)

        layout.addWidget(QLabel("Excluded Games"))
        self.table_excluded = QTableView()
        self.model_excluded = DataFrameModel()
        self.table_excluded.setModel(self.model_excluded)

        self.table_excluded.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table_excluded.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table_excluded.horizontalHeader().setStretchLastSection(True)
        self.table_excluded.verticalHeader().setVisible(False)

        layout.addWidget(self.table_excluded)

        control = QHBoxLayout()

        self.combo_dates = QComboBox()
        control.addWidget(self.combo_dates)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Reason for exclusion")
        control.addWidget(self.reason_edit)

        btn_add = QPushButton("Exclude Selected Game")
        btn_add.clicked.connect(self.exclude_game)
        control.addWidget(btn_add)

        btn_remove = QPushButton("Remove Selected Exclusion")
        btn_remove.clicked.connect(self.remove_exclusion)
        control.addWidget(btn_remove)

        layout.addLayout(control)

        self.setLayout(layout)
        self.refresh_all()

    def refresh_all(self):
        self.refresh_dates()
        self.refresh_excluded()
        self.refresh_comboboxes()

    def refresh_dates(self):
        dates = self.manager.game_repo.get_all_game_dates()
        df = DataFrameModel._build_dataframe(["GameDate"], dates)
        self.model_dates.setDataFrame(df)

    def refresh_excluded(self):
        df = self.manager.game_repo.get_excluded_games_table()
        self.model_excluded.setDataFrame(df)

    def refresh_comboboxes(self):
        self.combo_dates.clear()
        dates = self.manager.game_repo.get_all_game_dates()
        for d in dates:
            self.combo_dates.addItem(str(d))

    def exclude_game(self):
        d = self.combo_dates.currentText().strip()
        reason = self.reason_edit.text().strip()

        if not d:
            QMessageBox.warning(self, "Error", "No game date selected.")
            return

        if not reason:
            QMessageBox.warning(self, "Error", "A reason is required.")
            return

        self.manager.game_repo.add_excluded_game(d, reason)
        self.refresh_all()

    def remove_exclusion(self):
        d = self.combo_dates.currentText().strip()

        if not d:
            QMessageBox.warning(self, "Error", "No game date selected.")
            return

        self.manager.game_repo.remove_excluded_game(d)
        self.refresh_all()
