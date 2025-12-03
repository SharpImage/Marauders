# gui/widgets/scrollable_tab.py

from PySide6.QtWidgets import QScrollArea


class ScrollableTab(QScrollArea):
    """
    A wrapper that makes any QWidget scrollable.
    Used for all tabs to support smaller screens and laptops.
    """
    def __init__(self, inner_widget):
        super().__init__()
        self.setWidgetResizable(True)
        self.setWidget(inner_widget)
