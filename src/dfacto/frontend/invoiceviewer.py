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
from dfacto.backend.api import CommandStatus, CommandReport
from dfacto.backend.models.invoice import InvoiceStatus
from dfacto.backend.util import Period, PeriodFilter
from dfacto.util import qtutil as QtUtil
from . import get_current_company
from .invoice_web_view import InvoiceWebViewer

logger = logging.getLogger(__name__)

InvoiceItem = list[int, int, str, str, datetime, float, float, float, InvoiceStatus]

ID, CLIENT_ID, CLIENT_NAME, CODE, CREATED_ON, RAW_AMOUNT, VAT, NET_AMOUNT, STATUS = range(9)
VAT_COLUMNS = (CODE, CREATED_ON, RAW_AMOUNT, VAT, NET_AMOUNT, STATUS)
NOVAT_COLUMNS = (CODE, CREATED_ON, RAW_AMOUNT, STATUS)


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
            "Amount",
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

    def get_html_preview(
        self, invoice_id: int, mode: api.client.HtmlMode
    ) -> tuple[Optional[str], CommandReport]:
        response = api.client.preview_invoice(
            self._get_client_of_invoice(invoice_id),
            invoice_id=invoice_id,
            mode=mode
        )

        if response.status is not CommandStatus.FAILED:
            return response.body, response.report

        QtUtil.raise_fatal_error(
            f"Cannot get HTML preview"
            f" - Reason is: {response.reason}"
        )

    def delete_invoice(self, invoice_id: int) -> CommandReport:
        response = api.client.delete_invoice(
            self._get_client_of_invoice(invoice_id),
            invoice_id=invoice_id
        )

        if response.status is CommandStatus.COMPLETED:
            self.remove_invoice(invoice_id)
            return response.report

        if response.status is CommandStatus.REJECTED:
            return response.report

        QtUtil.raise_fatal_error(
            f"Cannot delete invoice - Reason is: {response.reason}"
        )

    def mark_invoice_as(self, invoice_id: int, status: InvoiceStatus) -> CommandReport:
        if status is InvoiceStatus.EMITTED:
            action = api.client.mark_as_emitted
        elif status is InvoiceStatus.REMINDED:
            action = api.client.mark_as_reminded
        elif status is InvoiceStatus.PAID:
            action = api.client.mark_as_paid
        elif status is InvoiceStatus.CANCELLED:
            action = api.client.mark_as_cancelled
        else:
            raise ValueError(f"Cannot mark invoice as {status.name}")

        # match status:
        #     case InvoiceStatus.EMITTED:
        #         action = api.client.mark_as_emitted
        #     case InvoiceStatus.REMINDED:
        #         action = api.client.mark_as_reminded
        #     case InvoiceStatus.PAID:
        #         action = api.client.mark_as_paid
        #     case InvoiceStatus.CANCELLED:
        #         action = api.client.mark_as_cancelled
        #     case _:
        #         raise ValueError(f"Cannot mark invoice as {status.name}")

        response = action(
            self._get_client_of_invoice(invoice_id),
            invoice_id=invoice_id
        )

        if response.status is CommandStatus.COMPLETED:
            invoice: schemas.Invoice = response.body
            self.update_invoice(invoice)
            return response.report

        if response.status is CommandStatus.REJECTED:
            return response.report

        QtUtil.raise_fatal_error(
            f"Cannot mark invoice as {status.name} - Reason is: {response.reason}"
        )

    def move_in_basket(self, client_id: int, invoice_id: int) -> CommandReport:
        response = api.client.move_in_basket(client_id, invoice_id=invoice_id)

        if response.status is CommandStatus.COMPLETED:
            self.remove_invoice(invoice_id)
            return response.report

        if response.status is CommandStatus.REJECTED:
            return response.report

        QtUtil.raise_fatal_error(
            f"Cannot move invoice in basket - Reason is: {response.reason}"
        )

    def copy_in_basket(self, client_id: int, invoice_id: int) -> CommandReport:
        response = api.client.copy_in_basket(client_id, invoice_id=invoice_id)

        if response.status is not CommandStatus.FAILED:
            return response.report

        QtUtil.raise_fatal_error(
            f"Cannot copy invoice in basket - Reason is: {response.reason}"
        )

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

    def _invoice_id_from_index(self, index: QtCore.QModelIndex) -> Optional[int]:
        if index.isValid():
            row = index.row()
            if 0 <= row < self.rowCount():
                return self._invoice_ids[row]
        return None

    def _get_client_of_invoice(self, invoice_id: int) -> int:
        try:
            invoice = self._invoices[invoice_id]
        except KeyError:
            return -1
        return invoice[CLIENT_ID]


