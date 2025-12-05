from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QMessageBox, QSizePolicy
)
from datetime import date
import pandas as pd  # needed because _load_dates uses pd.to_datetime


class ReportsTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # ---------------------------------------------------
        # Report type selector (Label + Combo Box together)
        # ---------------------------------------------------
        type_layout = QHBoxLayout()
        lbl_type = QLabel("Choose Report Type:")
        self.cmb_type = QComboBox()

        # Limit dropdown width so arrow stays close
        self.cmb_type.setMaximumWidth(220)
        self.cmb_type.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.cmb_type.addItems([
            "Game Report",
            "Current Handicaps",
            "Balances Report"
        ])
        self.cmb_type.currentIndexChanged.connect(self._toggle_date_selector)

        type_layout.addWidget(lbl_type)
        type_layout.addWidget(self.cmb_type)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # ---------------------------------------------------
        # Game date selector (Label + Combo Box together)
        # ---------------------------------------------------
        date_layout = QHBoxLayout()
        lbl_date = QLabel("Choose Game Date:")
        self.cmb_date = QComboBox()

        self.cmb_date.setMaximumWidth(220)
        self.cmb_date.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        date_layout.addWidget(lbl_date)
        date_layout.addWidget(self.cmb_date)
        date_layout.addStretch()
        layout.addLayout(date_layout)

        # Load available game dates
        self._load_dates()
        self._toggle_date_selector()

        # ---------------------------------------------------
        # Buttons
        # ---------------------------------------------------
        btn_layout = QHBoxLayout()

        btn_generate = QPushButton("Generate Report")
        btn_layout.addWidget(btn_generate)
        btn_layout.addStretch()
        btn_generate.clicked.connect(self.generate_report)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    # ---------------------------------------------------
    def _load_dates(self):
        dates = self.manager.scores_repo.get_game_dates()

        try:
            dates_sorted = sorted(
                [pd.to_datetime(d).date() for d in dates],
                reverse=True
            )
        except Exception:
            dates_sorted = sorted(dates, reverse=True)

        self.cmb_date.clear()
        for d in dates_sorted:
            self.cmb_date.addItem(str(d))

    # ---------------------------------------------------
    def _toggle_date_selector(self):
        selected = self.cmb_type.currentText()
        self.cmb_date.setEnabled(selected == "Game Report")

    # ---------------------------------------------------
    def generate_report(self):
        report_type = self.cmb_type.currentText()

        if report_type == "Game Report":
            date_text = self.cmb_date.currentText()
            if not date_text:
                QMessageBox.warning(self, "No Date", "Please select a game date.")
                return

            game_date = date.fromisoformat(date_text)
            html = self.manager.build_game_report_html(game_date)
            filename = f"game_report_{game_date}.html"

        elif report_type == "Current Handicaps":
            html = self.manager.build_handicap_report_html()
            filename = "current_handicaps_report.html"

        elif report_type == "Balances Report":
            html = self.manager.build_balances_report_html()
            filename = "player_balances_report.html"

        else:
            QMessageBox.warning(self, "Unknown Report", "Unsupported report type.")
            return

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "Report Saved", f"Report written to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error Writing File", str(e))
