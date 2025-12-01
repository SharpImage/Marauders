# gui/dataframes.py

from PySide6.QtCore import QAbstractTableModel, Qt
import pandas as pd

class DataFrameModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._dataframe = df

    def setDataFrame(self, df):
        self.beginResetModel()
        self._dataframe = df
        self.endResetModel()

    def rowCount(self, parent=None):
        return 0 if self._dataframe is None else len(self._dataframe)

    def columnCount(self, parent=None):
        return 0 if self._dataframe is None else len(self._dataframe.columns)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._dataframe.iat[index.row(), index.column()]
            return str(value)
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._dataframe.columns[section]
            else:
                return str(section)
        return None

    @staticmethod
    def _build_dataframe(columns, rows):
        return pd.DataFrame(rows, columns=columns)
