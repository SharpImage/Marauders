# gui/tabs/tab_settings.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QMessageBox, QLineEdit, QHBoxLayout
)
from PySide6.QtCore import Qt
import pandas as pd
import requests
from io import BytesIO


class SettingsTab(QWidget):
    def __init__(self, manager):
        super().__init__()

        self.manager = manager

        layout = QVBoxLayout()

        # ---------------------------------------------------
        # TEXT BOX: master file path OR URL (new!)
        # ---------------------------------------------------
        txt_layout = QHBoxLayout()
        self.txt_master = QLineEdit()
        self.txt_master.setPlaceholderText("Enter local file path or URL...")
        self.txt_master.setText("" if self.manager.master_file is None else str(self.manager.master_file))
        txt_layout.addWidget(QLabel("Master file:"))
        txt_layout.addWidget(self.txt_master)
        layout.addLayout(txt_layout)

        # ---------------------------------------------------
        # BUTTON: choose local file
        # ---------------------------------------------------
        btn_set = QPushButton("Browse for Local File…")
        btn_set.clicked.connect(self.choose_local_file)
        layout.addWidget(btn_set)

        # ---------------------------------------------------
        # BUTTON: save the text in the box as master file
        # ---------------------------------------------------
        btn_save = QPushButton("Save Master File Path/URL")
        btn_save.clicked.connect(self.save_master_file)
        layout.addWidget(btn_save)

        # ---------------------------------------------------
        # BUTTON: test connection (URL or local)
        # ---------------------------------------------------
        btn_test = QPushButton("Test Connection")
        btn_test.clicked.connect(self.test_connection)
        layout.addWidget(btn_test)

        # ---------------------------------------------------
        # STATUS LABEL
        # ---------------------------------------------------
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#444;")
        layout.addWidget(self.lbl_status)

        layout.addStretch()
        self.setLayout(layout)

    # ---------------------------------------------------
    # LOCAL FILE PICKER
    # ---------------------------------------------------
    def choose_local_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Master Excel File",
            "",
            "Excel Files (*.xlsx)"
        )
        if path:
            self.txt_master.setText(path)

    # ---------------------------------------------------
    # SAVE MASTER FILE (URL or local path)
    # ---------------------------------------------------
    def save_master_file(self):
        text = self.txt_master.text().strip()
        if not text:
            QMessageBox.warning(self, "No Path", "Please enter a file path or URL.")
            return

        self.manager.set_master_file(text)
        QMessageBox.information(self, "Saved", f"Master file set to:\n{text}")

    # ---------------------------------------------------
    # TEST CONNECTION
    # ---------------------------------------------------
    def test_connection(self):
        path = self.txt_master.text().strip()

        if not path:
            QMessageBox.warning(self, "No File", "Master file is not set.")
            return

        try:
            # ------------------------------
            # Load Excel from URL or local
            # ------------------------------
            if path.startswith("http://") or path.startswith("https://"):
                self.lbl_status.setText("Testing URL…")
                self.lbl_status.repaint()

                resp = requests.get(path, timeout=10)
                resp.raise_for_status()
                excel_bytes = BytesIO(resp.content)
                df = pd.read_excel(excel_bytes, sheet_name="Scores")

            else:
                self.lbl_status.setText("Testing local file…")
                self.lbl_status.repaint()

                df = pd.read_excel(path, sheet_name="Scores")

            # ---------------------------------------
            # APPLY SAME RENAME MAP AS ImportService
            # ---------------------------------------
            rename_map = {
                "Game Date": "Game_Date",
                "Player Name": "Player_Name",
                "Front Nine": "Front_Nine",
                "Back Nine": "Back_Nine",
                "Overall": "Overall",
                "NTP Hole 3": "NTP_Hole3",
                "NTP Hole 6": "NTP_Hole6",
                "NTP in 2 Hole 7": "NTP_in2_Hole7",
                "NTP in 2 Hole 10": "NTP_in2_Hole10",
                "NTP Hole 11": "NTP_Hole11",
                "NTP Hole 15": "NTP_Hole15",
            }

            df.rename(columns=rename_map, inplace=True, errors="ignore")

            # ---------------------------------------
            # Now validate required columns
            # ---------------------------------------
            required = ["Game_Date", "Player_Name"]
            missing = [c for c in required if c not in df.columns]

            if missing:
                QMessageBox.critical(
                    self,
                    "Invalid File",
                    "The 'Scores' sheet does not contain required renamed columns:\n"
                    + ", ".join(required)
                )
                return

            # Success
            QMessageBox.information(
                self,
                "Connection OK",
                f"Successfully loaded the Scores sheet!\nRows: {len(df)}"
            )
            self.lbl_status.setText("Connection OK ✔")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed:\n{e}")
            self.lbl_status.setText("Connection FAILED ✘")

