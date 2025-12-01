# gui/tabs/tab_games.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLineEdit,
    QLabel, QTableView, QMessageBox
)
from gui.dataframes import DataFrameModel


class GamesTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # ----------------------------------------------------------------------
        # GAME SELECTION + EXCLUDE/INCLUDE
        # ----------------------------------------------------------------------
        top_row = QHBoxLayout()

        self.cmb_dates = QComboBox()
        top_row.addWidget(QLabel("Select Game:"))
        top_row.addWidget(self.cmb_dates)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("Reason for exclusion (optional)")
        top_row.addWidget(self.txt_reason)

        btn_exclude = QPushButton("Exclude Game")
        btn_exclude.clicked.connect(self.exclude_game)
        top_row.addWidget(btn_exclude)

        btn_include = QPushButton("Include Game")
        btn_include.clicked.connect(self.include_game)
        top_row.addWidget(btn_include)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_all)
        top_row.addWidget(btn_refresh)

        layout.addLayout(top_row)

        # ----------------------------------------------------------------------
        # EXCLUDED GAMES TABLE
        # ----------------------------------------------------------------------
        layout.addWidget(QLabel("<b>Excluded Games:</b>"))
        self.table_excluded = QTableView()
        self.model_excluded = DataFrameModel()
        self.table_excluded.setModel(self.model_excluded)
        layout.addWidget(self.table_excluded)

        # ----------------------------------------------------------------------
        # GAME SUMMARY SECTION
        # ----------------------------------------------------------------------
        layout.addWidget(QLabel("<h3>Game Summary</h3>"))

        btn_summary = QPushButton("Load Summary for Selected Game")
        btn_summary.clicked.connect(self.show_summary)
        layout.addWidget(btn_summary)

        # SCORES TABLE
        layout.addWidget(QLabel("<b>Scores</b>"))
        self.table_scores = QTableView()
        self.model_scores = DataFrameModel()
        self.table_scores.setModel(self.model_scores)
        layout.addWidget(self.table_scores)

        # HANDICAP CHANGES TABLE
        layout.addWidget(QLabel("<b>Handicap Changes</b>"))
        self.table_hcaps = QTableView()
        self.model_hcaps = DataFrameModel()
        self.table_hcaps.setModel(self.model_hcaps)
        layout.addWidget(self.table_hcaps)

        # PRIZE PAYOUTS TABLE
        layout.addWidget(QLabel("<b>Prize Payouts</b>"))
        self.table_prizes = QTableView()
        self.model_prizes = DataFrameModel()
        self.table_prizes.setModel(self.model_prizes)
        layout.addWidget(self.table_prizes)

        self.setLayout(layout)

        # INITIAL LOAD
        self.refresh_all()

    # ----------------------------------------------------------------------
    # REFRESH FUNCTIONS
    # ----------------------------------------------------------------------
    def refresh_dates(self):
        dates = self.manager.get_all_game_dates()
        self.cmb_dates.clear()
        for d in dates:
            self.cmb_dates.addItem(str(d))

    def refresh_excluded(self):
        df = self.manager.get_excluded_games()
        self.model_excluded.setDataFrame(df)

    def refresh_all(self):
        self.refresh_dates()
        self.refresh_excluded()
        self.clear_summary()
        self.txt_reason.clear()

    # ----------------------------------------------------------------------
    # CLEAR SUMMARY TABLES
    # ----------------------------------------------------------------------
    def clear_summary(self):
        self.model_scores.setDataFrame(None)
        self.model_hcaps.setDataFrame(None)
        self.model_prizes.setDataFrame(None)

    # ----------------------------------------------------------------------
    # EXCLUDE GAME
    # ----------------------------------------------------------------------
    def exclude_game(self):
        date = self.cmb_dates.currentText()
        reason = self.txt_reason.text().strip()

        try:
            self.manager.exclude_game(date, reason)
            QMessageBox.information(self, "Game Excluded", f"{date} excluded.")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ----------------------------------------------------------------------
    # INCLUDE GAME
    # ----------------------------------------------------------------------
    def include_game(self):
        date = self.cmb_dates.currentText()

        try:
            self.manager.include_game(date)
            QMessageBox.information(self, "Game Included", f"{date} included.")
            self.refresh_all()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ----------------------------------------------------------------------
    # GAME SUMMARY
    # ----------------------------------------------------------------------
    def show_summary(self):
        date = self.cmb_dates.currentText()

        try:
            summary = self.manager.build_game_summary(date)

            self.model_scores.setDataFrame(summary["scores"])
            self.model_hcaps.setDataFrame(summary["handicaps"])
            self.model_prizes.setDataFrame(summary["prizes"])

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
