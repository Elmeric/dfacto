# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
from enum import Enum, IntEnum, auto
from pathlib import Path

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWebEngineWidgets as QtWeb
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import api
from dfacto.backend.api import CommandStatus
from dfacto.backend.models.invoice import InvoiceStatus
from dfacto.frontend import get_current_company
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
            QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.WindowTitleHint
        )
        self.setWindowTitle(_("Invoice preview"))
        self.setWindowIcon(QtGui.QIcon(f"{resources}/invoice-32.ico"))

        self.html_view = QtWeb.QWebEngineView()
        self.html_view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)

        icon_size = QtCore.QSize(32, 32)

        self.basket_btn = QtWidgets.QPushButton()
        self.basket_btn.setFlat(True)
        self.basket_btn.setIconSize(icon_size)
        self.basket_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-to-basket.png"))
        tip = _("Put invoice items in basket")
        self.basket_btn.setToolTip(tip)
        self.basket_btn.setStatusTip(tip)
        self.delete_btn = QtWidgets.QPushButton()
        self.delete_btn.setFlat(True)
        self.delete_btn.setIconSize(icon_size)
        self.delete_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-delete.png"))
        tip = _("Delete the selected invoice")
        self.delete_btn.setToolTip(tip)
        self.delete_btn.setStatusTip(tip)
        self.emit_btn = QtWidgets.QPushButton()
        self.emit_btn.setFlat(True)
        self.emit_btn.setIconSize(icon_size)
        self.emit_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-emit.png"))
        tip = _("Emit the selected invoice")
        self.emit_btn.setToolTip(tip)
        self.emit_btn.setStatusTip(tip)
        self.paid_btn = QtWidgets.QPushButton()
        self.paid_btn.setFlat(True)
        self.paid_btn.setIconSize(icon_size)
        self.paid_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-paid.png"))
        tip = _("Mark the selected invoice as paid")
        self.paid_btn.setToolTip(tip)
        self.paid_btn.setStatusTip(tip)
        self.cancel_btn = QtWidgets.QPushButton()
        self.cancel_btn.setFlat(True)
        self.cancel_btn.setIconSize(icon_size)
        self.cancel_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-cancel.png"))
        tip = _("Mark the selected invoice as cancelled")
        self.cancel_btn.setToolTip(tip)
        self.cancel_btn.setStatusTip(tip)
        self.ok_btn = QtWidgets.QPushButton()
        self.ok_btn.setFlat(True)
        self.ok_btn.setIconSize(icon_size)
        self.ok_btn.setIcon(QtGui.QIcon(f"{resources}/ok.png"))
        tip = _("Confirm invoice emission (Alt+Enter)")
        self.ok_btn.setToolTip(tip)
        self.ok_btn.setStatusTip(tip)
        self.quit_btn = QtWidgets.QPushButton()
        self.quit_btn.setFlat(True)
        self.quit_btn.setIconSize(icon_size)
        self.quit_btn.setIcon(QtGui.QIcon(f"{resources}/cancel.png"))
        tip = _("Close invoice viewer (Esc)")
        self.quit_btn.setToolTip(tip)
        self.quit_btn.setStatusTip(tip)
        self.progress_bar = QtWidgets.QProgressBar()

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.progress_bar)
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
        self.html_view.loadStarted.connect(self.on_load_started)
        self.html_view.loadProgress.connect(self.on_load_progress)
        self.html_view.loadFinished.connect(self.on_load_finished)
        self.html_view.pdfPrintingFinished.connect(self.on_pdf_print_finished)

        self._invoice_id = None
        self._status = None
        self._mode = None
        self._enable_buttons(False)
        self.move(678, 287)
        self.resize(526, 850)
        self.html_view.setZoomFactor(0.7)
        self.html_view.setEnabled(False)  # To let focus on the toolbar buttons
        self.progress_bar.hide()

    def set_invoice(
        self, invoice_id: int, status: InvoiceStatus, html: str, mode: Mode = Mode.SHOW
    ) -> None:
        # https://stackoverflow.com/questions/73027846/pyqt5-reference-local-copy-of-mathjax-in-qwebengineview
        self._invoice_id = invoice_id
        self._status = status
        self._mode = mode

        company = get_current_company()
        templates_dir = Config.dfacto_settings.templates
        template_dir = templates_dir / company.home.name
        if not template_dir.exists():
            resources = Config.dfacto_settings.resources
            template_dir = resources / "invoice_template"

        base_url = QtCore.QUrl.fromLocalFile(template_dir.as_posix() + "/")
        self.html_view.setHtml(html, base_url)
        self.html_view.show()

    @QtCore.pyqtSlot()
    def send(self) -> None:
        # https://stackoverflow.com/questions/59274653/how-to-print-from-qwebengineview
        home = get_current_company().home
        file_path = self._get_invoice_pathname(home)
        self.html_view.printToPdf(file_path.as_posix())

    def _get_invoice_pathname(self, home: Path) -> Path:
        response = api.client.get_invoice_pathname(
            invoice_id=self._invoice_id, home=home
        )
        if response.status is CommandStatus.COMPLETED:
            pathname: Path = response.body
            return pathname

        msg = _("Cannot get invoice pathname")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

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

    @QtCore.pyqtSlot()
    def on_load_started(self) -> None:
        self.progress_bar.reset()
        self.progress_bar.show()

    @QtCore.pyqtSlot(int)
    def on_load_progress(self, progress: int) -> None:
        self.progress_bar.setValue(progress)

    @QtCore.pyqtSlot(bool)
    def on_load_finished(self, success: bool) -> None:
        self.progress_bar.hide()
        self._enable_buttons(success)
        self.setWindowTitle(self.html_view.title())

    @QtCore.pyqtSlot(str, bool)
    def on_pdf_print_finished(self, file_path: str, success: bool) -> None:
        app_name = QtWidgets.QApplication.applicationName()
        action = _("Save invoice to PDF")
        if success:
            msg_box = QtWidgets.QMessageBox()
            msg_box.setWindowTitle(f"{app_name} - {action}")
            lbl1 = _("Your invoice is saved in:")
            msg_box.setText(
                f"""
                <p>{lbl1}</p>
                <p><strong>{file_path}</strong></p>
                """
            )
            lbl2 = _("You can open it in a PDF viewer or in the Explorer")
            msg_box.setInformativeText(lbl2)
            msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
            msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Close)
            open_btn = msg_box.addButton(
                _("Open"), QtWidgets.QMessageBox.ButtonRole.ActionRole
            )
            explore_btn = msg_box.addButton(
                _("Show in Explorer"), QtWidgets.QMessageBox.ButtonRole.ActionRole
            )
            mail_btn = msg_box.addButton(
                _("Send by email"), QtWidgets.QMessageBox.ButtonRole.ActionRole
            )
            mail_btn.setEnabled(False)
            mail_btn.setToolTip(_("Send by email is not yet implemented"))
            # mail_lbl = QtWidgets.QLabel(msg_box)
            # mail_lbl.setText(
            #     f"<a href='mailto:erik.lemoine@gmail.com?subject=Facture du ...&body=Please, receive your invoice'>"
            #     f"Send by email</a>"
            # )
            # mail_lbl.setOpenExternalLinks(True)
            msg_box.setDefaultButton(explore_btn)

            msg_box.exec()

            if msg_box.clickedButton() is open_btn:
                os.startfile(file_path)
            elif msg_box.clickedButton() is explore_btn:
                os.startfile(Path(file_path).parent)
            elif msg_box.clickedButton() is mail_btn:
                # attachment = f"file:///{urllib.parse.quote(Path(file_path).as_posix())}"
                # os.startfile(
                #     f"mailto:erik.lemoine@gmail.com?subject=Facture du ...&"
                #     f"body=Please, receive your invoice&"
                #     f"attach={attachment}"
                # )
                pass

            if self._status is InvoiceStatus.DRAFT:
                self.done(InvoiceWebViewer.Action.SEND)
            else:
                self.done(InvoiceWebViewer.Action.REMIND)
            return

        msg = _("Error when saving your invoice")
        QtUtil.warning(
            None,  # type: ignore
            f"{app_name} - {action}",
            f"""
            <p>{msg} {file_path}</p>
            """,
        )

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        alt = event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier

        if key == QtCore.Qt.Key.Key_Escape:
            self.quit()
            return
        if (
            alt
            and key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return)
            and self._mode == InvoiceWebViewer.Mode.CONFIRM
        ):
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
                is_emitted_or_reminded = (
                    status is InvoiceStatus.EMITTED or status is InvoiceStatus.REMINDED
                )
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
