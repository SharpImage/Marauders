# gui/tabs/tab_players.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableView, QCheckBox
)
from gui.dataframes import DataFrameModel
from gui.dialogs.edit_player_dialog import EditPlayerDialog
from gui.dialogs.add_player_dialog import AddPlayerDialog


class PlayersTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # ---------------------------------------------------
        # Instruction label
        # ---------------------------------------------------
        lbl = QLabel("Double-click a player to edit their details.")
        layout.addWidget(lbl)

        # ---------------------------------------------------
        # Add + Refresh buttons
        # ---------------------------------------------------
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("Add Player")
        btn_add.clicked.connect(self.add_player)
        btn_layout.addWidget(btn_add)

        btn_refresh = QPushButton("Refresh Players")
        btn_refresh.clicked.connect(self.refresh_players)
        btn_layout.addWidget(btn_refresh)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ---------------------------------------------------
        # Active-only checkbox
        # ---------------------------------------------------
        self.chk_active_only = QCheckBox("Show only active players")
        self.chk_active_only.stateChanged.connect(self.refresh_players)
        layout.addWidget(self.chk_active_only)

        # ---------------------------------------------------
        # Table
        # ---------------------------------------------------
        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)

        self.table.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableView.ScrollPerPixel)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        self.table.doubleClicked.connect(self.edit_player)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.refresh_players()

    # ---------------------------------------------------
    def add_player(self):
        dlg = AddPlayerDialog(self.manager, self)
        if dlg.exec():
            self.refresh_players()

    # ---------------------------------------------------
    def edit_player(self, index):
        df = self.model.getDataFrame()
        player_name = df.iloc[index.row()]["Player"]
        dlg = EditPlayerDialog(self.manager, player_name, self)
        if dlg.exec():
            self.refresh_players()

    # ---------------------------------------------------
    def refresh_players(self):
        show_active_only = self.chk_active_only.isChecked()

        df = self.manager.player_service.build_player_status_table(
            include_inactive=not show_active_only
        )

        self.model.setDataFrame(df)
