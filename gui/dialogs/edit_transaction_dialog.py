# gui/dialogs/edit_transaction_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDoubleSpinBox, QPushButton, QFormLayout,
    QMessageBox, QDateEdit
)
from PySide6.QtCore import QDate
import pandas as pd


class EditTransactionDialog(QDialog):
    """
    Dialog to edit an existing transaction.
    Expects a pandas Series (single row) with fields:
        TransactionID, Date, Player, PaidIn, PaidOut, Description
    """

    def __init__(self, manager, transaction_row, parent=None):
        super().__init__(parent)
        self.manager = manager

        # MUST exist for updating the correct DB row
        self.transaction_id = int(transaction_row["TransactionID"])
        self.row = transaction_row

        self.setWindowTitle("Edit Transaction")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        form = QFormLayout()

        # -------------------------------------
        # Date
        # -------------------------------------
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")

        raw_date = transaction_row.get("Date")
        if hasattr(raw_date, "strftime"):
            date_str = raw_date.strftime("%Y-%m-%d")
        else:
            date_str = str(raw_date)
        self.date_edit.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))

        form.addRow("Date", self.date_edit)

        # -------------------------------------
        # Player dropdown (same as Add dialog)
        # -------------------------------------
        self.cmb_player = QComboBox()
        players_df = self.manager.player_service.players_repo.get_all()
        players = players_df["Player"].astype(str).tolist()
        self.cmb_player.addItems(players)

        current_player = str(transaction_row.get("Player", "") or "")
        idx = self.cmb_player.findText(current_player)
        if idx >= 0:
            self.cmb_player.setCurrentIndex(idx)

        form.addRow("Player", self.cmb_player)

        # -------------------------------------
        # Paid In
        # -------------------------------------
        self.spn_paid_in = QDoubleSpinBox()
        self.spn_paid_in.setRange(0, 9999)
        self.spn_paid_in.setDecimals(2)
        self.spn_paid_in.setValue(float(transaction_row.get("PaidIn", 0) or 0))
        form.addRow("Paid In (£)", self.spn_paid_in)

        # -------------------------------------
        # Paid Out
        # -------------------------------------
        self.spn_paid_out = QDoubleSpinBox()
        self.spn_paid_out.setRange(0, 9999)
        self.spn_paid_out.setDecimals(2)
        self.spn_paid_out.setValue(float(transaction_row.get("PaidOut", 0) or 0))
        form.addRow("Paid Out (£)", self.spn_paid_out)

        # -------------------------------------
        # Description
        # -------------------------------------
        self.txt_description = QLineEdit()
        self.txt_description.setText(str(transaction_row.get("Description", "") or ""))
        form.addRow("Description", self.txt_description)

        layout.addLayout(form)

        # -------------------------------------
        # Buttons
        # -------------------------------------
        btn_row = QHBoxLayout()

        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(self.save_transaction)
        btn_row.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        layout.addLayout(btn_row)

        self.setLayout(layout)

    # ---------------------------------------------------------
    def save_transaction(self):
        """Validate and update a transaction."""
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        player = self.cmb_player.currentText()
        paid_in = float(self.spn_paid_in.value())
        paid_out = float(self.spn_paid_out.value())
        desc = self.txt_description.text().strip()

        # ---- VALIDATION ----
        if paid_in > 0 and paid_out > 0:
            QMessageBox.warning(self, "Invalid Input",
                                "Paid In AND Paid Out cannot both be greater than zero.")
            return

        if paid_in == 0 and paid_out == 0:
            QMessageBox.warning(self, "Invalid Input",
                                "Either Paid In OR Paid Out must be greater than zero.")
            return

        try:
            # Call FinanceRepository.update_transaction()
            self.manager.finance_service.finance_repo.update_transaction(
                transaction_id=self.transaction_id,
                date=date_str,
                player=player,
                paid_in=paid_in,
                paid_out=paid_out,
                description=desc,
            )

            # Rebuild finance ledger immediately
            self.manager.finance_service.rebuild_finance()

            QMessageBox.information(self, "Updated", "Transaction updated successfully.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
