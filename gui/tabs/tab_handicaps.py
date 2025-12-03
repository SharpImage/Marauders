# gui/tabs/tab_handicaps.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableView, QMessageBox
from gui.dataframes import DataFrameModel


class HandicapsTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        btn_rebuild = QPushButton("Rebuild Handicaps")
        btn_rebuild.clicked.connect(self.rebuild)
        layout.addWidget(btn_rebuild)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        layout.addWidget(btn_refresh)

        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)

        # Scroll-friendly settings
        self.table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh()

    def rebuild(self):
        try:
            self.manager.rebuild_handicaps()
            QMessageBox.information(self, "OK", "Handicaps rebuilt.")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def refresh(self):
        try:
            df = self.manager.handicap_service.get_current_handicaps()
            self.model.setDataFrame(df)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", str(e))
