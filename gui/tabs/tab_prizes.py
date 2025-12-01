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
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.refresh()

    def compute(self):
        result = self.manager.compute_prizes()
        self.model.setDataFrame(result["payouts"])

    def refresh(self):
        df = self.manager.prize_service.prizes_repo.get_all_payouts()
        self.model.setDataFrame(df)
