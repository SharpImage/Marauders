# gui/tabs/tab_transactions.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableView, QLabel, QMessageBox
)
from gui.dataframes import DataFrameModel
from gui.dialogs.add_transaction_dialog import AddTransactionDialog
from gui.dialogs.edit_transaction_dialog import EditTransactionDialog
import pandas as pd


class TransactionsTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # Instruction
        lbl = QLabel("Double-click a transaction to edit it.")
        layout.addWidget(lbl)

        # Buttons
        btn_row = QHBoxLayout()

        btn_add = QPushButton("Add Transaction")
        btn_add.clicked.connect(self.add_transaction)
        btn_row.addWidget(btn_add)

        btn_edit = QPushButton("Edit Selected")
        btn_edit.clicked.connect(self.edit_selected_transaction)
        btn_row.addWidget(btn_edit)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        btn_row.addWidget(btn_refresh)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Table
        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)

        self.table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        # Double-click to edit
        self.table.doubleClicked.connect(self.edit_transaction_from_index)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh()

    # ---------------------------------------------------
    def _load_transactions(self) -> pd.DataFrame:
        """Load transactions from the repository."""
        df = self.manager.finance_service.finance_repo.get_player_transactions().copy()
        if not df.empty:
            # Normalise date for display
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
        return df

    # ---------------------------------------------------
    def refresh(self):
        df = self._load_transactions()
        self.model.setDataFrame(df)

        # Hide internal TransactionID column if present
        if not df.empty and "TransactionID" in df.columns:
            idx = df.columns.get_loc("TransactionID")
            self.table.setColumnHidden(idx, True)

    # ---------------------------------------------------
    def add_transaction(self):
        dlg = AddTransactionDialog(self.manager, self)
        if dlg.exec():
            self.refresh()
            self.refresh_finance_tab()

    # ---------------------------------------------------
    def edit_selected_transaction(self):
        index = self.table.currentIndex()
        if not index.isValid():
            QMessageBox.information(
                self, "No Selection", "Please select a transaction to edit."
            )
            return
        self._edit_by_index(index)

    def edit_transaction_from_index(self, index):
        """Slot for table double-click."""
        if index.isValid():
            self._edit_by_index(index)

    def _edit_by_index(self, index):
        df = self.model.getDataFrame()
        if df is None or df.empty:
            return

        row = df.iloc[index.row()]
        if "TransactionID" not in row:
            QMessageBox.warning(
                self,
                "Missing ID",
                "This transaction cannot be edited because it has no TransactionID.",
            )
            return

        dlg = EditTransactionDialog(self.manager, row, self)

        if dlg.exec():
            self.refresh()
            self.refresh_finance_tab()

    def refresh_finance_tab(self):
        """Refresh FinanceTab if present in the main window."""
        win = self.window()
        if hasattr(win, "tab_finance"):
            try:
                win.tab_finance.widget().refresh()
            except Exception:
                pass

