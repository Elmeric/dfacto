"""A set of useful Qt5 utilities.

It provides:
    - A customized status bar.
    - A QProgressBar that show background task progress.
    - A descriptor that wraps a Qt Signal.
    - A customized splash screen.
    - A QLineEdit that fit its content while minimizing its size.
    - A dialog to select file or directory path.
    - A plain text editor with auto-completion.
    - A tool to layout two widgets horizontally or vertically.
    - A tool to create a QAction.
    - A tool to retrieve the application main window.
    - A tool to reconnect a Qt signal to another slot.
    - A DcfsStyle class to override some default settings of the application
      style.
    - A standard QStyledItemDelegate that hides focus decoration.
    - A QSyntaxHighlighter that highlight all occurrences of a string pattern.
    - A basic textual filter input widget.
"""
from typing import Callable, Optional, Union

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

# from .backgroundprogressbar import BackgroundProgressBar
# from .signaladpater import QtSignalAdapter
# from .splash import SplashScreen
from .fittedlineedit import FittedLineEdit

# from .autocompletetextedit import AutoCompleteTextEdit
# from .collapsiblewidget import CollapsibleWidget
from .framewidget import QFramedWidget
from .pathselector import DirectorySelector, FileSelector, PathSelector
from .statusbar import StatusBar

# from .panelview import QPanelView


# def autoLayoutWithLabel(
#         label: QtWidgets.QWidget,
#         widget: QtWidgets.QWidget,
#         orientation: Optional[str] = 'V') -> QtWidgets.QLayout:
#     """Layout two widgets horizontally or vertically (default).
#
#     Current usage: the first widget is a QLabel that titles the second.
#
#     Args:
#         label: the 'widget' title (generally a QLabel).
#         widget: any QWidget to be labelled by the 'label'.
#         orientation: 'label' and 'widget' are layout vertically id equal to 'V'
#             (the default), horizontally otherwise.
#
#     Returns:
#         the created QVBoxLayout or QHBoxLayout.
#     """
#     layout = QtWidgets.QVBoxLayout() if orientation == 'V' else QtWidgets.QHBoxLayout()
#     layout.setContentsMargins(0, 0, 0, 0)
#     layout.setAlignment(QtCore.Qt.AlignLeft)
#     layout.addWidget(label)
#     layout.addWidget(widget)
#     layout.addStretch()
#     return layout


def createAction(
    parent: QtCore.QObject,
    text: str,
    name: Optional[str] = None,
    slot: Optional[Callable] = None,
    shortcut: Optional[Union[str, QtGui.QKeySequence.StandardKey]] = None,
    icon: Optional[Union[str, QtGui.QIcon]] = None,
    tip: Optional[str] = None,
    checkable: Optional[bool] = False,
    signal: Optional[str] = "triggered",
) -> QtGui.QAction:
    """A convenient function to create a QAction.

    Args:
        parent: parent object of the QAction to be created (mandatory).
        text: text of the QaAction (mandatory).
        name: optional objectName of the QAction.
        slot: optional slot to connect on the QAction signal.
        shortcut:optional shortcut of the QAction.
        icon: optional icon of the QAction (maybe a file name or a QIcon).
        tip: optional tool tip and status tip of the QAction.
        checkable: make the QAction checkable if True (False by default).
        signal: the QAction signal to be cnnected with 'slot' ('triggered' by
            default).

    Returns:
        The created QAction
    """
    action = QtGui.QAction(text, parent)
    if name is not None:
        action.setObjectName(name)
    if icon is not None:
        action.setIcon(QtGui.QIcon(icon))
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if slot is not None:
        getattr(action, signal).connect(slot)
    if checkable:
        action.setCheckable(True)
    return action


def getMainWindow() -> QtWidgets.QMainWindow:
    """A convenient function to retrieve the application main window.

    The application main window is defined as the first QMainWindow object
    retrieved from its top level widgets.

    Returns:
        The application main window.

    Raises:
        ValueError if no QMainWindow object exists in the application top level
            widgets list.
    """
    widgets = QtWidgets.QApplication.topLevelWidgets()
    for w in widgets:
        if isinstance(w, QtWidgets.QMainWindow):
            return w
    raise ValueError("No Main Window found!")


