# gui/tabs/tab_dashboard.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox
)

class DashboardTab(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

        layout = QVBoxLayout()

        # -------------------------------------------------
        # Checkbox: include inactive players in counts
        # -------------------------------------------------
        self.chk_inactive = QCheckBox("Include inactive players")
        self.chk_inactive.setChecked(False)
        self.chk_inactive.stateChanged.connect(self.refresh_dashboard)
        layout.addWidget(self.chk_inactive)

        # -------------------------------------------------
        # Summary labels
        # -------------------------------------------------
        self.lbl_total_players = QLabel()
        self.lbl_active_players = QLabel()
        self.lbl_inactive_players = QLabel()
        self.lbl_num_games = QLabel()
        self.lbl_last_game = QLabel()
        self.lbl_total_prizes = QLabel()
        self.lbl_total_game_fees = QLabel()
        self.lbl_kitty = QLabel()

        for lbl in [
            self.lbl_total_players, self.lbl_active_players, self.lbl_inactive_players,
            self.lbl_num_games, self.lbl_last_game, self.lbl_total_prizes,
            self.lbl_total_game_fees, self.lbl_kitty
        ]:
            layout.addWidget(lbl)

        self.setLayout(layout)

        self.refresh_dashboard()

    # ---------------------------------------------------------
    # Dashboard summary
    # ---------------------------------------------------------
    def refresh_dashboard(self):

        include_inactive = self.chk_inactive.isChecked()

        # -----------------------------------------
        # PLAYERS
        # -----------------------------------------
        players_df = self.manager.player_service.players_repo.get_all()
        active_df = players_df[players_df["Active"].str.upper() == "YES"]
        inactive_df = players_df[players_df["Active"].str.upper() != "YES"]

        if include_inactive:
            count_players = len(players_df)
        else:
            count_players = len(active_df)

        self.lbl_total_players.setText(f"Total players: {len(players_df)}")
        self.lbl_active_players.setText(f"Active players: {len(active_df)}")
        self.lbl_inactive_players.setText(f"Inactive players: {len(inactive_df)}")

        # -----------------------------------------
        # GAME COUNT
        # -----------------------------------------
        dates = self.manager.scores_repo.get_game_dates()
        num_games = len(dates)
        last_game = dates[-1] if num_games > 0 else "N/A"

        self.lbl_num_games.setText(f"Games recorded: {num_games}")
        self.lbl_last_game.setText(f"Last game date: {last_game}")

        # -----------------------------------------
        # FINANCE SUMMARY
        # -----------------------------------------
        finance = self.manager.finance_service.rebuild_finance()

        kitty = finance.kitty_total

        # --- Total prizes awarded ---
        mask_prizes = (finance.ledger["Category"] == "PRIZE")
        total_prizes = finance.ledger.loc[mask_prizes, "PaidOut"].sum()

        # --- Total game fees collected ---
        mask_fees = (finance.ledger["Category"] == "GAME_FEE")
        total_fees = finance.ledger.loc[mask_fees, "PaidIn"].sum()

        self.lbl_total_prizes.setText(f"Total prizes awarded: £{total_prizes:.2f}")
        self.lbl_total_game_fees.setText(f"Total game fees collected: £{total_fees:.2f}")
        self.lbl_kitty.setText(f"Kitty balance: £{kitty:.2f}")
