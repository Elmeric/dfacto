import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets


class FittedLineEdit(QtWidgets.QLineEdit):
    """A QLineEdit that fit its content while minimizing its size."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )

    def sizeHint(self) -> QtCore.QSize:
        """Override the parent sizeHint getter to fit its text content.

        Returns:
            A width size hint corresponding to the text content and font.
            A minimum 100 size is set to ensure readibility as well as an extra
            15 pixels.

        """
        size = QtCore.QSize()
        fm = self.fontMetrics()
        width = fm.boundingRect(self.text()).width() + 15
        size.setWidth(max(100, width))
        return size

    def resizeEvent(self, event: QtGui.QResizeEvent):
        """Override the parent resizeEvent handler to udpate the widget geometry.

        Args:
            event: the widget resize event.
        """
        self.updateGeometry()
        super().resizeEvent(event)