#
#
# def reconnect(signal, newSlot=None, oldSlot=None):
#     try:
#         if oldSlot is not None:
#             while True:
#                 signal.disconnect(oldSlot)
#         else:
#             signal.disconnect()
#     except TypeError:
#         pass
#     if newSlot is not None:
#         signal.connect(newSlot)
#
#
# def standardFontSize(shrinkOnOdd: bool = True) -> int:
#     h = QtGui.QFontMetrics(QtGui.QFont()).height()
#     if h % 2 == 1:
#         if shrinkOnOdd:
#             h -= 1
#         else:
#             h += 1
#     return h
#
#
# def scaledIcon(path: str, size: Optional[QtCore.QSize] = None) -> QtGui.QIcon:
#     """Create a QIcon that scales well.
#
#     Args:
#         path: path to the icon file.
#         size: target size for the icon.
#
#     Returns:
#         The scaled icon
#     """
#     i = QtGui.QIcon()
#     if size is None:
#         s = standardFontSize()
#         size = QtCore.QSize(s, s)
#     i.addFile(path, size)
#     return i
#
#
# def setElidedText(label: QtWidgets.QLabel, text: str):
#     fm = label.fontMetrics()
#     width = label.width() - 2
#     elidedText = fm.elidedText(text, QtCore.Qt.ElideMiddle, width)
#     label.setText(elidedText)


class MyAppStyle(QtWidgets.QProxyStyle):
    """A QProxyStyle specialization to adjust some default style settings.

    Increase the default small icon size from 16 to 24 pixels.
    Adjust the size of the view item decoration (apply to QTreeView and
    QTableView).
    """

    def pixelMetric(self, metric, option=None, widget=None) -> int:
        size = super().pixelMetric(metric, option, widget)
        if metric == QtWidgets.QStyle.PixelMetric.PM_SmallIconSize:
            size += 8
        return size

    def subElementRect(self, element, option, widget) -> QtCore.QRect:
        rect = super().subElementRect(element, option, widget)
        if element == QtWidgets.QStyle.SubElement.SE_ItemViewItemDecoration:
            dh = (rect.height() - 16) / 2
            if dh >= 0:
                rect.setRect(rect.x(), rect.y() + dh, rect.width(), 16)
        return rect


class NoFocusDelegate(QtWidgets.QStyledItemDelegate):
    """A standard QStyledItemDelegate that hides focus decoration.

    From https://stackoverflow.com/questions/9795791/removing-dotted-border-without-setting-nofocus-in-windows-pyqt.

    Args:
        parent: an optional parent for the delegate.
    """

    def __init__(self, parent):
        super().__init__(parent)

    def paint(self, QPainter, QStyleOptionViewItem, QModelIndex):
        if QStyleOptionViewItem.state & QtWidgets.QStyle.StateFlag.State_HasFocus:
            QStyleOptionViewItem.state = (
                QStyleOptionViewItem.state ^ QtWidgets.QStyle.StateFlag.State_HasFocus
            )
        super().paint(QPainter, QStyleOptionViewItem, QModelIndex)


