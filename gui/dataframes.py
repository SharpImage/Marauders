# gui/dataframes.py

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QBrush
import pandas as pd


class DataFrameModel(QAbstractTableModel):
    """A minimal Qt table model backed by a pandas DataFrame.

    This is used throughout the GUI to display tabular data.

    Behaviour:
    - If the DataFrame is ``None`` or empty, the model reports 0 rows/columns.
    - Numbers are right-aligned; other values are left-aligned.
    - If a column named ``"Active"`` exists, rows where ``Active`` is not
      logically "YES" are rendered with a grey foreground colour. This lets
      us show active + inactive players together while visually de-emphasising
      inactive ones.
    """

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        super().__init__()
        self._dataframe: pd.DataFrame | None = df

    # ------------------------------------------------------------------
    # Core DataFrame handling
    # ------------------------------------------------------------------
    def setDataFrame(self, df: pd.DataFrame | None) -> None:
        """Replace the underlying DataFrame and reset the model."""
        self.beginResetModel()
        self._dataframe = df
        self.endResetModel()

    def getDataFrame(self) -> pd.DataFrame | None:
        """Return the underlying DataFrame (may be None)."""
        return self._dataframe

    # ------------------------------------------------------------------
    # Model API
    # ------------------------------------------------------------------
    def rowCount(self, parent: QModelIndex | None = None) -> int:  # type: ignore[override]
        if self._dataframe is None:
            return 0
        return int(self._dataframe.shape[0])

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # type: ignore[override]
        if self._dataframe is None:
            return 0
        return int(self._dataframe.shape[1])

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
        if (
            not index.isValid()
            or self._dataframe is None
            or index.row() >= self._dataframe.shape[0]
            or index.column() >= self._dataframe.shape[1]
        ):
            return None

        value = self._dataframe.iat[index.row(), index.column()]

        # -----------------------------
        # Display text
        # -----------------------------
        if role == Qt.DisplayRole:
            # Directly return empty string for NaN/None to avoid "nan" text.
            if pd.isna(value):
                return ""
            return str(value)

        # -----------------------------
        # Alignment
        # -----------------------------
        if role == Qt.TextAlignmentRole:
            # Right-align numeric types, left-align everything else.
            col = self._dataframe.columns[index.column()]
            dtype = self._dataframe[col].dtype

            if pd.api.types.is_numeric_dtype(dtype):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        # -----------------------------
        # Foreground colour (inactive rows)
        # -----------------------------
        if role == Qt.ForegroundRole:
            if self._dataframe is not None and "Active" in self._dataframe.columns:
                active_col = self._dataframe.columns.get_loc("Active")
                status = self._dataframe.iat[index.row(), active_col]
                status_str = str(status).strip().upper()
                # Treat anything other than an explicit YES as inactive/grey.
                if status_str not in ("YES", "Y", "TRUE", "1"):
                    return QBrush(Qt.gray)

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ):  # type: ignore[override]
        if self._dataframe is None:
            return None

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                # Column headers are the DataFrame's column names.
                if 0 <= section < self._dataframe.shape[1]:
                    return str(self._dataframe.columns[section])
            else:
                # Row numbers (0-based, to match previous behaviour).
                return str(section)
        return None

    # ------------------------------------------------------------------
    # Convenience helper (used in a few places)
    # ------------------------------------------------------------------
    @staticmethod
    def _build_dataframe(columns, rows) -> pd.DataFrame:
        """Small helper to construct a DataFrame from a list of rows."""
        return pd.DataFrame(rows, columns=columns)
