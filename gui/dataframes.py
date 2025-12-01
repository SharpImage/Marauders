from PySide6.QtCore import QAbstractTableModel, Qt


class DataFrameModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._dataframe = df   # SINGLE source of truth

    # -----------------------------------------------------------
    # Set the dataframe
    # -----------------------------------------------------------
    def setDataFrame(self, df):
        self.beginResetModel()
        self._dataframe = df   # always assign to same attribute
        self.endResetModel()

    # -----------------------------------------------------------
    # Read-only access for export / clipboard
    # -----------------------------------------------------------
    def dataFrame(self):
        return self._dataframe

    # -----------------------------------------------------------
    # Table dimensions
    # -----------------------------------------------------------
    def rowCount(self, parent=None):
        if self._dataframe is None:
            return 0
        return len(self._dataframe)

    def columnCount(self, parent=None):
        if self._dataframe is None:
            return 0
        return len(self._dataframe.columns)

    # -----------------------------------------------------------
    # Cell data
    # -----------------------------------------------------------
    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._dataframe.iat[index.row(), index.column()]
            return str(value)
        return None

    # -----------------------------------------------------------
    # Header labels
    # -----------------------------------------------------------
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._dataframe.columns[section]
            else:
                return str(section)
        return None
