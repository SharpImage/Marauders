# gui/dialogs/add_player_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QMessageBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt


class AddPlayerDialog(QDialog):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager

        self.setWindowTitle("Add New Player")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        form = QFormLayout()

        # Name (required)
        self.txt_player = QLineEdit()
        form.addRow("Player Name *", self.txt_player)

        # Optional fields
        self.txt_first = QLineEdit()
        form.addRow("First Name", self.txt_first)

        self.txt_last = QLineEdit()
        form.addRow("Last Name", self.txt_last)

        self.txt_email = QLineEdit()
        form.addRow("Email", self.txt_email)

        # Starting values
        self.spn_handicap = QDoubleSpinBox()
        self.spn_handicap.setRange(0, 54)
        self.spn_handicap.setDecimals(1)
        form.addRow("Starting Handicap", self.spn_handicap)

        self.spn_balance = QDoubleSpinBox()
        self.spn_balance.setRange(-1000, 1000)
        self.spn_balance.setDecimals(2)
        form.addRow("Starting Balance (£)", self.spn_balance)

        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        btn_add = QPushButton("Add Player")
        btn_add.clicked.connect(self.add_player)
        btns.addWidget(btn_add)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        layout.addLayout(btns)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # ADD PLAYER HANDLER
    # ------------------------------------------------------------------
    def add_player(self):
        try:
            player = self.txt_player.text().strip()
            if not player:
                QMessageBox.warning(self, "Missing Name", "Player name is required.")
                return

            self.manager.add_player(
                player=player,
                first_name=self.txt_first.text().strip(),
                last_name=self.txt_last.text().strip(),
                email=self.txt_email.text().strip(),
                starting_handicap=float(self.spn_handicap.value()),
                starting_balance=float(self.spn_balance.value()),
            )

            QMessageBox.information(self, "Success", f"Player '{player}' added.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
