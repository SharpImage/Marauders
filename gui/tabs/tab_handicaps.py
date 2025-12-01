# gui/tabs/tab_handicaps.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableView
from gui.dataframes import DataFrameModel


class HandicapsTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        btn = QPushButton("Rebuild Handicaps")
        btn.clicked.connect(self.rebuild)
        layout.addWidget(btn)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.refresh()

    def rebuild(self):
        result = self.manager.rebuild_handicaps()
        self.model.setDataFrame(result["current"])

    def refresh(self):
        df = self.manager.handicap_service.get_current_handicaps()
        self.model.setDataFrame(df)