#
#
# class PatternHighlighter(QtGui.QSyntaxHighlighter):
#     """A QSyntaxHighlighter that highlight all occurrences of a string pattern.
#
#     From https://doc.qt.io/qt-5/qtwidgets-richtext-syntaxhighlighter-example.html.
#
#     Args:
#         pattern: the regular expression defining the highlight pattern.
#         parent: an optional parent for the delegate.
#
#     Attributes:
#         keywordsFormat: a bold / darkMagenta QTextCharFormat to highlight
#             matching text
#
#     Properties (in Qt5 properties style):
#         pattern: a QRegularExpression for text highlighting.
#     """
#     def __init__(self, pattern: QtCore.QRegularExpression, parent):
#         super().__init__(parent)
#         self._pattern = pattern
#         self.keywordsFormat = QtGui.QTextCharFormat()
#         self.keywordsFormat.setFontWeight(QtGui.QFont.Bold)
#         self.keywordsFormat.setForeground(QtCore.Qt.darkMagenta)
#
#     def pattern(self) -> QtCore.QRegularExpression:
#         """Getter for the pattern property.
#
#         Returns:
#             the current pattern regular expression.
#         """
#         return self._pattern
#
#     def setPattern(self, pattern: QtCore.QRegularExpression):
#         """The pattern property setter.
#
#         Args:
#             pattern: a QRegularExpression for text highlighting.
#         """
#         self._pattern = pattern
#
#     def highlightBlock(self, text):
#         """Highlight all text blocks that match the pattern.
#
#         The highlightBlock() method is called automatically whenever it is
#         necessary by the rich text engine, i.e. when there are text blocks that
#         have changed.
#
#         Args:
#             text: the string where to find pattern to highlight.
#         """
#         i = self._pattern.globalMatch(text)
#         while i.hasNext():
#             match = i.next()
#             self.setFormat(match.capturedStart(), match.capturedLength(), self.keywordsFormat)
#
#
# class TextFilterWidget(QtWidgets.QWidget):
#     """A basic textual filter input widget.
#
#     Allow to enter the text to filter on, set the filter on/off and toggle
#     a match case option.
#
#     Args:
#         filterIcon: the icon of the filter on/off button.
#         matchCaseIcon: the icon of the match case button.
#         parent: an optional parent for the widget.
#
#     Class attributes:
#         toggled: This signal is emitted whenever the filter on/off button is
#             toggled. The parameter is True when the filter is on.
#         matchCaseToggled: This signal is emitted whenever the match case button
#             is toggled. The parameter is True when the match case option is on.
#         filterTextEdited: This signal is emitted whenever the text filter
#             changes. The parameter is the new text to filter.
#
#     Attributes:
#         textFilterBtn: the filter on/off button.
#         filterText: the text filter line edit widget.
#     """
#
#     toggled = QtCore.pyqtSignal(bool)
#     matchCaseToggled = QtCore.pyqtSignal(bool)
#     filterTextEdited = QtCore.pyqtSignal(str)
#
#     def __init__(self, filterIcon: QtGui.QIcon, matchCaseIcon: QtGui.QIcon, parent=None):
#         super().__init__(parent)
#
#         self.textFilterBtn = QtWidgets.QToolButton()
#         self.textFilterBtn.setIconSize(QtCore.QSize(24, 24))
#         self.textFilterBtn.setIcon(filterIcon)
#         self.textFilterBtn.setCheckable(True)
#         self.textFilterBtn.setToolTip('Filter flows on text content')
#         self.textFilterBtn.setStatusTip('Filter flows on text content')
#         self.textFilterBtn.toggled.connect(self.toggled)                # noqa
#
#         self.matchCaseBtn = QtWidgets.QToolButton()
#         self.matchCaseBtn.setIconSize(QtCore.QSize(24, 24))
#         self.matchCaseBtn.setIcon(matchCaseIcon)
#         self.matchCaseBtn.setCheckable(True)
#         self.matchCaseBtn.setToolTip('Match case')
#         self.matchCaseBtn.toggled.connect(self.toggleMatcCase)             # noqa
#
#         self.filterText = QtWidgets.QLineEdit()
#         self.filterText.setPlaceholderText('')
#         self.filterText.setClearButtonEnabled(True)
#         self.filterText.textChanged.connect(self.filterTextEdited)           # noqa
#         self.filterText.returnPressed.connect(self.triggerTextFilter)        # noqa
#
#         layout = QtWidgets.QHBoxLayout()
#         layout.addWidget(self.textFilterBtn)
#         layout.addWidget(self.matchCaseBtn)
#         layout.addWidget(self.filterText)
#         layout.setContentsMargins(0, 0, 0, 0)
#
#         self.setLayout(layout)
#
#     @QtCore.pyqtSlot(bool)
#     def toggleMatcCase(self, checked: bool):
#         """This slot is called when the match case option is toggled.
#
#         Args:
#             checked: the state of the match case option (True if on).
#         """
#         tip = 'Match case' if checked else ''
#         self.filterText.setPlaceholderText(tip)
#         self.matchCaseToggled.emit(checked)
#
#     @QtCore.pyqtSlot()
#     def triggerTextFilter(self):
#         """Called on a Return pressed event to toggle the filter on/off. """
#         checked = not self.textFilterBtn.isChecked()
#         self.textFilterBtn.setChecked(checked)
#
#     def clear(self):
#         self.textFilterBtn.setChecked(False)
#         self.matchCaseBtn.setChecked(False)
#         self.filterText.setText('')


class UndeselectableListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        # self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setStyleSheet(
            "QListView::item{border: 1px solid transparent;}"
            "QListView::item:selected{color: blue;}"
            "QListView::item:selected{background-color: rgba(0,0,255,64);}"
            "QListView::item:selected:hover{border-color: rgba(0,0,255,128);}"
            "QListView::item:hover{background: rgba(0,0,255,32);}"
        )
        self.setItemDelegate(NoFocusDelegate(self))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setResizeMode(QtWidgets.QListWidget.ResizeMode.Adjust)
        self.setSizeAdjustPolicy(
            QtWidgets.QListWidget.SizeAdjustPolicy.AdjustToContents
        )

        old_selection_model = self.selectionModel()
        new_selection_model = MySelectionModel(
            self.model(), old_selection_model.parent()
        )
        self.setSelectionModel(new_selection_model)
        old_selection_model.deleteLater()


