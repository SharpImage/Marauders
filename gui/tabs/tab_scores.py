# gui/tabs/tab_scores.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableView
from gui.dataframes import DataFrameModel


class ScoresTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        btn_refresh = QPushButton("Refresh Scores")
        btn_refresh.clicked.connect(self.refresh_scores)
        layout.addWidget(btn_refresh)

        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        self.setLayout(layout)

        # Auto-load
        self.refresh_scores()

    def refresh_scores(self):
        df = self.manager.scores_repo.get_all()
        self.model.setDataFrame(df)
