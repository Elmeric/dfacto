# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from datetime import datetime
from enum import IntEnum
from typing import Any, Optional, cast

from babel.dates import format_date

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.backend.models.invoice import InvoiceStatus
from dfacto.backend.util import Period, PeriodFilter
from dfacto.util import qtutil as QtUtil
from .Invoice_web_view import InvoiceWebViewer

logger = logging.getLogger(__name__)

InvoiceItem = list[int, int, str, str, datetime, float, float, float, InvoiceStatus]

ID, CLIENT_ID, CLIENT_NAME, CODE, CREATED_ON, RAW_AMOUNT, VAT, NET_AMOUNT, STATUS = range(9)


class InvoiceTableModel(QtCore.QAbstractTableModel):
    STATUS_COLOR = {
        InvoiceStatus.PAID: 'darkGreen',
        InvoiceStatus.EMITTED: 'darkslateblue',
        InvoiceStatus.CANCELLED: 'lightgrey',
        InvoiceStatus.REMINDED: 'darkorange',
        InvoiceStatus.DRAFT: 'darkgrey',
        'ERROR': 'firebrick'
    }

    class UserRoles(IntEnum):
        DateRole = QtCore.Qt.ItemDataRole.UserRole + 1
        StatusRole = QtCore.Qt.ItemDataRole.UserRole + 2

    def __init__(self) -> None:
        super().__init__()
        self._headers = [
            "Id",
            "Client Id",
            "Client name",
            "Code",
            "Date",
            "Raw amount",
            "VAT",
            "Net amount",
            "Status",
        ]
        self._client_id: int = -1
        self._invoices: dict[int, InvoiceItem] = {}
        self._invoice_ids: list[int] = []

    def load_invoices(self) -> None:
        response = api.client.get_all_invoices()

        if response.status is CommandStatus.COMPLETED:
            invoices: list[schemas.Invoice] = response.body
            self.clear_invoices()
            self.add_invoices(invoices)
            return

        QtUtil.raise_fatal_error(
            f"Cannot retrieve invoices - Reason is: {response.reason}"
        )

    # def set_client(self, client_id: int) -> None:
    #     self._client_id = client_id
    #     invoices = self._get_invoices_of_client(client_id)
    #     self.clear_invoices()
    #     self.add_invoices(invoices)

    # def update_invoice_status(self, invoice_id: int, status: InvoiceStatus) -> bool:
    #     assert status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED)
    #     invoice = self._invoices[invoice_id]
    #     if status is InvoiceStatus.PAID:
    #         response = api.client.mark_as_paid(
    #             invoice[CLIENT_ID],
    #             invoice_id=invoice_id,
    #             status=status
    #         )
    #     else:
    #         response = api.client.mark_as_cancelled(
    #             invoice[CLIENT_ID],
    #             invoice_id=invoice_id,
    #             status=status
    #         )
    #
    #     if response.status is CommandStatus.COMPLETED:
    #         self.update_invoice(response.body)
    #         return True
    #
    #     if response.status is CommandStatus.FAILED:
    #         QtUtil.raise_fatal_error(
    #             f"Cannot update invoice status"
    #             f" - Reason is: {response.reason}"
    #         )
    #     if response.status is CommandStatus.REJECTED:
    #         QtWidgets.QMessageBox.warning(
    #             None,  # type: ignore
    #             f"Dfacto - Update invoice status",
    #             f"""
    #             <p>Cannot update invoice status</p>
    #             <p><strong>Reason is: {response.reason}</strong></p>
    #             """,
    #             QtWidgets.QMessageBox.StandardButton.Close,
    #         )
    #     return False

    def invoice_from_index(self, index: QtCore.QModelIndex) -> Optional[InvoiceItem]:
        invoice_id = self._invoice_id_from_index(index)
        if invoice_id is not None:
            return self._invoices[invoice_id]
        return None

    def index_from_invoice_id(self, invoice_id: int) -> QtCore.QModelIndex:
        try:
            row = self._invoice_ids.index(invoice_id)
        except ValueError:
            return QtCore.QModelIndex()
        else:
            return self.index(row, CODE)

    def clear_invoices(self) -> None:
        self.beginResetModel()
        self._invoices = {}
        self._invoice_ids = []
        self.endResetModel()

    def add_invoices(self, invoices: list[schemas.Invoice]) -> None:
        row = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), row, row + len(invoices) - 1)

        for invoice in invoices:
            self._invoice_ids.append(invoice.id)
            date_ = (
                invoice.created_on
                if invoice.status is InvoiceStatus.DRAFT
                else invoice.issued_on
            )
            self._invoices[invoice.id] = [
                invoice.id,
                invoice.client_id,
                invoice.client.name,
                invoice.code,
                date_,
                invoice.amount.raw,
                invoice.amount.vat,
                invoice.amount.net,
                invoice.status,
            ]

        self.endInsertRows()

    def add_invoice(self, invoice: schemas.Invoice) -> None:
        self.add_invoices([invoice])

    def update_invoice(self, invoice: schemas.Invoice) -> None:
        start_index = self.index_from_invoice_id(invoice.id)
        if start_index.isValid():
            self._invoices[invoice.id] = [
                invoice.id,
                invoice.client_id,
                invoice.client.name,
                invoice.code,
                invoice.created_on,
                invoice.amount.raw,
                invoice.amount.vat,
                invoice.amount.net,
                invoice.status,
            ]
            end_index = start_index.sibling(start_index.row(), STATUS)
            self.dataChanged.emit(
                start_index,
                end_index,
                (QtCore.Qt.ItemDataRole.DisplayRole,),
            )

    def remove_invoice(self, invoice_id: int) -> None:
        index = self.index_from_invoice_id(invoice_id)
        if index.isValid():
            row = index.row()
            self.beginRemoveRows(QtCore.QModelIndex(), row, row)
            del self._invoices[invoice_id]
            del self._invoice_ids[row]
            self.endRemoveRows()

    def rowCount(self, index: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._invoice_ids)

    def columnCount(self, index: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._headers)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == QtCore.Qt.ItemDataRole.TextAlignmentRole:
            if orientation == QtCore.Qt.Orientation.Horizontal:
                return int(
                    QtCore.Qt.AlignmentFlag.AlignLeft
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
            return int(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )

        if role == QtCore.Qt.ItemDataRole.FontRole:
            bold_font = QtGui.QFont()
            bold_font.setBold(True)
            return bold_font

        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == QtCore.Qt.Orientation.Horizontal:
            return self._headers[section]

        return int(section + 1)

    # def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
    #     if index.isValid():
    #         column = index.column()
    #
    #         if column == STATUS:
    #             status = index.model().data(index, InvoiceTableModel.UserRoles.StatusRole)
    #             if status and status in (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED):
    #                 flags = QtCore.Qt.ItemFlag.ItemIsEditable | super().flags(index)
    #                 return flags
    #
    #         return super().flags(index)
    #
    #     return QtCore.Qt.ItemFlag.NoItemFlags

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if index.isValid():
            row = index.row()
            column = index.column()

            if 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
                item = self._invoices[self._invoice_ids[row]]

                if role in (
                    QtCore.Qt.ItemDataRole.DisplayRole,
                    QtCore.Qt.ItemDataRole.EditRole,
                ):
                    if column == CREATED_ON:
                        datetime_ = cast(datetime, item[column])
                        return format_date(
                            datetime_.date(), format="short", locale="fr_FR"
                        )
                    if column == STATUS:
                        status = cast(InvoiceStatus, item[column])
                        return status.name
                    if 0 <= column < len(item):
                        return str(item[column])

                if role == QtCore.Qt.ItemDataRole.ForegroundRole:
                    status = cast(InvoiceStatus, item[STATUS])
                    return QtGui.QBrush(QtGui.QColor(self.STATUS_COLOR[status]))

                if role == QtCore.Qt.ItemDataRole.FontRole:
                    status = cast(InvoiceStatus, item[STATUS])
                    font = QtGui.QFont()
                    if column in (CLIENT_NAME, CODE, CREATED_ON):
                        font.setBold(True)
                    if status is InvoiceStatus.CANCELLED:
                        font.setItalic(True)
                    return font

                if role == InvoiceTableModel.UserRoles.DateRole:
                    return cast(datetime, item[CREATED_ON]).date()

                if role == InvoiceTableModel.UserRoles.StatusRole:
                    return cast(InvoiceStatus, item[STATUS])

        return None

    # def setData(
    #     self,
    #     index: QtCore.QModelIndex,
    #     value: Any,
    #     role: int = QtCore.Qt.ItemDataRole.EditRole,
    # ) -> bool:
    #     if index.isValid() and role == QtCore.Qt.ItemDataRole.EditRole:
    #         row = index.row()
    #         column = index.column()
    #
    #         if 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
    #             invoice_id = self._invoice_ids[row]
    #
    #             if column == STATUS:
    #                 print(f"setData: row: {row}, status: {value}")
    #                 return self.update_invoice_status(
    #                     invoice_id=invoice_id, status=value
    #                 )
    #
    #             return super().setData(index, value, role)
    #
    #     return False

    def _invoice_id_from_index(self, index: QtCore.QModelIndex) -> Optional[int]:
        if index.isValid():
            row = index.row()
            if 0 <= row < self.rowCount():
                return self._invoice_ids[row]
        return None

    # @staticmethod
    # def _get_invoices_of_client(client_id: int) -> list[schemas.Invoice]:
    #     response = api.client.get_invoices(client_id)
    #
    #     if response.status is CommandStatus.COMPLETED:
    #         invoices: list[schemas.Invoice] = response.body
    #         return invoices
    #
    #     QtUtil.raise_fatal_error(
    #         f"Cannot retrieve invoices of client {client_id}"
    #         f" - Reason is: {response.reason}"
    #     )


class InvoiceViewer(QtUtil.QFramedWidget):
    def __init__(self, invoice_model: InvoiceTableModel, parent=None) -> None:
        super().__init__(parent=parent)

        resources = Config.dfacto_settings.resources

        self.active_pix = QtGui.QPixmap(
            f"{resources}/client-active.png"
        ).scaledToHeight(24, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.inactive_pix = QtGui.QPixmap(
            f"{resources}/client-inactive.png"
        ).scaledToHeight(24, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.all_pix = QtGui.QPixmap(
            f"{resources}/client-all.png"
        ).scaledToHeight(24, QtCore.Qt.TransformationMode.SmoothTransformation)

        self.header_lbl = QtWidgets.QLabel("INVOICES")
        self.header_lbl.setMaximumHeight(32)
        self.client_pix = QtWidgets.QLabel()
        self.client_pix.setPixmap(self.active_pix)
        self.client_lbl = QtWidgets.QLabel()

        icon_size = QtCore.QSize(32, 32)
        small_icon_size = QtCore.QSize(24, 24)

        self.all_ckb = QtWidgets.QCheckBox("")
        self.all_ckb.setToolTip("Show invoices of all clients")
        self.all_ckb.setStatusTip("Show invoices of all clients")
        self.all_ckb.setIconSize(icon_size)
        self.all_ckb.setIcon(QtGui.QIcon(f"{resources}/client-all.png"))
        self.period_cmb = QtWidgets.QComboBox()
        self.period_cmb.setToolTip("Filter on emitted date")
        self.period_cmb.setStatusTip("Filter on emitted date")
        self.status_cmb = QtWidgets.QComboBox()
        self.status_cmb.setToolTip("Filter on status")
        self.status_cmb.setStatusTip("Filter on status")
        self.reset_btn = QtWidgets.QPushButton()
        self.reset_btn.setFlat(True)
        self.reset_btn.setIconSize(small_icon_size)
        self.reset_btn.setIcon(QtGui.QIcon(f"{resources}/reload.png"))
        self.reset_btn.setToolTip("Reset to default filters")
        self.reset_btn.setStatusTip("Reset to default filters")

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
        self.show_btn = QtWidgets.QPushButton()
        self.show_btn.setFlat(True)
        self.show_btn.setIconSize(icon_size)
        self.show_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-preview.png"))
        self.show_btn.setToolTip("Preview the selected invoice")
        self.show_btn.setStatusTip("Preview the selected invoice")
        self.emit_btn = QtWidgets.QPushButton()
        self.emit_btn.setFlat(True)
        self.emit_btn.setIconSize(icon_size)
        self.emit_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-emit.png"))
        self.emit_btn.setToolTip("Emit the selected invoice")
        self.emit_btn.setStatusTip("Emit the selected invoice")
        self.remind_btn = QtWidgets.QPushButton()
        self.remind_btn.setFlat(True)
        self.remind_btn.setIconSize(icon_size)
        self.remind_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-remind.png"))
        self.remind_btn.setToolTip("Remind the selected invoice")
        self.remind_btn.setStatusTip("Remind the selected invoice")
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

        self._invoice_table = InvoiceTable(invoice_model)

        self.invoice_html_view = InvoiceWebViewer(parent=self)

        header = QtWidgets.QWidget()
        header_color = QtGui.QColor("#5d5b59")
        header_font_color = QtGui.QColor(QtCore.Qt.GlobalColor.white)
        header_style = f"""
            QWidget {{
                background-color: {header_color.name()};
                color: {header_font_color.name()};
            }}
        """
        header.setStyleSheet(header_style)
        header.setMinimumWidth(350)
        header.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        header_layout.setSpacing(5)
        header_layout.addWidget(self.header_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.client_pix)
        header_layout.addWidget(self.client_lbl)
        header.setLayout(header_layout)

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setContentsMargins(5, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.all_ckb)
        tool_layout.addWidget(self.period_cmb)
        tool_layout.addWidget(self.status_cmb)
        tool_layout.addWidget(self.reset_btn)
        tool_layout.addStretch()
        tool_layout.addWidget(self.show_btn)
        tool_layout.addWidget(self.emit_btn)
        tool_layout.addWidget(self.remind_btn)
        tool_layout.addWidget(self.paid_btn)
        tool_layout.addWidget(self.delete_btn)
        tool_layout.addWidget(self.cancel_btn)
        tool_layout.addSpacing(32)
        tool_layout.addWidget(self.basket_btn)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header)
        main_layout.addLayout(tool_layout)
        main_layout.addWidget(self._invoice_table)
        self.setLayout(main_layout)

        for filter_ in PeriodFilter:
            self.period_cmb.addItem(
                filter_.name.title().replace("_", " "),
                userData=filter_.as_period()
            )
        self.period_cmb.addItem("All Dates", userData=Period())
        self.period_cmb.model().sort(0)

        for status in InvoiceStatus:
            self.status_cmb.addItem(status.name.title(), userData=status)
        self.status_cmb.addItem("Not Cancelled", userData="")
        self.status_cmb.model().sort(0)

        self.all_ckb.toggled.connect(self.on_all_selection)
        self.period_cmb.activated.connect(self.on_period_selection)
        self.status_cmb.activated.connect(self.on_status_selection)
        self.reset_btn.clicked.connect(self.set_default_filters)

        self._invoice_table.selectionModel().currentChanged.connect(self.show_buttons)

        self.show_btn.clicked.connect(self.show_invoice)
        self.emit_btn.clicked.connect(self.issue_invoice)
        self.remind_btn.clicked.connect(self.remind_invoice)
        self.paid_btn.clicked.connect(self.paid_invoice)
        self.delete_btn.clicked.connect(self.delete_invoice)
        self.cancel_btn.clicked.connect(self.cancel_invoice)

        self.invoice_html_view.finished.connect(self.on_html_view_finished)

        self._current_client: Optional[schemas.Client] = None
        self.all_ckb.setChecked(False)

    def load_invoices(self) -> None:
        self._invoice_table.source_model().load_invoices()
        self._invoice_table.sort_invoices()
        self.set_default_filters()

    @QtCore.pyqtSlot()
    def show_invoice(self) -> None:
        invoice = self._invoice_table.selected_invoice()

        response = api.client.preview_invoice(
            invoice[CLIENT_ID],
            invoice_id=invoice[ID],
            mode=api.client.HtmlMode.VIEW
        )
        if response.status is CommandStatus.COMPLETED:
            status = cast(InvoiceStatus, invoice[STATUS])
            html = response.body
            self.invoice_html_view.set_invoice(status, html, mode=InvoiceWebViewer.Mode.SHOW)
            self.invoice_html_view.open()
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Show invoice",
                f"""
                <p>Cannot show invoice {invoice[ID]} of client {invoice[CLIENT_NAME]}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot show invoice"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot()
    def issue_invoice(self) -> None:
        invoice = self._invoice_table.selected_invoice()

        response = api.client.preview_invoice(
            invoice[CLIENT_ID],
            invoice_id=invoice[ID],
            mode=api.client.HtmlMode.ISSUE
        )
        if response.status is CommandStatus.COMPLETED:
            status = cast(InvoiceStatus, invoice[STATUS])
            html = response.body
            self.invoice_html_view.set_invoice(status, html, mode=InvoiceWebViewer.Mode.CONFIRM)
            self.invoice_html_view.open()
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Preview invoice",
                f"""
                <p>Cannot preview invoice {invoice[ID]} of client {invoice[CLIENT_NAME]}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot preview invoice"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot()
    def remind_invoice(self) -> None:
        invoice = self._invoice_table.selected_invoice()

        response = api.client.preview_invoice(
            invoice[CLIENT_ID],
            invoice_id=invoice[ID],
            mode=api.client.HtmlMode.REMIND
        )
        if response.status is CommandStatus.COMPLETED:
            status = cast(InvoiceStatus, invoice[STATUS])
            html = response.body
            self.invoice_html_view.set_invoice(status, html, mode=InvoiceWebViewer.Mode.CONFIRM)
            self.invoice_html_view.open()
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Preview invoice",
                f"""
                <p>Cannot preview invoice {invoice[ID]} of client {invoice[CLIENT_NAME]}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot preview invoice"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot()
    def delete_invoice(self) -> None:
        invoice = self._invoice_table.selected_invoice()

        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Delete invoice",
            f"""
            <p>Do you really want to delete this invoice permanently?</p>
            <p><strong>{invoice[CODE]}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        response = api.client.delete_invoice(invoice[CLIENT_ID], invoice_id=invoice[ID])

        if response.status is CommandStatus.COMPLETED:
            self._invoice_table.source_model().remove_invoice(invoice[ID])
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Delete invoice",
                f"""
                <p>Cannot delete invoice {invoice[ID]} of client {invoice[CLIENT_NAME]}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot delete invoice {invoice[ID]} of client {invoice[CLIENT_NAME]}"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot()
    def emit_invoice(self):
        invoice_lst = self._invoice_table.selected_invoice()

        response = api.client.mark_as_emitted(
            invoice_lst[CLIENT_ID],
            invoice_id=invoice_lst[ID]
        )

        if response.status is CommandStatus.COMPLETED:
            invoice: schemas.Invoice = response.body
            self._invoice_table.source_model().update_invoice(invoice)
            self._enable_buttons(status=InvoiceStatus.EMITTED)
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Mark invoice as emitted",
                f"""
                <p>Cannot mark invoice {invoice_lst[ID]} as emitted</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot mark invoice {invoice_lst[ID]} as emitted"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot()
    def reemit_invoice(self):
        invoice_lst = self._invoice_table.selected_invoice()

        response = api.client.mark_as_reminded(
            invoice_lst[CLIENT_ID],
            invoice_id=invoice_lst[ID]
        )

        if response.status is CommandStatus.COMPLETED:
            invoice: schemas.Invoice = response.body
            self._invoice_table.source_model().update_invoice(invoice)
            self._enable_buttons(status=InvoiceStatus.REMINDED)
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Mark invoice as reminded",
                f"""
                <p>Cannot mark invoice {invoice_lst[ID]} as reminded</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot mark invoice {invoice_lst[ID]} as reminded"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot()
    def paid_invoice(self):
        invoice_lst = self._invoice_table.selected_invoice()

        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Mark invoice as paid",
            f"""
            <p>Do you really want to mark permanently this invoice as paid?</p>
            <p><strong>{invoice_lst[CODE]}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        response = api.client.mark_as_paid(
            invoice_lst[CLIENT_ID],
            invoice_id=invoice_lst[ID]
        )

        if response.status is CommandStatus.COMPLETED:
            invoice: schemas.Invoice = response.body
            self._invoice_table.source_model().update_invoice(invoice)
            self._enable_buttons(status=InvoiceStatus.PAID)
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Mark invoice as paid",
                f"""
                <p>Cannot mark invoice {invoice_lst[ID]} as paid</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot mark invoice {invoice_lst[ID]} as paid"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot()
    def cancel_invoice(self):
        invoice_lst = self._invoice_table.selected_invoice()

        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Mark invoice as cancelled",
            f"""
            <p>Do you really want to mark permanently this invoice as cancelled?</p>
            <p><strong>{invoice_lst[CODE]}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        response = api.client.mark_as_cancelled(
            invoice_lst[CLIENT_ID],
            invoice_id=invoice_lst[ID]
        )

        if response.status is CommandStatus.COMPLETED:
            invoice: schemas.Invoice = response.body
            self._invoice_table.source_model().update_invoice(invoice)
            self._enable_buttons(status=InvoiceStatus.CANCELLED)
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Mark invoice as cancelled",
                f"""
                <p>Cannot mark invoice {invoice_lst[ID]} as cancelled</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot mark invoice {invoice_lst[ID]} as cancelled"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot(schemas.Client)
    def set_current_client(self, client: schemas.Client) -> None:
        self._current_client = client

        self.client_lbl.setText(f"{client.name}")
        self.client_pix.setPixmap(
            self.active_pix if client.is_active else self.inactive_pix
        )

        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.set_client_filter(client.id)

        with QtCore.QSignalBlocker(self.all_ckb):
            self.all_ckb.setChecked(False)

        row_count = proxy.rowCount()
        self._invoice_table.select_and_show_row(row_count - 1)
        if row_count < 1:
            self._enable_buttons(enable=False)

    def set_default_filters(self) -> None:
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.reset_to_defaults()

        with QtCore.QSignalBlocker(self.all_ckb):
            self.all_ckb.setChecked(False)

        client = self._current_client
        if client is not None:
            self.client_lbl.setText(f"{client.name}")
            self.client_pix.setPixmap(
                self.active_pix if client.is_active else self.inactive_pix
            )

        with QtCore.QSignalBlocker(self.period_cmb):
            self.period_cmb.setCurrentText("Current Quarter")

        with QtCore.QSignalBlocker(self.status_cmb):
            self.status_cmb.setCurrentText("Not Cancelled")

        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    @QtCore.pyqtSlot(bool)
    def on_all_selection(self, checked: bool):
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.set_are_all_invoices_visible(checked)

        if checked:
            self.client_lbl.setText("All")
            self.client_pix.setPixmap(self.all_pix)
        else:
            client = self._current_client
            self.client_lbl.setText(f"{client.name}")
            self.client_pix.setPixmap(
                self.active_pix if client.is_active else self.inactive_pix
            )

        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    @QtCore.pyqtSlot(int)
    def on_period_selection(self, index: int) -> None:
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        period = self.period_cmb.itemData(index)
        proxy.set_period_filter(period)
        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    @QtCore.pyqtSlot(int)
    def on_status_selection(self, index: int) -> None:
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        status = self.status_cmb.itemText(index)
        proxy.set_status_filter(status)
        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def show_buttons(self, index: QtCore.QModelIndex) -> None:
        if index.isValid():
            proxy_model = cast(InvoiceFilterProxyModel, self._invoice_table.model())
            status = proxy_model.invoice_status_from_index(index)
            self._enable_buttons(status=status)
        else:
            self._enable_buttons(enable=False)

    @QtCore.pyqtSlot(schemas.Invoice)
    def on_invoice_creation(self, invoice: schemas.Invoice) -> None:
        self._invoice_table.source_model().add_invoice(invoice)

        self._invoice_table.sort_invoices()

        self._invoice_table.select_invoice(invoice.id)

        response = api.client.preview_invoice(
            invoice.client_id,
            invoice_id=invoice.id,
            mode=api.client.HtmlMode.ISSUE
        )
        if response.status is CommandStatus.COMPLETED:
            self.invoice_html_view.set_invoice(invoice.status, response.body, mode=InvoiceWebViewer.Mode.ISSUE)
            self.invoice_html_view.open()
            return

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"Dfacto - Delete invoice",
                f"""
                <p>Cannot preview invoice {invoice.code} created for {invoice.client.name}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot preview invoice {invoice.code} created for {invoice.client.name}"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot(int)
    def on_html_view_finished(self, result: int):
        match result:
            case InvoiceWebViewer.Action.DELETE:
                self.delete_invoice()
            case InvoiceWebViewer.Action.SEND:
                self.emit_invoice()
            case InvoiceWebViewer.Action.REMIND:
                self.reemit_invoice()
            case InvoiceWebViewer.Action.PAID:
                self.paid_invoice()
            case InvoiceWebViewer.Action.CANCEL:
                self.cancel_invoice()
            case InvoiceWebViewer.Action.TO_BASKET:
                # TODO
                pass
            case _:
                assert result == InvoiceWebViewer.Action.NO_ACTION

    def _enable_buttons(
        self,
        *,
        status: InvoiceStatus = None,
        enable: bool = True
    ) -> None:
        if enable:
            assert status is not None
            is_draft = status is InvoiceStatus.DRAFT
            is_emitted_or_reminded = status is InvoiceStatus.EMITTED or status is InvoiceStatus.REMINDED
            self.show_btn.setEnabled(True)
            self.emit_btn.setVisible(is_draft)
            self.remind_btn.setVisible(is_emitted_or_reminded)
            self.paid_btn.setVisible(is_emitted_or_reminded)
            self.delete_btn.setVisible(is_draft)
            self.cancel_btn.setVisible(is_emitted_or_reminded)
            self.basket_btn.setEnabled(True)
        else:
            assert status is None
            self.show_btn.setEnabled(False)
            self.emit_btn.setVisible(False)
            self.remind_btn.setVisible(False)
            self.paid_btn.setVisible(False)
            self.delete_btn.setVisible(False)
            self.cancel_btn.setVisible(False)
            self.basket_btn.setEnabled(False)


class InvoiceTable(QtWidgets.QTableView):
    def __init__(self, invoice_model: InvoiceTableModel, parent=None) -> None:
        super().__init__(parent=parent)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().hide()
        self.horizontalHeader().setStretchLastSection(True)
        self.setStyleSheet(
            "QTableView::item{border: 1px solid transparent;}"
            "QTableView::item:selected{color: blue;}"
            "QTableView::item:selected{background-color: rgba(0,0,255,64);}"
            "QTableView::item:selected:hover{border-color: rgba(0,0,255,128);}"
            "QTableView::item:hover{background: rgba(0,0,255,32);}"
        )
        self.setItemDelegate(QtUtil.NoFocusDelegate(self))
        # self.setItemDelegate(InvoiceTableDelegate(self))
        self.setSortingEnabled(True)

        proxy_model = InvoiceFilterProxyModel()
        proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        proxy_model.setSourceModel(invoice_model)
        self.setModel(proxy_model)

        # Prevent deselection: one row is always selected and a current index exists
        old_selection_model = self.selectionModel()
        new_selection_model = QtUtil.UndeselectableSelectionModel(
            self.model(), old_selection_model.parent()
        )
        self.setSelectionModel(new_selection_model)
        old_selection_model.deleteLater()

    def source_model(self) -> InvoiceTableModel:
        return cast(InvoiceTableModel, self.model().sourceModel())

    def sort_invoices(self) -> None:
        # Sort the invoice table on the date column and resize columns
        # to fit their content
        proxy = cast(InvoiceFilterProxyModel, self.model())
        sort_order = proxy.sortOrder()
        sort_column = proxy.sortColumn()
        if sort_column < 0:
            sort_column = 2 if proxy.are_all_invoices_visible() else 1
        self.sortByColumn(sort_column, sort_order)
        for column in range(proxy.columnCount()):
            self.horizontalHeader().setSectionResizeMode(
                column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
            )

    def select_and_show_row(self, row: int) -> None:
        self.selectRow(row)
        self.scrollTo(
            self.model().index(row, 1),
            QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible
        )

    def select_first_invoice(self) -> None:
        self.select_and_show_row(0)

    def select_invoice(self, invoice_id: int) -> None:
        proxy_model = cast(InvoiceFilterProxyModel, self.model())
        source_model = cast(InvoiceTableModel, proxy_model.sourceModel())
        source_index = source_model.index_from_invoice_id(invoice_id)
        proxy_index = proxy_model.mapFromSource(source_index)
        if proxy_index.isValid():
            self.select_and_show_row(proxy_index.row())

    def selected_invoice(self) -> InvoiceItem:
        proxy_index = self.selectionModel().selectedIndexes()[-1]
        proxy_model = cast(InvoiceFilterProxyModel, self.model())
        return proxy_model.invoice_from_index(proxy_index)

    def selected_source_index(self) -> QtCore.QModelIndex:
        try:
            proxy_index = self.selectionModel().selectedIndexes()[-1]
        except IndexError:
            return QtCore.QModelIndex()

        return self.model().mapToSource(proxy_index)

    def current_source_index(self) -> QtCore.QModelIndex:
        proxy_index = self.currentIndex()
        return self.model().mapToSource(proxy_index)

    def contextMenuEvent(self, event):
        # index = self.selected_source_index()
        index = self.current_source_index()
        if not index.isValid():
            return

        proxy_model = cast(InvoiceFilterProxyModel, self.model())
        source_model = cast(InvoiceTableModel, proxy_model.sourceModel())

        resources = Config.dfacto_settings.resources
        test_action = QtUtil.createAction(
            self, 'Test',
            slot=lambda: print("Test"), # noqa
            icon=QtGui.QIcon(f'{resources}/ok.png'),
            # shortcut="CTRL+ALT+P",
            tip='Test a context menu action')

        menu = QtWidgets.QMenu(self)
        menu.addAction(test_action)
        # menu.addSeparator()
        # menu.addActions((
        #     globalActions['CUT'],
        #     globalActions['COPY'],
        #     globalActions['PASTE'],
        #     globalActions['DELETE']
        # ))
        menu.exec(event.globalPos())


# class InvoiceTableDelegate(QtUtil.NoFocusDelegate):
#     previous_status: Optional[InvoiceStatus]
#
#     def __init__(self, parent=None) -> None:
#         super().__init__(parent=parent)
#
#     def createEditor(
#         self,
#         parent: QtWidgets.QWidget,
#         options: QtWidgets.QStyleOptionViewItem,
#         index: QtCore.QModelIndex,
#     ) -> QtWidgets:
#         proxy_model = cast(InvoiceFilterProxyModel, index.model())
#         source_index = proxy_model.mapToSource(index)
#         column = source_index.column()
#
#         if column == STATUS:
#             editor = QtWidgets.QComboBox(parent)
#             editor.setFrame(False)
#             editor.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
#             tip = "Select Invoice status"
#             editor.setToolTip(tip)
#             editor.setStatusTip(tip)
#             for s in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
#                 editor.addItem(s.name, userData=s)
#             # editor.model().sort(0)
#             width = editor.minimumSizeHint().width()
#             editor.view().setMinimumWidth(width)
#             self.previous_status = None
#             return editor
#
#         return super().createEditor(parent, options, index)
#
#     def setEditorData(
#         self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex
#     ) -> None:
#         proxy_model = cast(InvoiceFilterProxyModel, index.model())
#         source_index = proxy_model.mapToSource(index)
#         column = source_index.column()
#
#         if column == STATUS:
#             editor: QtWidgets.QComboBox
#             status = proxy_model.data(index, InvoiceTableModel.UserRoles.StatusRole)
#             if status:
#                 self.previous_status = status
#                 editor.setCurrentText(status.name)
#                 editor.showPopup()
#                 return
#
#         super().setEditorData(editor, index)
#
#     def setModelData(
#         self,
#         editor: QtWidgets.QWidget,
#         model: QtCore.QAbstractItemModel,
#         index: QtCore.QModelIndex,
#     ) -> None:
#         source_index = model.mapToSource(index)
#         column = source_index.column()
#
#         if column == STATUS:
#             editor: QtWidgets.QComboBox
#             status = editor.currentData()
#             if status != self.previous_status:
#                 print(f"setModelData: row: {source_index.row()}, status: {status.name}, previou status: {self.previous_status.name}")
#                 model.setData(index, status, QtCore.Qt.ItemDataRole.EditRole)
#             return
#
#         super().setModelData(editor, model, index)
#
#     def updateEditorGeometry(
#         self,
#         editor: QtWidgets.QWidget,
#         option: QtWidgets.QStyleOptionViewItem,
#         index: QtCore.QModelIndex,
#     ) -> None:
#         proxy_model = cast(InvoiceFilterProxyModel, index.model())
#         source_index = proxy_model.mapToSource(index)
#         column = source_index.column()
#
#         if column == STATUS:
#             rect = option.rect
#             rect.setWidth(rect.width() + 20)
#             editor.setGeometry(option.rect)
#             return
#
#         super().updateEditorGeometry(editor, option, index)


class InvoiceFilterProxyModel(QtCore.QSortFilterProxyModel):
    _client_filter = -1
    _period_filter = PeriodFilter.CURRENT_QUARTER.as_period()
    _status_filter = "Not Cancelled"
    _are_all_invoices_visible = False

    @classmethod
    def client_filter(cls) -> int:
        return cls._client_filter

    def set_client_filter(self, value: int) -> None:
        InvoiceFilterProxyModel._client_filter = value
        InvoiceFilterProxyModel._are_all_invoices_visible = False
        self.invalidateFilter()

    @classmethod
    def period_filter(cls) -> Period:
        return cls._period_filter

    def set_period_filter(self, value: Period) -> None:
        InvoiceFilterProxyModel._period_filter = value
        self.invalidateFilter()

    @classmethod
    def status_filter(cls) -> str:
        return cls._status_filter

    def set_status_filter(self, value: str) -> None:
        InvoiceFilterProxyModel._status_filter = value
        self.invalidateFilter()

    @classmethod
    def are_all_invoices_visible(cls) -> bool:
        return cls._are_all_invoices_visible

    def set_are_all_invoices_visible(self, value: bool) -> None:
        InvoiceFilterProxyModel._are_all_invoices_visible = value
        self.invalidateFilter()

    def reset_to_defaults(self) -> None:
        InvoiceFilterProxyModel._are_all_invoices_visible = False
        InvoiceFilterProxyModel._period_filter = PeriodFilter.CURRENT_QUARTER.as_period()
        InvoiceFilterProxyModel._status_filter = "Not Cancelled"
        self.invalidateFilter()

    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
        source_model = self.sourceModel()

        if left.column() == CREATED_ON:
            left_date = source_model.data(
                left,
                role=InvoiceTableModel.UserRoles.DateRole
            )
            right_date = source_model.data(
                right,
                role=InvoiceTableModel.UserRoles.DateRole
            )
            return left_date < right_date
        return super().lessThan(left, right)

    def filterAcceptsColumn(
        self, source_column: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        if source_column in (ID, CLIENT_ID):
            return False
        if source_column == CLIENT_NAME:
            return self.are_all_invoices_visible()
        return True

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        source_model = self.sourceModel()

        if self._are_all_invoices_visible:
            ok_client = True
        else:
            index = source_model.index(source_row, CLIENT_ID, source_parent)
            client_id = self.sourceModel().data(index, QtCore.Qt.ItemDataRole.DisplayRole)
            ok_client = int(client_id) == self.client_filter()

        if self._period_filter == Period():
            ok_period = True
        else:
            index = source_model.index(source_row, CREATED_ON, source_parent)
            date_ = source_model.data(index, InvoiceTableModel.UserRoles.DateRole)
            period = self.period_filter()
            ok_period = period.start <= date_ <= period.end

        index = source_model.index(source_row, STATUS, source_parent)
        status = source_model.data(index, QtCore.Qt.ItemDataRole.DisplayRole)
        if self._status_filter == "Not Cancelled":
            ok_status = status.lower() != InvoiceStatus.CANCELLED.name.lower()
        else:
            ok_status = status.lower() == self.status_filter().lower()

        return ok_client and ok_period and ok_status

    def invoice_from_index(self, index: QtCore.QModelIndex) -> InvoiceItem:
        source_model = cast(InvoiceTableModel, self.sourceModel())
        source_index = self.mapToSource(index)
        return source_model.invoice_from_index(source_index)

    def invoice_status_from_index(self, index: QtCore.QModelIndex) -> InvoiceStatus:
        source_model = cast(InvoiceTableModel, self.sourceModel())
        source_index = self.mapToSource(index)
        return source_model.data(source_index, InvoiceTableModel.UserRoles.StatusRole)
