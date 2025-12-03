# gui/tabs/tab_prizes.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableView
from gui.dataframes import DataFrameModel


class PrizesTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        btn_compute = QPushButton("Compute Prizes")
        btn_compute.clicked.connect(self.compute)
        layout.addWidget(btn_compute)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)

        # Scroll-friendly improvements
        self.table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh()

    # ------------------------------------------------------------------
    def compute(self):
        """Recompute all prize payouts and refresh the table."""
        result = self.manager.prize_service.compute_all_prizes()
        df = result["payouts"]
        self.model.setDataFrame(df)

    # ------------------------------------------------------------------
    def refresh(self):
        """Refresh by recomputing in-memory results."""
        result = self.manager.prize_service.compute_all_prizes()
        df = result["payouts"]
        self.model.setDataFrame(df)