class InvoiceViewer(QtUtil.QFramedWidget):
    basket_updated = QtCore.pyqtSignal(int)     # client id

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
        self.status_btn = QtWidgets.QToolButton()
        self.status_btn.setText('Status filter ')
        self.status_btn.setToolTip("Filter on status")
        self.status_btn.setStatusTip("Filter on status")
        self.status_btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
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
        tool_layout.addWidget(self.status_btn)
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

        self.status_menu = QtWidgets.QMenu(self)
        self.status_actions: dict[str, QtWidgets.QCheckBox] = dict()
        action_ckb = QtWidgets.QCheckBox("All", self.status_menu)
        ckb_action = QtWidgets.QWidgetAction(self.status_menu)
        ckb_action.setDefaultWidget(action_ckb)
        self.status_menu.addAction(ckb_action)
        action_ckb.setChecked(False)
        action_ckb.stateChanged.connect(self.on_all_selected)
        self.status_actions["all"] = action_ckb
        for status in InvoiceStatus:
            action_ckb = QtWidgets.QCheckBox(status.name.title(), self.status_menu)
            ckb_action = QtWidgets.QWidgetAction(self.status_menu)
            ckb_action.setDefaultWidget(action_ckb)
            self.status_menu.addAction(ckb_action)
            if status is not InvoiceStatus.CANCELLED:
                action_ckb.setChecked(True)
            action_ckb.stateChanged.connect(
                lambda state, s=status: self.on_status_changed(s.name.lower(), state)
            )
            self.status_actions[status.name.lower()] = action_ckb
        self.status_btn.setMenu(self.status_menu)

        self.all_ckb.toggled.connect(self.on_all_selection)
        self.period_cmb.activated.connect(self.on_period_selection)
        self.reset_btn.clicked.connect(self.set_default_filters)

        self._invoice_table.selectionModel().currentChanged.connect(self.show_buttons)

        self.basket_btn.clicked.connect(self.basket_from_invoice)
        self.show_btn.clicked.connect(
            lambda: self._open_html_view(mode=api.client.HtmlMode.SHOW)
        )
        self.emit_btn.clicked.connect(
            lambda: self._open_html_view(mode=api.client.HtmlMode.ISSUE)
        )
        self.remind_btn.clicked.connect(
            lambda: self._open_html_view(mode=api.client.HtmlMode.REMIND)
        )
        self.paid_btn.clicked.connect(
            lambda: self._mark_invoice_as(InvoiceStatus.PAID, confirm=True)
        )
        self.delete_btn.clicked.connect(self.delete_invoice)
        self.cancel_btn.clicked.connect(
            lambda: self._mark_invoice_as(InvoiceStatus.CANCELLED, confirm=True)
        )

        self.invoice_html_view.finished.connect(self.on_html_view_finished)

        self._current_client: Optional[schemas.Client] = None
        self.all_ckb.setChecked(False)

    def load_invoices(self) -> None:
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.set_is_vat_visible(not get_current_company().no_vat)
        self._invoice_table.source_model().load_invoices()
        self._invoice_table.sort_invoices()
        self.set_default_filters()

    @QtCore.pyqtSlot()
    def delete_invoice(self) -> None:
        invoice_table = self._invoice_table
        invoice = invoice_table.selected_invoice()

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

        report = invoice_table.source_model().delete_invoice(invoice[ID])

        if report.status is not CommandStatus.COMPLETED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Delete invoice",
                f"""
                <p>Cannot delete invoice {invoice[ID]} of client {invoice[CLIENT_NAME]}</p>
                <p><strong>Reason is: {report.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )

    def basket_from_invoice(self) -> None:
        invoice_table = self._invoice_table
        invoice = invoice_table.selected_invoice()

        if invoice[STATUS] is InvoiceStatus.DRAFT:
            self._move_in_basket(invoice)
        else:
            self._copy_in_basket(invoice)

    @QtCore.pyqtSlot(object)
    def set_current_client(self, client: Optional[schemas.Client]) -> None:
        self._current_client = client
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())

        if client is None:
            logger.info("No client exists or all clients are hidden, disable invoices interactions")
            self.client_lbl.clear()
            self.client_pix.clear()
            self._enable_filters(False)
            self._enable_buttons(enable=False)
            proxy.set_client_filter(-1)
            return

        # A client is selected and it is visible
        logger.info(f"Show invoices of client: %s", client.name)
        self._enable_filters(True)
        self.client_lbl.setText(f"{client.name}")
        self.client_pix.setPixmap(
            self.active_pix if client.is_active else self.inactive_pix
        )

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

        for ckb in self.status_actions.values():
            status = ckb.text().lower()
            with QtCore.QSignalBlocker(ckb):
                ckb.setChecked(status != "all" and status != "cancelled")

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
    def on_all_selected(self, state: int) -> None:
        if state == QtCore.Qt.CheckState.Checked.value:
            selection = ["draft", "emitted", "reminded", "paid", "cancelled"]
            for ckb in self.status_actions.values():
                with QtCore.QSignalBlocker(ckb):
                    ckb.setChecked(True)
        else:
            selection = []
            for ckb in self.status_actions.values():
                with QtCore.QSignalBlocker(ckb):
                    ckb.setChecked(False)
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.set_statuses_filter(selection)
        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    def on_status_changed(self, status: str, state: int) -> None:
        ckb = self.status_actions["all"]
        if state == QtCore.Qt.CheckState.Checked.value:
            with QtCore.QSignalBlocker(ckb):
                ckb.setChecked(
                    all([c.isChecked() for s, c in self.status_actions.items() if s != "all"])
                )
        else:
            with QtCore.QSignalBlocker(ckb):
                ckb.setChecked(False)
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.toggle_status(status)
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

        self._open_html_view(mode=api.client.HtmlMode.CREATE)

    @QtCore.pyqtSlot(int)
    def on_html_view_finished(self, result: int):
        if result == InvoiceWebViewer.Action.DELETE:
            self.delete_invoice()
        elif result == InvoiceWebViewer.Action.SEND:
            self._mark_invoice_as(InvoiceStatus.EMITTED, confirm=False)
        elif result == InvoiceWebViewer.Action.REMIND:
            self._mark_invoice_as(InvoiceStatus.REMINDED, confirm=False)
        elif result == InvoiceWebViewer.Action.PAID:
            self._mark_invoice_as(InvoiceStatus.PAID, confirm=True)
        elif result == InvoiceWebViewer.Action.CANCEL:
            self._mark_invoice_as(InvoiceStatus.CANCELLED, confirm=True)
        elif result == InvoiceWebViewer.Action.TO_BASKET:
            self.basket_from_invoice()
        else:
            assert result == InvoiceWebViewer.Action.NO_ACTION

        # match result:
        #     case InvoiceWebViewer.Action.DELETE:
        #         self.delete_invoice()
        #     case InvoiceWebViewer.Action.SEND:
        #         self._mark_invoice_as(InvoiceStatus.EMITTED, confirm=False)
        #     case InvoiceWebViewer.Action.REMIND:
        #         self._mark_invoice_as(InvoiceStatus.REMINDED, confirm=False)
        #     case InvoiceWebViewer.Action.PAID:
        #         self._mark_invoice_as(InvoiceStatus.PAID, confirm=True)
        #     case InvoiceWebViewer.Action.CANCEL:
        #         self._mark_invoice_as(InvoiceStatus.CANCELLED, confirm=True)
        #     case InvoiceWebViewer.Action.TO_BASKET:
        #         # TODO
        #         pass
        #     case _:
        #         assert result == InvoiceWebViewer.Action.NO_ACTION

    def _enable_filters(self, enable: bool) -> None:
        self.all_ckb.setEnabled(enable)
        self.period_cmb.setEnabled(enable)
        self.status_btn.setEnabled(enable)
        self.reset_btn.setEnabled(enable)

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

    def _open_html_view(self, mode: api.client.HtmlMode) -> None:
        if mode is api.client.HtmlMode.CREATE:
            viewer_mode = InvoiceWebViewer.Mode.ISSUE
        elif mode is api.client.HtmlMode.SHOW:
            viewer_mode = InvoiceWebViewer.Mode.SHOW
        elif mode is api.client.HtmlMode.ISSUE:
            viewer_mode = InvoiceWebViewer.Mode.CONFIRM
        elif mode is api.client.HtmlMode.REMIND:
            viewer_mode = InvoiceWebViewer.Mode.CONFIRM
        else:
            viewer_mode = InvoiceWebViewer.Mode.SHOW

        # match mode:
        #     case api.client.HtmlMode.CREATE:
        #         viewer_mode = InvoiceWebViewer.Mode.ISSUE
        #     case api.client.HtmlMode.SHOW:
        #         viewer_mode = InvoiceWebViewer.Mode.SHOW
        #     case api.client.HtmlMode.ISSUE:
        #         viewer_mode = InvoiceWebViewer.Mode.CONFIRM
        #     case api.client.HtmlMode.REMIND:
        #         viewer_mode = InvoiceWebViewer.Mode.CONFIRM
        #     case _:
        #         viewer_mode = InvoiceWebViewer.Mode.SHOW

        invoice_table = self._invoice_table
        invoice = invoice_table.selected_invoice()
        invoice_id = invoice[ID]

        html, report = invoice_table.source_model().get_html_preview(
            invoice_id,
            mode=mode
        )

        if html is not None:
            status = cast(InvoiceStatus, invoice[STATUS])
            self.invoice_html_view.set_invoice(invoice_id, status, html, mode=viewer_mode)
            self.invoice_html_view.open()
            return

        QtWidgets.QMessageBox.warning(
            None,  # type: ignore
            f"{QtWidgets.QApplication.applicationName()} - Invoice view",
            f"""
            <p>Cannot show invoice {invoice[CODE]} of client {invoice[CLIENT_NAME]}</p>
            <p><strong>Reason is: {report.reason}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Close,
        )

    def _mark_invoice_as(self, status: InvoiceStatus, confirm: bool = False) -> None:
        invoice_table = self._invoice_table
        invoice = invoice_table.selected_invoice()
        status_txt = status.name.lower()

        if confirm:
            reply = QtWidgets.QMessageBox.warning(
                self,  # noqa
                f"{QtWidgets.QApplication.applicationName()} - Mark invoice as {status_txt}",
                f"""
                <p>Do you really want to mark permanently this invoice as {status_txt}?</p>
                <p><strong>{invoice[CODE]}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return

        report = invoice_table.source_model().mark_invoice_as(invoice[ID], status)

        if report.status is CommandStatus.COMPLETED:
            self._enable_buttons(status=status)
            return

        QtWidgets.QMessageBox.warning(
            None,  # type: ignore
            f"{QtWidgets.QApplication.applicationName()} - Mark invoice as {status_txt}",
            f"""
            <p>Cannot mark invoice {invoice[ID]} as {status_txt}</p>
            <p><strong>Reason is: {report.reason}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Close,
        )

    def _move_in_basket(self, invoice: InvoiceItem):
        report = self._invoice_table.source_model().move_in_basket(
            invoice[CLIENT_ID],
            invoice[ID]
        )

        if report.status is CommandStatus.COMPLETED:
            self.basket_updated.emit(invoice[CLIENT_ID])
        else:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Move invoice in basket",
                f"""
                <p>Cannot move invoice {invoice[CODE]} in basket of client {invoice[CLIENT_NAME]}</p>
                <p><strong>Reason is: {report.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )

    def _copy_in_basket(self, invoice: InvoiceItem):
        report = self._invoice_table.source_model().copy_in_basket(
            invoice[CLIENT_ID],
            invoice[ID]
        )

        if report.status is CommandStatus.COMPLETED:
            self.basket_updated.emit(invoice[CLIENT_ID])
        else:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"{QtWidgets.QApplication.applicationName()} - Copy invoice in basket",
                f"""
                <p>Cannot copy invoice {invoice[CODE]} in basket of client {invoice[CLIENT_NAME]}</p>
                <p><strong>Reason is: {report.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )


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


