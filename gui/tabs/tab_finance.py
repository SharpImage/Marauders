from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableView, QLabel,
    QHBoxLayout, QComboBox, QLineEdit, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QGuiApplication

from gui.dataframes import DataFrameModel
from gui.dialogs.add_transaction_dialog import AddTransactionDialog


class FinanceTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # ===========================================================
        # FILTER BAR
        # ===========================================================
        filter_row = QHBoxLayout()

        # Player filter
        self.cbo_player = QComboBox()
        self.cbo_player.addItem("All Players")
        filter_row.addWidget(self.cbo_player)

        # Date from
        self.date_from = QDateEdit()
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate(2025, 1, 1))
        filter_row.addWidget(self.date_from)

        # Date to
        self.date_to = QDateEdit()
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        filter_row.addWidget(self.date_to)

        # Description filter
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Search description...")
        filter_row.addWidget(self.txt_desc)

        # Clear Filters
        btn_clear = QPushButton("Clear Filters")
        btn_clear.clicked.connect(self.clear_filters)
        filter_row.addWidget(btn_clear)

        layout.addLayout(filter_row)

        # ===========================================================
        # ACTION BUTTONS
        # ===========================================================
        button_row = QHBoxLayout()

        btn_rebuild = QPushButton("Rebuild Finance")
        btn_rebuild.clicked.connect(self.rebuild)
        button_row.addWidget(btn_rebuild)

        btn_add = QPushButton("Add Transaction")
        btn_add.clicked.connect(self.add_transaction)
        button_row.addWidget(btn_add)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        button_row.addWidget(btn_refresh)

        btn_copy = QPushButton("Copy Ledger to Clipboard")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        button_row.addWidget(btn_copy)

        layout.addLayout(button_row)

        # ===========================================================
        # SUMMARY LABEL
        # ===========================================================
        self.lbl_summary = QLabel("Summary will appear here.")
        self.lbl_summary.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.lbl_summary)

        # ===========================================================
        # TABLE VIEW
        # ===========================================================
        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        self.setLayout(layout)

        # Initial load
        self.refresh()

        # Hook up live filter triggers
        self.cbo_player.currentIndexChanged.connect(self.apply_filters)
        self.date_from.dateChanged.connect(self.apply_filters)
        self.date_to.dateChanged.connect(self.apply_filters)
        self.txt_desc.textChanged.connect(self.apply_filters)

    # -----------------------------------------------------------
    def add_transaction(self):
        dlg = AddTransactionDialog(self.manager, self)
        if dlg.exec():
            self.refresh()

    # -----------------------------------------------------------
    def rebuild(self):
        result = self.manager.rebuild_finance()
        self.full_ledger = result.ledger.copy()
        self.current_result = result
        self.update_player_list()
        self.apply_filters()

    # -----------------------------------------------------------
    def refresh(self):
        result = self.manager.rebuild_finance()
        self.full_ledger = result.ledger.copy()
        self.current_result = result
        self.update_player_list()
        self.apply_filters()

    # -----------------------------------------------------------
    def update_player_list(self):
        """Populate player dropdown."""
        self.cbo_player.clear()
        self.cbo_player.addItem("All Players")
        players = sorted(self.full_ledger["Player"].dropna().unique())
        for p in players:
            self.cbo_player.addItem(p)

    # -----------------------------------------------------------
    def apply_filters(self):
        """Apply Player, Date, and Description filters."""
        df = self.full_ledger.copy()

        # Filter by player
        sel_player = self.cbo_player.currentText()
        if sel_player != "All Players":
            df = df[df["Player"] == sel_player]

        # Filter by date range
        d_from = self.date_from.date().toPython()
        d_to = self.date_to.date().toPython()
        df = df[(df["Date"] >= d_from) & (df["Date"] <= d_to)]

        # Filter by description
        search = self.txt_desc.text().strip().lower()
        if search:
            df = df[df["Description"].fillna("").str.lower().str.contains(search)]

        # Format currency columns
        df_disp = df.copy()
        for col in ["Game Fee", "Prizes", "Other", "Net", "Balance"]:
            if col in df_disp.columns:
                df_disp[col] = df_disp[col].map(lambda x: f"£{x:,.2f}")

        self.model.setDataFrame(df_disp)
        self.update_summary(self.current_result)

    # -----------------------------------------------------------
    def clear_filters(self):
        self.cbo_player.setCurrentIndex(0)
        self.date_from.setDate(QDate(2025, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.txt_desc.clear()
        self.apply_filters()

    # -----------------------------------------------------------
    def update_summary(self, result):
        gs = result.game_summary

        total_fees = gs["GameFees"].sum()
        total_prizes = gs["PrizeToPlayers"].sum()
        surplus = gs["Surplus"].sum()

        summary_text = (
            f"<b>Kitty: £{result.kitty_total:,.2f}</b><br>"
            f"Included Games: {len(gs)}<br>"
            f"Total Game Fees: £{total_fees:,.2f}<br>"
            f"Total Prizes: £{total_prizes:,.2f}<br>"
            f"Surplus: £{surplus:,.2f}<br>"
        )
        self.lbl_summary.setText(summary_text)

    # -----------------------------------------------------------
    def copy_to_clipboard(self):
        df = self.model.dataFrame()
        if df is None or df.empty:
            return
        text = df.to_csv(sep="\t", index=False)
        QGuiApplication.clipboard().setText(text)
