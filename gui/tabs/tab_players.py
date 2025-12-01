# gui/tabs/tab_players.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableView, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt

from gui.dataframes import DataFrameModel
from gui.dialogs.add_player_dialog import AddPlayerDialog
from gui.dialogs.edit_player_dialog import EditPlayerDialog


class PlayersTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # Buttons bar
        btn_bar = QHBoxLayout()

        btn_add = QPushButton("Add Player")
        btn_add.clicked.connect(self.open_add_dialog)
        btn_bar.addWidget(btn_add)

        btn_edit = QPushButton("Edit Selected Player")
        btn_edit.clicked.connect(self.open_edit_dialog)
        btn_bar.addWidget(btn_edit)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_status)
        btn_bar.addWidget(btn_refresh)

        layout.addLayout(btn_bar)

        # Table view
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)

        self.model = DataFrameModel()
        self.table.setModel(self.model)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.refresh_status()

    # ------------------------------------------------------------------
    def refresh_status(self):
        df = self.manager.get_player_status()
        self.model.setDataFrame(df)

    # ------------------------------------------------------------------
    # Add Player
    # ------------------------------------------------------------------
    def open_add_dialog(self):
        dlg = AddPlayerDialog(self.manager, self)
        if dlg.exec():
            self.refresh_status()

    # ------------------------------------------------------------------
    # Edit Player
    # ------------------------------------------------------------------
    def open_edit_dialog(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "No Selection", "Please select a player to edit.")
            return

        row_idx = indexes[0].row()
        player_name = self.model.df.iloc[row_idx]["Player"]

        dlg = EditPlayerDialog(self.manager, player_name, self)
        if dlg.exec():
            self.refresh_status()
