# gui/tabs/tab_players.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTableView
from gui.dataframes import DataFrameModel
from gui.dialogs.edit_player_dialog import EditPlayerDialog
from gui.dialogs.add_player_dialog import AddPlayerDialog


class PlayersTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        btn_add = QPushButton("Add Player")
        btn_add.clicked.connect(self.add_player)
        layout.addWidget(btn_add)

        btn_refresh = QPushButton("Refresh Players")
        btn_refresh.clicked.connect(self.refresh_players)
        layout.addWidget(btn_refresh)

        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)

        # Scroll-friendly
        self.table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        self.table.doubleClicked.connect(self.edit_player)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh_players()

    def add_player(self):
        dlg = AddPlayerDialog(self.manager, self)
        if dlg.exec():
            self.refresh_players()

    def edit_player(self, index):
        df = self.model.getDataFrame()
        player = df.iloc[index.row()]["Player"]
        dlg = EditPlayerDialog(self.manager, player, self)
        if dlg.exec():
            self.refresh_players()

    def refresh_players(self):
        df = self.manager.player_service.build_player_status_table()
        self.model.setDataFrame(df)
