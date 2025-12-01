# gui/tabs/tab_dashboard.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout
from PySide6.QtCore import Qt


class DashboardTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        title = QLabel("<h1>Marauders Golf System</h1>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("<h3>System Overview</h3>")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        layout.addLayout(grid)

        # Summary labels
        self.lbl_players = QLabel("")
        self.lbl_games = QLabel("")
        self.lbl_handicaps = QLabel("")
        self.lbl_balances = QLabel("")

        grid.addWidget(QLabel("Active Players:"), 0, 0)
        grid.addWidget(self.lbl_players, 0, 1)

        grid.addWidget(QLabel("Games Played:"), 1, 0)
        grid.addWidget(self.lbl_games, 1, 1)

        grid.addWidget(QLabel("Handicap Records:"), 2, 0)
        grid.addWidget(self.lbl_handicaps, 2, 1)

        grid.addWidget(QLabel("Finance Entries:"), 3, 0)
        grid.addWidget(self.lbl_balances, 3, 1)

        btn_refresh = QPushButton("Refresh Dashboard")
        btn_refresh.clicked.connect(self.refresh_dashboard)
        layout.addWidget(btn_refresh)

        self.setLayout(layout)
        self.refresh_dashboard()

    def refresh_dashboard(self):
        # Player count
        players = self.manager.get_player_status()
        self.lbl_players.setText(str(len(players)))

        # Games played
        self.lbl_games.setText(str(len(self.manager.get_valid_game_dates())))

        # Handicap history count
        h = self.manager.handicap_service.hcaps_repo.get_history()
        self.lbl_handicaps.setText(str(len(h)))

        # Finance ledger
        ledger = self.manager.finance_service.finance_repo.get_ledger()
        self.lbl_balances.setText(str(len(ledger)))