class MySelectionModel(QtCore.QItemSelectionModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select(self, index, command):
        if command & QtCore.QItemSelectionModel.SelectionFlag.Deselect:
            return
        super().select(index, command)


class BasketController(QtWidgets.QWidget):
    add_started = QtCore.pyqtSignal(int)
    quantity_changed = QtCore.pyqtSignal(int)

    _quantity: int
    _folded: bool

    def __init__(
        self,
        basket_icon: QtGui.QIcon,
        add_icon: QtGui.QIcon,
        minus_icon: QtGui.QIcon,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._max = 100

        self.quantity_lbl = QtWidgets.QLineEdit()
        self.quantity_lbl.setValidator(
            QtGui.QRegularExpressionValidator(QtCore.QRegularExpression("[0-9]*"))
        )
        self.quantity_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.quantity_lbl.setFrame(False)
        palette = self.quantity_lbl.palette()
        palette.setColor(
            QtGui.QPalette.ColorRole.Base, QtCore.Qt.GlobalColor.transparent
        )
        self.quantity_lbl.setPalette(palette)
        self.quantity_lbl.setFixedWidth(30)

        icon_size = QtCore.QSize(32, 32)
        self.basket_btn = QtWidgets.QPushButton(basket_icon, "")
        self.basket_btn.setIconSize(icon_size)
        self.basket_btn.setToolTip("Add to basket")
        self.basket_btn.setStatusTip("Add to basket")
        self.basket_btn.setFlat(True)

        icon_size = QtCore.QSize(18, 18)
        self.add_btn = QtWidgets.QPushButton(add_icon, "")
        self.add_btn.setIconSize(icon_size)
        self.add_btn.setToolTip("Increase")
        self.add_btn.setStatusTip("Increase")
        self.add_btn.setFlat(True)
        self.minus_btn = QtWidgets.QPushButton(minus_icon, "")
        self.minus_btn.setIconSize(icon_size)
        self.minus_btn.setToolTip("Decrease")
        self.minus_btn.setStatusTip("Decrease")
        self.minus_btn.setFlat(True)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.basket_btn)
        layout.addWidget(self.minus_btn)
        layout.addWidget(self.quantity_lbl)
        layout.addWidget(self.add_btn)
        layout.addStretch()

        self.setLayout(layout)

        self.basket_btn.clicked.connect(self.start_adding)
        self.add_btn.clicked.connect(self.increase)
        self.minus_btn.clicked.connect(self.decrease)
        self.quantity_lbl.editingFinished.connect(self.input_quantity)

        self.reset(0)

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, qty: int) -> None:
        delta = qty - self._quantity

        # In all cases, save the new quantity and display it
        self._quantity = qty
        self.quantity_lbl.setText(str(qty))

        if qty == 0:
            # On update, 0 means "clear basket"
            self._fold()
            self.quantity_changed.emit(0)
        elif qty > 0:
            if self._folded:
                # add first quantity (1) in basket
                self._unfold()
                self.add_started.emit(delta)
            else:
                # Increment or decrement the basket quantity
                self.quantity_changed.emit(delta)

    @QtCore.pyqtSlot()
    def start_adding(self) -> None:
        if self._folded:
            self.quantity = 1

    @QtCore.pyqtSlot()
    def increase(self) -> None:
        if self._quantity == self._max:
            # We cannot go beyond the max
            return
        self.quantity = min(self._max, self._quantity + 1)

    @QtCore.pyqtSlot()
    def decrease(self) -> None:
        self.quantity = max(0, self._quantity - 1)

    @QtCore.pyqtSlot()
    def input_quantity(self) -> None:
        # Qt6 bug work around (editingFinished emitted twice).
        # Refer to https://bugreports.qt.io/browse/QTBUG-40
        obj = self.sender()
        if not obj.isModified():                                        # noqa
            # Ignore second signal
            return
        obj.setModified(False)                                          # noqa

        qty_str = self.quantity_lbl.text()
        quantity = 0 if qty_str == "" else int(qty_str)
        try:
            self.quantity = min(self._max, max(0, quantity))
        except ValueError:
            # Ignore invalid input and display the previous quantity
            self.quantity_lbl.setText(str(self._quantity))

    def reset(self, quantity: int) -> None:
        if quantity == 0:
            # On init, 0 means "empty basket"
            self._fold()
        else:
            self._unfold()
        self._quantity = quantity
        self.quantity_lbl.setText(str(quantity))

    def _unfold(self) -> None:
        self._folded = False
        self.basket_btn.setIconSize(QtCore.QSize(24, 24))
        self.add_btn.show()
        self.minus_btn.show()
        self.quantity_lbl.show()

    def _fold(self) -> None:
        self._folded = True
        self.basket_btn.setIconSize(QtCore.QSize(32, 32))
        self.add_btn.hide()
        self.minus_btn.hide()
        self.quantity_lbl.hide()
