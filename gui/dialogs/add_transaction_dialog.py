# gui/dialogs/add_transaction_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDoubleSpinBox, QPushButton, QFormLayout, QMessageBox, QDateEdit
)
from PySide6.QtCore import QDate
import pandas as pd


class AddTransactionDialog(QDialog):
    """
    Dialog to create a new entry in PlayerTransactions.
    """

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager

        self.setWindowTitle("Add Transaction")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        form = QFormLayout()

        # Date field
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date", self.date_edit)

        # Player dropdown
        self.cmb_player = QComboBox()
        players_df = self.manager.player_service.players_repo.get_all()
        players = players_df["Player"].astype(str).tolist()
        self.cmb_player.addItems(players)
        form.addRow("Player", self.cmb_player)

        # Paid In
        self.spn_paid_in = QDoubleSpinBox()
        self.spn_paid_in.setRange(0, 9999)
        self.spn_paid_in.setDecimals(2)
        form.addRow("Paid In (£)", self.spn_paid_in)

        # Paid Out
        self.spn_paid_out = QDoubleSpinBox()
        self.spn_paid_out.setRange(0, 9999)
        self.spn_paid_out.setDecimals(2)
        form.addRow("Paid Out (£)", self.spn_paid_out)

        # Description
        self.txt_description = QLineEdit()
        form.addRow("Description", self.txt_description)

        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()

        btn_add = QPushButton("Add Transaction")
        btn_add.clicked.connect(self.add_transaction)
        btn_row.addWidget(btn_add)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        layout.addLayout(btn_row)
        self.setLayout(layout)

    # ---------------------------------------------------------
    def add_transaction(self):
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        player = self.cmb_player.currentText()
        paid_in = float(self.spn_paid_in.value())
        paid_out = float(self.spn_paid_out.value())
        desc = self.txt_description.text().strip()

        # Basic validation
        if paid_in > 0 and paid_out > 0:
            QMessageBox.warning(
                self,
                "Invalid Transaction",
                "Enter either Paid In OR Paid Out, not both.",
            )
            return

        if paid_in == 0 and paid_out == 0:
            QMessageBox.warning(
                self,
                "Invalid Transaction",
                "Paid In or Paid Out must be greater than zero.",
            )
            return

        try:
            # Insert into DB
            self.manager.finance_service.finance_repo.add_transaction(
                date=date_str,
                player=player,
                paid_in=paid_in,
                paid_out=paid_out,
                description=desc,
            )

            # Rebuild finance ledger immediately
            self.manager.finance_service.rebuild_finance()

            QMessageBox.information(self, "Success", "Transaction added.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
