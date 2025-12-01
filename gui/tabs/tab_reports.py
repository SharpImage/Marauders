from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QMessageBox
)
from datetime import date


class ReportsTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # ---------------------------------------------------
        # Report type selector
        # ---------------------------------------------------
        self.cmb_type = QComboBox()
        self.cmb_type.addItems([
            "Game Report",
            "Current Handicaps",
            "Balances Report"
        ])
        self.cmb_type.currentIndexChanged.connect(self._toggle_date_selector)
        layout.addWidget(QLabel("Choose Report Type:"))
        layout.addWidget(self.cmb_type)

        # ---------------------------------------------------
        # Game date selector (only used for game report)
        # ---------------------------------------------------
        self.cmb_date = QComboBox()
        layout.addWidget(QLabel("Choose Game Date:"))
        layout.addWidget(self.cmb_date)

        self._load_dates()
        self._toggle_date_selector()

        # ---------------------------------------------------
        # Buttons
        # ---------------------------------------------------
        btn_layout = QHBoxLayout()

        btn_generate = QPushButton("Generate Report")
        btn_generate.clicked.connect(self.generate_report)
        btn_layout.addWidget(btn_generate)

        # Email button (future)
        # btn_email = QPushButton("Email Report")
        # btn_email.clicked.connect(self.email_report)
        # btn_layout.addWidget(btn_email)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # ---------------------------------------------------
    def _load_dates(self):
        dates = self.manager.scores_repo.get_game_dates()
        self.cmb_date.clear()
        for d in dates:
            self.cmb_date.addItem(str(d))

    # ---------------------------------------------------
    def _toggle_date_selector(self):
        """Enable date dropdown only for Game Report."""
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