class InvoiceFilterProxyModel(QtCore.QSortFilterProxyModel):
    _is_vat_visible = True
    _client_filter = -1
    _period_filter = PeriodFilter.CURRENT_QUARTER.as_period()
    _status_filter = "Not Cancelled"
    _statuses_filter = ["draft", "emitted", "reminded", "paid"]
    _are_all_invoices_visible = False

    def __init__(self):
        super().__init__()
        company = get_current_company()
        self.set_is_vat_visible(not company.no_vat)

    @classmethod
    def is_vat_visible(cls) -> bool:
        return cls._is_vat_visible

    def set_is_vat_visible(self, value: bool) -> None:
        InvoiceFilterProxyModel._is_vat_visible = value
        self.invalidateFilter()

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
    def statuses_filter(cls) -> list[str]:
        return cls._statuses_filter

    def set_statuses_filter(self, values: list[str]) -> None:
        InvoiceFilterProxyModel._statuses_filter = values
        self.invalidateFilter()

    def toggle_status(self, value: str) -> None:
        current_filter = InvoiceFilterProxyModel._statuses_filter
        if value in current_filter:
            current_filter.remove(value)
        else:
            current_filter.append(value)
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
        InvoiceFilterProxyModel._statuses_filter = ["draft", "emitted", "reminded", "paid"]
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
        if self._is_vat_visible:
            if source_column in VAT_COLUMNS:
                return True
            return False
        else:
            if source_column in NOVAT_COLUMNS:
                return True
            return False

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
        ok_status = status.lower() in self.statuses_filter()

        return ok_client and ok_period and ok_status

    def invoice_from_index(self, index: QtCore.QModelIndex) -> InvoiceItem:
        source_model = cast(InvoiceTableModel, self.sourceModel())
        source_index = self.mapToSource(index)
        return source_model.invoice_from_index(source_index)

    def invoice_status_from_index(self, index: QtCore.QModelIndex) -> InvoiceStatus:
        source_model = cast(InvoiceTableModel, self.sourceModel())
        source_index = self.mapToSource(index)
        return source_model.data(source_index, InvoiceTableModel.UserRoles.StatusRole)
