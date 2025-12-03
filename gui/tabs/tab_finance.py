# gui/tabs/tab_finance.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableView, QLabel
from gui.dataframes import DataFrameModel
from gui.dialogs.add_transaction_dialog import AddTransactionDialog


class FinanceTab(QWidget):
    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout()

        btn_rebuild = QPushButton("Rebuild Finance")
        btn_rebuild.clicked.connect(self.rebuild)
        layout.addWidget(btn_rebuild)

        btn_add = QPushButton("Add Transaction")
        btn_add.clicked.connect(self.add_transaction)
        layout.addWidget(btn_add)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

        self.lbl_summary = QLabel("Kitty:")
        layout.addWidget(self.lbl_summary)

        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)

        # Scroll-friendly
        self.table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh()

    def add_transaction(self):
        dlg = AddTransactionDialog(self.manager, self)
        if dlg.exec():
            self.refresh()

    def rebuild(self):
        result = self.manager.rebuild_finance()
        self.model.setDataFrame(result.ledger)
        self.lbl_summary.setText(f"Kitty: £{result.kitty_total:.2f}")

    def refresh(self):
        result = self.manager.rebuild_finance()
        self.model.setDataFrame(result.ledger)
        self.lbl_summary.setText(f"Kitty: £{result.kitty_total:.2f}")
