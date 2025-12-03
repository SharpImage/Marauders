# gui/main_window.py

from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox, QFileDialog, QSizePolicy
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from marauders.manager import MaraudersManager

# Import tabs
from gui.tabs.tab_dashboard import DashboardTab
from gui.tabs.tab_scores import ScoresTab
from gui.tabs.tab_handicaps import HandicapsTab
from gui.tabs.tab_prizes import PrizesTab
from gui.tabs.tab_finance import FinanceTab
from gui.tabs.tab_players import PlayersTab
from gui.tabs.tab_games import GamesTab
from gui.tabs.tab_settings import SettingsTab
from gui.tabs.tab_reports import ReportsTab

# Scroll wrapper
from gui.widgets.scrollable_tab import ScrollableTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Marauders Golf System")

        # Smaller minimum size for laptops
        self.setMinimumSize(800, 500)
        self.resize(1000, 700)

        # Load DB
        self.manager = MaraudersManager(db_path="marauders.db")

        self._create_menu()
        self._create_tabs()

    # -------------------------------------------------------
    def _create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        open_master = QAction("Set Master File...", self)
        open_master.triggered.connect(self.set_master_file)
        file_menu.addAction(open_master)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu("Tools")

        run_all = QAction("Run Full Update", self)
        run_all.triggered.connect(self.run_full_update)
        tools_menu.addAction(run_all)

    # -------------------------------------------------------
    def _create_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)

        # Ensure tabs resize on small screens
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create wrapped tabs
        self.tab_dashboard = ScrollableTab(DashboardTab(self.manager))
        self.tab_scores = ScrollableTab(ScoresTab(self.manager))
        self.tab_handicaps = ScrollableTab(HandicapsTab(self.manager))
        self.tab_prizes = ScrollableTab(PrizesTab(self.manager))
        self.tab_finance = ScrollableTab(FinanceTab(self.manager))
        self.tab_players = ScrollableTab(PlayersTab(self.manager))
        self.tab_games = ScrollableTab(GamesTab(self.manager))
        self.tab_settings = ScrollableTab(SettingsTab(self.manager))
        self.tab_reports = ScrollableTab(ReportsTab(self.manager))

        # Attach to tab widget
        self.tabs.addTab(self.tab_dashboard, "Dashboard")
        self.tabs.addTab(self.tab_scores, "Scores")
        self.tabs.addTab(self.tab_handicaps, "Handicaps")
        self.tabs.addTab(self.tab_prizes, "Prizes")
        self.tabs.addTab(self.tab_finance, "Finance")
        self.tabs.addTab(self.tab_players, "Players")
        self.tabs.addTab(self.tab_games, "Games")
        self.tabs.addTab(self.tab_settings, "Settings")
        self.tabs.addTab(self.tab_reports, "Reports")

        self.setCentralWidget(self.tabs)

    # -------------------------------------------------------
    def set_master_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Master Excel File",
            "",
            "Excel Files (*.xlsx)"
        )
        if path:
            self.manager.set_master_file(path)
            QMessageBox.information(self, "Master File Set", f"Master file set:\n{path}")

    def run_full_update(self):
        try:
            self.manager.run_full_update()
            QMessageBox.information(self, "Success", "Full update completed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
