# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from enum import Enum, IntEnum, auto

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtWebEngineWidgets as QtWeb
import PyQt6.QtWebEngineCore as QtWebCore

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.backend.models.invoice import InvoiceStatus
from dfacto.backend.util import Period, PeriodFilter
from dfacto.util import qtutil as QtUtil

logger = logging.getLogger(__name__)


class InvoiceWebViewer(QtWidgets.QDialog):
    class Mode(Enum):
        CONFIRM = auto()
        SHOW = auto()
        ISSUE = auto()
        REMIND = auto()

    class Action(IntEnum):
        NO_ACTION = auto()
        TO_BASKET = auto()
        SEND = auto()
        DELETE = auto()
        PAID = auto()
        REMIND = auto()
        CANCEL = auto()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        resources = Config.dfacto_settings.resources

        self.setModal(True)

        self.setWindowFlags(
            QtCore.Qt.WindowType.Dialog |
            QtCore.Qt.WindowType.WindowTitleHint
        )
        # self.setWindowFlags(
        #     QtCore.Qt.WindowType.Dialog |
        #     QtCore.Qt.WindowType.WindowTitleHint | QtCore.Qt.WindowType.CustomizeWindowHint
        # )
        self.setWindowTitle('Invoice preview')
        self.setWindowIcon(QtGui.QIcon(f"{resources}/invoice-32.ico"))

        self.html_view = QtWeb.QWebEngineView()

        icon_size = QtCore.QSize(32, 32)

        self.basket_btn = QtWidgets.QPushButton()
        self.basket_btn.setFlat(True)
        self.basket_btn.setIconSize(icon_size)
        self.basket_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-to-basket.png"))
        self.basket_btn.setToolTip("Put invoice items in basket")
        self.basket_btn.setStatusTip("Put invoice items in basket")
        self.delete_btn = QtWidgets.QPushButton()
        self.delete_btn.setFlat(True)
        self.delete_btn.setIconSize(icon_size)
        self.delete_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-delete.png"))
        self.delete_btn.setToolTip("Delete the selected invoice")
        self.delete_btn.setStatusTip("Delete the selected invoice")
        self.emit_btn = QtWidgets.QPushButton()
        self.emit_btn.setFlat(True)
        self.emit_btn.setIconSize(icon_size)
        self.emit_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-emit.png"))
        self.emit_btn.setToolTip("Emit the selected invoice")
        self.emit_btn.setStatusTip("Emit the selected invoice")
        self.paid_btn = QtWidgets.QPushButton()
        self.paid_btn.setFlat(True)
        self.paid_btn.setIconSize(icon_size)
        self.paid_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-paid.png"))
        self.paid_btn.setToolTip("Mark the selected invoice as paid")
        self.paid_btn.setStatusTip("Mark the selected invoice as paid")
        self.cancel_btn = QtWidgets.QPushButton()
        self.cancel_btn.setFlat(True)
        self.cancel_btn.setIconSize(icon_size)
        self.cancel_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-cancel.png"))
        self.cancel_btn.setToolTip("Mark the selected invoice as cancelled")
        self.cancel_btn.setStatusTip("Mark the selected invoice as cancelled")
        self.ok_btn = QtWidgets.QPushButton()
        self.ok_btn.setFlat(True)
        self.ok_btn.setIconSize(icon_size)
        self.ok_btn.setIcon(QtGui.QIcon(f"{resources}/ok.png"))
        self.ok_btn.setToolTip("Confirm invoice emission (Alt+Enter)")
        self.ok_btn.setStatusTip("Confirm invoice emission (Alt+Enter)")
        self.quit_btn = QtWidgets.QPushButton()
        self.quit_btn.setFlat(True)
        self.quit_btn.setIconSize(icon_size)
        self.quit_btn.setIcon(QtGui.QIcon(f"{resources}/cancel.png"))
        self.quit_btn.setToolTip("Close invoice viewer (Esc)")
        self.quit_btn.setStatusTip("Close invoice viewer (Esc)")

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.basket_btn)
        tool_layout.addStretch()
        tool_layout.addWidget(self.emit_btn)
        tool_layout.addWidget(self.paid_btn)
        tool_layout.addWidget(self.delete_btn)
        tool_layout.addWidget(self.cancel_btn)
        tool_layout.addSpacing(32)
        tool_layout.addWidget(self.ok_btn)
        tool_layout.addWidget(self.quit_btn)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addLayout(tool_layout)
        main_layout.addWidget(self.html_view)
        self.setLayout(main_layout)

        self.emit_btn.clicked.connect(self.send)
        self.paid_btn.clicked.connect(self.paid)
        self.delete_btn.clicked.connect(self.delete)
        self.cancel_btn.clicked.connect(self.cancel)
        self.basket_btn.clicked.connect(self.to_basket)
        self.ok_btn.clicked.connect(self.send)
        self.quit_btn.clicked.connect(self.quit)
        self.html_view.loadFinished.connect(self.on_load_finished)
        self.html_view.pdfPrintingFinished.connect(self.on_pdf_print_finished)

        self._status = None
        self._mode = None
        self._enable_buttons(False)
        # self.button_box.setEnabled(False)
        self.move(678, 287)
        self.resize(526, 850)
        self.html_view.setZoomFactor(0.7)

    def set_invoice(self, status: InvoiceStatus, html: str, mode: Mode = Mode.SHOW) -> None:
        # https://stackoverflow.com/questions/73027846/pyqt5-reference-local-copy-of-mathjax-in-qwebengineview
        self._status = status
        self._mode = mode
        base_url = QtCore.QUrl.fromLocalFile("F:\\Users\\Documents\\Dfacto\\MyCompany\\templates" + "/")
        self.html_view.setHtml(html, base_url)
        self.html_view.show()

    @QtCore.pyqtSlot()
    def send(self) -> None:
        # https://stackoverflow.com/questions/59274653/how-to-print-from-qwebengineview
        response = api.company.get_current()
        if response.status is CommandStatus.COMPLETED:
            company: schemas.Company = response.body
            file_path = company.home / "test.pdf"
            self.html_view.printToPdf(file_path.as_posix())

    @QtCore.pyqtSlot()
    def paid(self) -> None:
        self.done(InvoiceWebViewer.Action.PAID)

    @QtCore.pyqtSlot()
    def delete(self) -> None:
        self.done(InvoiceWebViewer.Action.DELETE)

    @QtCore.pyqtSlot()
    def cancel(self) -> None:
        self.done(InvoiceWebViewer.Action.CANCEL)

    @QtCore.pyqtSlot()
    def to_basket(self) -> None:
        self.done(InvoiceWebViewer.Action.TO_BASKET)

    @QtCore.pyqtSlot()
    def quit(self) -> None:
        self.done(InvoiceWebViewer.Action.NO_ACTION)

    @QtCore.pyqtSlot(bool)
    def on_load_finished(self, success: bool) -> None:
        self._enable_buttons(success)
        # self.button_box.setEnabled(success)
        self.setWindowTitle(self.html_view.title())

    @QtCore.pyqtSlot(str, bool)
    def on_pdf_print_finished(self, file_path: str, success: bool) -> None:
        if success:
            QtWidgets.QMessageBox.information(
                None,  # type: ignore
                f"Dfacto - Save invoice to PDF",
                f"""
                <p>Get your invoice in {file_path} to send it to your client</p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            if self._status is InvoiceStatus.DRAFT:
                self.done(InvoiceWebViewer.Action.SEND)
            else:
                self.done(InvoiceWebViewer.Action.REMIND)
            return
        QtWidgets.QMessageBox.warning(
            None,  # type: ignore
            f"Dfacto - Save invoice to PDF",
            f"""
            <p>Error when saving your invoice {file_path}</p>
            """,
            QtWidgets.QMessageBox.StandardButton.Close,
        )

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        alt = event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier

        if key == QtCore.Qt.Key.Key_Escape:
            self.quit()
            return
        if alt and key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return) and self._mode == InvoiceWebViewer.Mode.CONFIRM:
            self.send()
            return

        super().keyPressEvent(event)

    def _enable_buttons(self, enable: bool) -> None:
        if enable:
            if self._mode is InvoiceWebViewer.Mode.CONFIRM:
                self.delete_btn.setVisible(False)
                self.emit_btn.setVisible(False)
                self.paid_btn.setVisible(False)
                self.cancel_btn.setVisible(False)
                self.basket_btn.setVisible(False)
                self.ok_btn.setVisible(True)
                self.quit_btn.setVisible(True)
            else:
                status = self._status
                is_in_show_mode = self._mode is InvoiceWebViewer.Mode.SHOW
                is_draft = status is InvoiceStatus.DRAFT
                is_emitted_or_reminded = status is InvoiceStatus.EMITTED or status is InvoiceStatus.REMINDED
                self.delete_btn.setVisible(is_draft)
                self.emit_btn.setVisible(is_draft and not is_in_show_mode)
                self.paid_btn.setVisible(is_emitted_or_reminded)
                self.cancel_btn.setVisible(is_emitted_or_reminded)
                self.basket_btn.setVisible(True)
                self.ok_btn.setVisible(False)
                self.quit_btn.setVisible(True)
        else:
            self.delete_btn.setVisible(False)
            self.emit_btn.setVisible(False)
            self.paid_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.basket_btn.setVisible(False)
            self.ok_btn.setVisible(False)
            self.quit_btn.setVisible(True)


    def _load_css(self, path: str, name: str) -> None:
        path = QtCore.QFile(path)
        if not path.open(QtCore.QFile.OpenModeFlag.ReadOnly | QtCore.QFile.OpenModeFlag.Text):
            return
        css = path.readAll().data().decode("utf-8")
        SCRIPT = """
        (function() {
        css = document.createElement('style');
        css.type = 'text/css';
        css.id = "%s";
        document.head.appendChild(css);
        css.innerText = `%s`;
        })()
        """ % (name, css)

        script = QtWebCore.QWebEngineScript()
        view = self.html_view
        view.page().runJavaScript(SCRIPT, QtWebCore.QWebEngineScript.ScriptWorldId.ApplicationWorld)
        script.setName(name)
        script.setSourceCode(SCRIPT)
        script.setInjectionPoint(QtWebCore.QWebEngineScript.InjectionPoint.DocumentReady)
        script.setRunsOnSubFrames(True)
        script.setWorldId(QtWebCore.QWebEngineScript.ScriptWorldId.ApplicationWorld)
        view.page().scripts().insert(script)
