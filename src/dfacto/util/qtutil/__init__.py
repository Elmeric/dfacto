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
import sys
from typing import Callable, Optional, Union

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto.backend import BackendError

from .fittedlineedit import FittedLineEdit

# from .autocompletetextedit import AutoCompleteTextEdit
# from .collapsiblewidget import CollapsibleWidget
from .framewidget import QFramedWidget
from .pathselector import DirectorySelector, FileSelector, PathSelector

# from .backgroundprogressbar import BackgroundProgressBar
# from .signaladpater import QtSignalAdapter
from .splash import SplashScreen
from .statusbar import StatusBar

# from .panelview import QPanelView

__all__ = [
    "FittedLineEdit",
    "QFramedWidget",
    "DirectorySelector",
    "FileSelector",
    "PathSelector",
    "SplashScreen",
    "StatusBar",
    "information",
    "warning",
    "critical",
    "question",
    "select_locale",
]

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


def standardFontSize(shrinkOnOdd: bool = True) -> int:
    h = QtGui.QFontMetrics(QtGui.QFont()).height()
    if h % 2 == 1:
        if shrinkOnOdd:
            h -= 1
        else:
            h += 1
    return h


def scaledIcon(path: str, size: Optional[QtCore.QSize] = None) -> QtGui.QIcon:
    """Create a QIcon that scales well.

    Args:
        path: path to the icon file.
        size: target size for the icon.

    Returns:
        The scaled icon
    """
    i = QtGui.QIcon()
    if size is None:
        s = standardFontSize()
        size = QtCore.QSize(s, s)
    i.addFile(path, size)
    return i


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
        new_selection_model = UndeselectableSelectionModel(
            self.model(), old_selection_model.parent()
        )
        self.setSelectionModel(new_selection_model)
        old_selection_model.deleteLater()


class UndeselectableSelectionModel(QtCore.QItemSelectionModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select(self, index, command):
        if command & QtCore.QItemSelectionModel.SelectionFlag.Deselect:
            return
        if command & QtCore.QItemSelectionModel.SelectionFlag.Select:
            if isinstance(index, QtCore.QModelIndex) and not index.isValid():
                return
            if isinstance(index, QtCore.QItemSelection) and len(index.indexes()) <= 0:
                return
        super().select(index, command)


def raise_fatal_error(msg: str) -> None:
    critical(
        None,  # type: ignore
        _("Dfacto - Database error"),
        _("%s\n\nTry to restart Dfacto\nIf the problem persists, contact your admin")
        % msg,
    )
    getMainWindow().close()
    raise BackendError(msg)


def information(
    parent: QtWidgets.QWidget,
    title: str,
    text: str,
) -> None:
    box = QtWidgets.QMessageBox(parent=parent)
    box.setIcon(QtWidgets.QMessageBox.Icon.Information)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
    close_btn = box.button(QtWidgets.QMessageBox.StandardButton.Close)
    close_btn.setText(_("Close"))
    box.exec()


def warning(
    parent: QtWidgets.QWidget,
    title: str,
    text: str,
) -> None:
    box = QtWidgets.QMessageBox(parent=parent)
    box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
    close_btn = box.button(QtWidgets.QMessageBox.StandardButton.Close)
    close_btn.setText(_("Close"))
    box.exec()


def critical(
    parent: QtWidgets.QWidget,
    title: str,
    text: str,
) -> None:
    box = QtWidgets.QMessageBox(parent=parent)
    box.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
    close_btn = box.button(QtWidgets.QMessageBox.StandardButton.Close)
    close_btn.setText(_("Close"))
    box.exec()


def question(
    parent: QtWidgets.QWidget,
    title: str,
    text: str,
) -> int:
    box = QtWidgets.QMessageBox(parent=parent)
    box.setIcon(QtWidgets.QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(
        QtWidgets.QMessageBox.StandardButton.Yes
        | QtWidgets.QMessageBox.StandardButton.No
    )
    yes_btn = box.button(QtWidgets.QMessageBox.StandardButton.Yes)
    yes_btn.setText(_("Yes"))
    no_btn = box.button(QtWidgets.QMessageBox.StandardButton.No)
    no_btn.setText(_("No"))
    return box.exec()


class LocaleSelector(QtWidgets.QDialog):
    def __init__(self, icon: str, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setWindowTitle("Dfacto - Select you language")
        self.setWindowIcon(QtGui.QIcon(icon))
        self.setFixedWidth(300)

        self.locale_cmb = QtWidgets.QComboBox()
        self.locale_cmb.addItem("English", "en_US")
        self.locale_cmb.addItem("Français", "fr_FR")

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok,
            QtCore.Qt.Orientation.Horizontal,
            self,
        )
        self.button_box.accepted.connect(self.accept)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.locale_cmb)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)


def select_locale(icon: str) -> str:
    app = QtWidgets.QApplication([""])
    dialog = LocaleSelector(icon)
    dialog.show()
    app.exec()
    return dialog.locale_cmb.currentData()
