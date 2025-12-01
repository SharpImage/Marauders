# gui/tabs/tab_settings.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QInputDialog
)


class SettingsTab(QWidget):
    def __init__(self, manager, main_window):
        super().__init__()
        self.manager = manager
        self.main_window = main_window

        layout = QVBoxLayout()

        # Database Path
        layout.addWidget(QLabel(f"Database: {manager.db_path}"))

        # Master File
        self.lbl_master = QLabel("Master File: Not Set")
        if manager.master_file:
            self.lbl_master.setText(f"Master File: {manager.master_file}")
        layout.addWidget(self.lbl_master)

        btn_master = QPushButton("Set Master File…")
        btn_master.clicked.connect(self.choose_master_file)
        layout.addWidget(btn_master)

        # ------------------------------------------------------
        # STARTING KITTY
        # ------------------------------------------------------
        start_kitty = self.manager.finance_service.finance_repo.get_starting_kitty()
        self.lbl_kitty = QLabel(f"Starting Kitty: £{start_kitty:.2f}")
        layout.addWidget(self.lbl_kitty)

        btn_set_kitty = QPushButton("Set Starting Kitty")
        btn_set_kitty.clicked.connect(self.set_starting_kitty)
        layout.addWidget(btn_set_kitty)

        self.setLayout(layout)

    def choose_master_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel Master File",
            "",
            "Excel (*.xlsx)"
        )
        if path:
            self.manager.set_master_file(path)
            self.lbl_master.setText(f"Master File: {path}")

    def set_starting_kitty(self):
        amount, ok = QInputDialog.getDouble(
            self,
            "Set Starting Kitty",
            "Enter Starting Kitty (£):",
            decimals=2
        )
        if ok:
            self.manager.finance_service.finance_repo.set_starting_kitty(amount)
            self.lbl_kitty.setText(f"Starting Kitty: £{amount:.2f}")
