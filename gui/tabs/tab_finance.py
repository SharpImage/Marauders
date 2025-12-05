# gui/tabs/tab_finance.py

import datetime
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QDateEdit, QFileDialog
)
from PySide6.QtCore import Qt, QDate


class FinanceTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self._full_ledger = pd.DataFrame()

        layout = QVBoxLayout()

        # -------------------------------------------------------
        # Filters
        # -------------------------------------------------------
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Player:"))
        self.cmb_player = QComboBox()
        self.cmb_player.currentIndexChanged.connect(self.apply_filters)
        filters.addWidget(self.cmb_player)

        filters.addWidget(QLabel("From:"))
        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.dateChanged.connect(self.apply_filters)
        filters.addWidget(self.date_from)

        filters.addWidget(QLabel("To:"))
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.dateChanged.connect(self.apply_filters)
        filters.addWidget(self.date_to)

        filters.addStretch()
        layout.addLayout(filters)

        # Summary
        self.lbl_summary = QLabel("Kitty: £0.00")
        layout.addWidget(self.lbl_summary)

        # Table
        self.table = QTableWidget()
        layout.addWidget(self.table)

        # Buttons
        buttons = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        buttons.addWidget(btn_refresh)

        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self.export_csv)
        buttons.addWidget(btn_export)

        buttons.addStretch()
        layout.addLayout(buttons)

        self.setLayout(layout)

        self.refresh()

    # ======================================================================
    # Refresh ledger
    # ======================================================================
    def refresh(self):
        result = self.manager.rebuild_finance()
        self._load_ledger(result)
        self.apply_filters()

    def _load_ledger(self, result):
        df = result.ledger.copy()

        df["Date"] = df["Date"].apply(self._normalize_date)

        self._full_ledger = df
        self.lbl_summary.setText(f"Kitty: £{result.kitty_total:.2f}")

        # Determine filter boundaries
        valid_dates = df["Date"].dropna()
        valid_dates = valid_dates[valid_dates.apply(lambda d: isinstance(d, datetime.date))]

        if len(valid_dates) > 0:
            earliest = min(valid_dates)
            latest = max(valid_dates)
            self.date_from.setDate(QDate(earliest.year, earliest.month, earliest.day))
            self.date_to.setDate(QDate(latest.year, latest.month, latest.day))

        # Populate players
        players = sorted(df["Player"].dropna().unique().tolist())
        self.cmb_player.blockSignals(True)
        self.cmb_player.clear()
        self.cmb_player.addItem("All Players")
        self.cmb_player.addItems(players)
        self.cmb_player.blockSignals(False)

    # ======================================================================
    # Normalize date output
    # ======================================================================
    def _normalize_date(self, val):
        """Convert any possible value into a datetime.date or None."""
        # None or NaT
        if val is None or pd.isna(val):
            return None

        # Timestamp
        if isinstance(val, pd.Timestamp):
            try:
                return val.date()
            except Exception:
                return None

        # Python date
        if isinstance(val, datetime.date):
            return val

        # String date
        if isinstance(val, str):
            try:
                return datetime.date.fromisoformat(val)
            except Exception:
                return None

        return None

    # ======================================================================
    # Apply filters safely
    # ======================================================================
    def apply_filters(self):
        if self._full_ledger.empty:
            return

        df = self._full_ledger.copy()

        # Player filter
        player = self.cmb_player.currentText()
        if player != "All Players":
            df = df[df["Player"] == player]

        # Date filter
        from_date = self.date_from.date().toPython()
        to_date = self.date_to.date().toPython()

        def is_in_range(d):
            """Safely check if a date is in range, handling NaT and None."""
            if d is None or pd.isna(d):
                return True

            # Timestamp -> date
            if isinstance(d, pd.Timestamp):
                try:
                    d = d.date()
                except Exception:
                    return True

            # String -> attempt parse
            if isinstance(d, str):
                try:
                    d = datetime.date.fromisoformat(d)
                except Exception:
                    return True

            if isinstance(d, datetime.date):
                return from_date <= d <= to_date

            return True

        df = df[df["Date"].apply(is_in_range)]

        self._display_table(df)

    # ======================================================================
    # Display table
    # ======================================================================
    def _display_table(self, df):
        self.table.clear()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)

        for r, (_, row) in enumerate(df.iterrows()):
            for c, value in enumerate(row):
                text = "" if pd.isna(value) else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(r, c, item)

        self.table.resizeColumnsToContents()

    # ======================================================================
    # CSV Export
    # ======================================================================
    def export_csv(self):
        df = self._get_filtered_dataframe()
        if df.empty:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Finance CSV", "finance_ledger.csv", "CSV Files (*.csv)"
        )

        if filename:
            df.to_csv(filename, index=False)

    def _get_filtered_dataframe(self):
        """Return filtered ledger for CSV export."""
        df = self._full_ledger.copy()

        player = self.cmb_player.currentText()
        if player != "All Players":
            df = df[df["Player"] == player]

        from_date = self.date_from.date().toPython()
        to_date = self.date_to.date().toPython()

        def is_in_range(d):
            if d is None or pd.isna(d):
                return True

            if isinstance(d, pd.Timestamp):
                d = d.date()

            if isinstance(d, str):
                try:
                    d = datetime.date.fromisoformat(d)
                except Exception:
                    return True

            if isinstance(d, datetime.date):
                return from_date <= d <= to_date

            return True

        df = df[df["Date"].apply(is_in_range)]
        return df
