# gui/dialogs/edit_player_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QMessageBox, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Qt


class EditPlayerDialog(QDialog):
    def __init__(self, manager, player_name: str, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.player_name = player_name

        self.setWindowTitle(f"Edit Player — {player_name}")
        self.setMinimumWidth(400)

        # Retrieve full record via manager
        record = manager.get_player_record(player_name)

        layout = QVBoxLayout()

        # ------------------------------------------
        # FORM LAYOUT
        # ------------------------------------------
        form = QFormLayout()

        # Player name (read-only)
        self.lbl_name = QLabel(f"<b>{player_name}</b>")
        form.addRow("Player Name", self.lbl_name)

        # First Name (column name: "First Name")
        self.txt_first = QLineEdit(record.get("First Name", ""))
        form.addRow("First Name", self.txt_first)

        # Last Name (column name: "Last Name")
        self.txt_last = QLineEdit(record.get("Last Name", ""))
        form.addRow("Last Name", self.txt_last)

        # ------------------------------------------
        # Email (auto-detect any email column)
        # ------------------------------------------
        email_key = None
        for key in record.keys():
            if "email" in key.lower():
                email_key = key
                break

        email_value = record.get(email_key, "") if email_key else ""
        self.txt_email = QLineEdit(email_value)
        form.addRow("Email", self.txt_email)

        # Starting handicap (column: StartingHandicap)
        self.spn_handicap = QDoubleSpinBox()
        self.spn_handicap.setRange(0, 54)
        self.spn_handicap.setDecimals(1)
        self.spn_handicap.setValue(float(record.get("StartingHandicap", 0)))
        form.addRow("Starting Handicap", self.spn_handicap)

        # Starting balance (column: StartingBalance)
        self.spn_balance = QDoubleSpinBox()
        self.spn_balance.setRange(-1000, 1000)
        self.spn_balance.setDecimals(2)
        self.spn_balance.setValue(float(record.get("StartingBalance", 0)))
        form.addRow("Starting Balance (£)", self.spn_balance)

        # Active (column: Active)
        self.cmb_active = QComboBox()
        self.cmb_active.addItems(["YES", "NO"])
        current_active = str(record.get("Active", "YES")).upper()
        self.cmb_active.setCurrentText("YES" if current_active not in ["YES", "NO"] else current_active)
        form.addRow("Active", self.cmb_active)

        layout.addLayout(form)

        # ------------------------------------------
        # BUTTONS
        # ------------------------------------------
        btns = QHBoxLayout()

        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(self.save_changes)
        btns.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)

        layout.addLayout(btns)

        self.setLayout(layout)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------
    def save_changes(self):
        try:
            self.manager.edit_player(
                player=self.player_name,
                first_name=self.txt_first.text().strip(),
                last_name=self.txt_last.text().strip(),
                email=self.txt_email.text().strip(),
                starting_handicap=float(self.spn_handicap.value()),
                starting_balance=float(self.spn_balance.value()),
                active=self.cmb_active.currentText(),
            )

            QMessageBox.information(self, "Saved", "Player details updated.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
