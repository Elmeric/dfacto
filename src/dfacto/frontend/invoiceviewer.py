# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import IntEnum
from typing import Any, Optional, cast

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets
from babel.dates import format_date
from babel.numbers import format_currency

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandReport, CommandStatus
from dfacto.backend.models.invoice import InvoiceStatus
from dfacto.backend.util import DatetimeRange, Period, PeriodFilter
from dfacto.util import qtutil as QtUtil

from . import get_current_company
from .invoice_log_view import StatusLogEditor
from .invoice_web_view import InvoiceWebViewer

logger = logging.getLogger(__name__)

InvoiceItem = tuple[
    int,
    int,
    str,
    str,
    datetime,
    Decimal,
    Decimal,
    Decimal,
    InvoiceStatus,
    bool,
    datetime,
]

(
    ID,
    CLIENT_ID,
    CLIENT_NAME,
    CODE,
    CREATED_ON,
    RAW_AMOUNT,
    VAT,
    NET_AMOUNT,
    STATUS,
    IS_LATE,
    CHANGED_ON,
) = range(11)
VAT_COLUMNS = (CODE, CREATED_ON, RAW_AMOUNT, VAT, NET_AMOUNT, STATUS, IS_LATE)
NOVAT_COLUMNS = (CODE, CREATED_ON, RAW_AMOUNT, STATUS, IS_LATE)


class InvoiceTableModel(QtCore.QAbstractTableModel):
    STATUS_COLOR = {
        InvoiceStatus.PAID: "darkGreen",
        InvoiceStatus.EMITTED: "darkslateblue",
        InvoiceStatus.CANCELLED: "lightgrey",
        InvoiceStatus.REMINDED: "darkorange",
        InvoiceStatus.DRAFT: "darkgrey",
        "ERROR": "firebrick",
    }

    class UserRoles(IntEnum):
        DateRole = QtCore.Qt.ItemDataRole.UserRole + 1
        StatusRole = QtCore.Qt.ItemDataRole.UserRole + 2
        ClientRole = QtCore.Qt.ItemDataRole.UserRole + 3
        IsLateRole = QtCore.Qt.ItemDataRole.UserRole + 4

    some_payment_needed = QtCore.pyqtSignal()
    pending_payment_created = QtCore.pyqtSignal(schemas.Amount)
    pending_payment_changed = QtCore.pyqtSignal(schemas.Amount)
    sales_summary_created = QtCore.pyqtSignal(
        schemas.Amount, schemas.Amount
    )  # last and current quarter sales
    sales_summary_changed = QtCore.pyqtSignal(
        schemas.Amount, schemas.Amount
    )  # relative last and current quarter sales

    def __init__(self) -> None:
        super().__init__()
        self._headers = [
            _("Id"),
            _("Client Id"),
            _("Client name"),
            _("Code"),
            _("Date"),
            _("Amount"),
            _("VAT"),
            _("Net amount"),
            _("Status"),
            _("Late ?"),
            _("Changed on"),
        ]
        self._client_id: int = -1
        self._invoices: dict[int, InvoiceItem] = {}
        self._invoice_ids: list[int] = []
        resources = Config.dfacto_settings.resources
        self._is_late_icon = QtGui.QIcon(f"{resources}/alarm.png")

    def load_invoices(self) -> None:
        response = api.client.get_all_invoices()

        if response.status is CommandStatus.COMPLETED:
            invoices: list[schemas.Invoice] = response.body
            self.clear_invoices()
            self.add_invoices(invoices)
            return

        msg = _("Cannot retrieve invoices")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

    def get_invoice(self, invoice_id: int) -> schemas.Invoice:
        response = api.client.get_invoice(invoice_id=invoice_id)

        if response.status is not CommandStatus.FAILED:
            invoice = cast(schemas.Invoice, response.body)
            return invoice

        msg = _("Cannot get invoice")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} {invoice_id} - {reason} {response.reason}")

    def get_html_preview(
        self, invoice_id: int, mode: api.client.HtmlMode, translations
    ) -> tuple[Optional[str], CommandReport]:
        response = api.client.preview_invoice(
            self._get_client_id_of_invoice(invoice_id),
            invoice_id=invoice_id,
            mode=mode,
            translations=translations,
        )

        if response.status is not CommandStatus.FAILED:
            return response.body, response.report

        msg = _("Cannot get HTML preview")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

    def delete_invoice(self, invoice_id: int) -> CommandReport:
        response = api.client.delete_invoice(
            self._get_client_id_of_invoice(invoice_id), invoice_id=invoice_id
        )

        if response.status is CommandStatus.COMPLETED:
            self.remove_invoice(invoice_id)
            return response.report

        if response.status is CommandStatus.REJECTED:
            return response.report

        msg = _("Cannot delete invoice")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

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
            raise ValueError(_("Cannot mark invoice as %s") % status.name)

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
            self._get_client_id_of_invoice(invoice_id), invoice_id=invoice_id
        )

        if response.status is CommandStatus.COMPLETED:
            invoice: schemas.Invoice = response.body
            self.update_invoice(invoice)
            if status is InvoiceStatus.EMITTED:
                self.pending_payment_changed.emit(invoice.amount)
            elif status is InvoiceStatus.REMINDED:
                pass
            else:
                # status is PAID or CANCELLED
                self.pending_payment_changed.emit(-invoice.amount)
            if status is InvoiceStatus.PAID:
                pay_date = invoice.paid_on
                if pay_date in Period.from_last_quarter():
                    self.sales_summary_changed.emit(invoice.amount, schemas.Amount())
                elif pay_date in Period.from_current_quarter():
                    self.sales_summary_changed.emit(schemas.Amount(), invoice.amount)
            return response.report

        if response.status is CommandStatus.REJECTED:
            return response.report

        msg = _("Cannot mark invoice as %s") % status.name
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

    def move_in_basket(self, client_id: int, invoice_id: int) -> CommandReport:
        response = api.client.move_in_basket(client_id, invoice_id=invoice_id)

        if response.status is CommandStatus.COMPLETED:
            self.remove_invoice(invoice_id)
            return response.report

        if response.status is CommandStatus.REJECTED:
            return response.report

        msg = _("Cannot move invoice in basket")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

    def update_invoice_history(
        self, invoice_id: int, log: dict[InvoiceStatus, DatetimeRange]
    ) -> CommandReport:
        status = self._invoices[invoice_id][STATUS]
        prev_pay_date = None
        if status is InvoiceStatus.PAID:
            prev_pay_date = self._invoices[invoice_id][CHANGED_ON]

        response = api.client.update_invoice_history(invoice_id=invoice_id, log=log)

        if response.status is not CommandStatus.FAILED:
            invoice = cast(schemas.Invoice, response.body)
            self.update_invoice(invoice)
            if invoice.status is InvoiceStatus.PAID:
                pay_date = invoice.paid_on
                amount = invoice.amount
                null_amount = schemas.Amount()
                if prev_pay_date in Period.from_current_quarter():
                    if pay_date in Period.from_current_quarter():
                        pass
                    elif pay_date in Period.from_last_quarter():
                        self.sales_summary_changed.emit(amount, -amount)
                    else:
                        self.sales_summary_changed.emit(null_amount, -amount)
                elif prev_pay_date in Period.from_last_quarter():
                    if pay_date in Period.from_current_quarter():
                        self.sales_summary_changed.emit(-amount, amount)
                    elif pay_date in Period.from_last_quarter():
                        pass
                    else:
                        self.sales_summary_changed.emit(-amount, null_amount)
                else:
                    if pay_date in Period.from_current_quarter():
                        self.sales_summary_changed.emit(null_amount, amount)
                    elif pay_date in Period.from_last_quarter():
                        self.sales_summary_changed.emit(amount, null_amount)
                    else:
                        pass
            return response.report

        msg = _("Cannot update history of invoice %s") % invoice_id
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

    def copy_in_basket(self, client_id: int, invoice_id: int) -> CommandReport:
        response = api.client.copy_in_basket(client_id, invoice_id=invoice_id)

        if response.status is not CommandStatus.FAILED:
            return response.report

        msg = _("Cannot copy invoice in basket")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

    def revert_to_previous_status(
        self, invoice_id: int
    ) -> tuple[CommandReport, InvoiceStatus]:
        prev_status = self._invoices[invoice_id][STATUS]
        pay_date = self._invoices[invoice_id][CHANGED_ON]
        response = api.client.revert_invoice_status(invoice_id=invoice_id)

        if response.status is not CommandStatus.FAILED:
            invoice: schemas.Invoice = response.body
            self.update_invoice(invoice)
            status = invoice.status
            if status in (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED):
                if prev_status is not InvoiceStatus.REMINDED:
                    self.pending_payment_changed.emit(invoice.amount)
            else:
                self.pending_payment_changed.emit(-invoice.amount)
            if prev_status is InvoiceStatus.PAID:
                if pay_date in Period.from_last_quarter():
                    self.sales_summary_changed.emit(-invoice.amount, schemas.Amount())
                elif pay_date in Period.from_current_quarter():
                    self.sales_summary_changed.emit(schemas.Amount(), -invoice.amount)
            return response.report, status

        msg = _("Cannot revert invoice to its previous status")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")

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

        delta = Config.dfacto_settings.due_date_delta
        one_late = False
        pending_payments = schemas.Amount()
        last_quarter_sales = schemas.Amount()
        current_quarter_sales = schemas.Amount()
        for invoice in invoices:
            invoice_id = invoice.id
            status = invoice.status
            amount = invoice.amount
            self._invoice_ids.append(invoice_id)
            date_ = (
                invoice.created_on
                if status is InvoiceStatus.DRAFT
                else invoice.issued_on
            )
            is_late = False
            if status in (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED):
                is_late = date_ + timedelta(days=delta) < datetime.now()
                one_late = is_late
                pending_payments += amount
            if status is InvoiceStatus.PAID:
                pay_date = invoice.paid_on
                if pay_date in Period.from_last_quarter():
                    last_quarter_sales += amount
                if pay_date in Period.from_current_quarter():
                    current_quarter_sales += amount
            self._invoices[invoice_id] = (
                invoice_id,
                invoice.client_id,
                invoice.client.name,
                invoice.code,
                date_,
                amount.raw,
                amount.vat,
                amount.net,
                status,
                is_late,
                invoice.changed_to_on(status),
            )

        self.endInsertRows()
        if one_late:
            QtCore.QTimer.singleShot(
                1000,  # To let the splash screen to finish
                lambda: self.some_payment_needed.emit(),
            )
        self.pending_payment_created.emit(pending_payments)
        self.sales_summary_created.emit(last_quarter_sales, current_quarter_sales)

    def add_invoice(self, invoice: schemas.Invoice) -> None:
        row = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), row, row)

        invoice_id = invoice.id
        status = invoice.status
        assert status is InvoiceStatus.DRAFT
        amount = invoice.amount
        self._invoice_ids.append(invoice_id)
        date_ = invoice.created_on
        self._invoices[invoice_id] = (
            invoice_id,
            invoice.client_id,
            invoice.client.name,
            invoice.code,
            date_,
            amount.raw,
            amount.vat,
            amount.net,
            status,
            False,
            date_,
        )

        self.endInsertRows()

    def update_invoice(self, invoice: schemas.Invoice) -> None:
        start_index = self.index_from_invoice_id(invoice.id)
        if start_index.isValid():
            date_ = (
                invoice.created_on
                if invoice.status is InvoiceStatus.DRAFT
                else invoice.issued_on
            )
            is_late = False
            if invoice.status in (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED):
                delta = Config.dfacto_settings.due_date_delta
                is_late = date_ + timedelta(days=delta) < datetime.now()
            self._invoices[invoice.id] = (
                invoice.id,
                invoice.client_id,
                invoice.client.name,
                invoice.code,
                date_,
                invoice.amount.raw,
                invoice.amount.vat,
                invoice.amount.net,
                invoice.status,
                is_late,
                invoice.changed_to_on(invoice.status),
            )
            end_index = start_index.sibling(start_index.row(), IS_LATE)
            self.dataChanged.emit(
                start_index,
                end_index,
                (
                    QtCore.Qt.ItemDataRole.DisplayRole,
                    QtCore.Qt.ItemDataRole.DecorationRole,
                ),
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
                        locale = Config.dfacto_settings.locale
                        return format_date(
                            datetime_.date(), format="short", locale=locale
                        )
                    if column == STATUS:
                        status = cast(InvoiceStatus, item[column])
                        return status.as_string().upper()
                    if column == IS_LATE:
                        return None
                    if column in (RAW_AMOUNT, VAT, NET_AMOUNT):
                        return format_currency(
                            item[column], "EUR", locale=Config.dfacto_settings.locale
                        )
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

                if role == QtCore.Qt.ItemDataRole.DecorationRole:
                    if column == IS_LATE and item[IS_LATE]:
                        return self._is_late_icon

                if role in (
                    QtCore.Qt.ItemDataRole.ToolTipRole,
                    QtCore.Qt.ItemDataRole.StatusTipRole,
                ):
                    if column == STATUS:
                        status = cast(InvoiceStatus, item[STATUS])
                        status_changed_on = cast(datetime, item[CHANGED_ON]).date()
                        locale = Config.dfacto_settings.locale
                        changed_date = format_date(
                            status_changed_on, format="short", locale=locale
                        )
                        return "%(status)s on %(date)s" % {
                            "status": status.name.title(),
                            "date": changed_date,
                        }

                if role == InvoiceTableModel.UserRoles.DateRole:
                    return cast(datetime, item[CREATED_ON]).date()

                if role == InvoiceTableModel.UserRoles.StatusRole:
                    return cast(InvoiceStatus, item[STATUS])

                if role == InvoiceTableModel.UserRoles.ClientRole:
                    return self._get_client_of_invoice(item[ID])

                if role == InvoiceTableModel.UserRoles.IsLateRole:
                    return cast(bool, item[IS_LATE])

        return None

    def _invoice_id_from_index(self, index: QtCore.QModelIndex) -> Optional[int]:
        if index.isValid():
            row = index.row()
            if 0 <= row < self.rowCount():
                return self._invoice_ids[row]
        return None

    def _get_client_id_of_invoice(self, invoice_id: int) -> int:
        try:
            invoice = self._invoices[invoice_id]
        except KeyError:
            return -1
        return invoice[CLIENT_ID]

    def _get_client_of_invoice(self, invoice_id: int) -> schemas.Client:
        response = api.client.get(self._get_client_id_of_invoice(invoice_id))

        if response.status is not CommandStatus.FAILED:
            client: schemas.Client = response.body
            return client

        msg = _("Cannot get client of invoice %s") % invoice_id
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} - {reason} {response.reason}")


class InvoiceViewer(QtUtil.QFramedWidget):
    basket_updated = QtCore.pyqtSignal(int)  # client id

    def __init__(
        self, invoice_model: InvoiceTableModel, translations, parent=None
    ) -> None:
        super().__init__(parent=parent)

        self.translations = translations

        resources = Config.dfacto_settings.resources

        self.active_pix = QtGui.QPixmap(
            f"{resources}/client-active.png"
        ).scaledToHeight(24, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.inactive_pix = QtGui.QPixmap(
            f"{resources}/client-inactive.png"
        ).scaledToHeight(24, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.all_pix = QtGui.QPixmap(f"{resources}/client-all.png").scaledToHeight(
            24, QtCore.Qt.TransformationMode.SmoothTransformation
        )

        self.header_lbl = QtWidgets.QLabel(_("INVOICES"))
        self.header_lbl.setMaximumHeight(32)
        self.client_pix = QtWidgets.QLabel()
        self.client_pix.setPixmap(self.active_pix)
        self.client_lbl = QtWidgets.QLabel()

        icon_size = QtCore.QSize(32, 32)
        small_icon_size = QtCore.QSize(24, 24)

        self.all_btn = QtWidgets.QPushButton()
        self.all_btn.setCheckable(True)
        self.all_btn.setFlat(True)
        self.all_btn.setIconSize(small_icon_size)
        self.all_btn.setIcon(QtGui.QIcon(f"{resources}/client-all.png"))
        tip = _("Show invoices of all clients")
        self.all_btn.setToolTip(tip)
        self.all_btn.setStatusTip(tip)
        self.period_cmb = QtWidgets.QComboBox()
        tip = _("Filter on emitted date")
        self.period_cmb.setToolTip(tip)
        self.period_cmb.setStatusTip(tip)
        self.status_btn = QtWidgets.QToolButton()
        self.status_btn.setText(_("Status filter "))
        tip = _("Filter on status")
        self.status_btn.setToolTip(tip)
        self.status_btn.setStatusTip(tip)
        self.status_btn.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.late_btn = QtWidgets.QPushButton()
        self.late_btn.setCheckable(True)
        self.late_btn.setFlat(True)
        self.late_btn.setIconSize(small_icon_size)
        self.late_btn.setIcon(QtGui.QIcon(f"{resources}/alarm.png"))
        tip = _("Show only invoice to be checked for payment")
        self.late_btn.setToolTip(tip)
        self.late_btn.setStatusTip(tip)
        self.reset_btn = QtWidgets.QPushButton()
        self.reset_btn.setFlat(True)
        self.reset_btn.setIconSize(small_icon_size)
        self.reset_btn.setIcon(QtGui.QIcon(f"{resources}/reload.png"))
        tip = _("Reset to default filters")
        self.reset_btn.setToolTip(tip)
        self.reset_btn.setStatusTip(tip)

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
        self.show_btn = QtWidgets.QPushButton()
        self.show_btn.setFlat(True)
        self.show_btn.setIconSize(icon_size)
        self.show_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-preview.png"))
        tip = _("Preview the selected invoice")
        self.show_btn.setToolTip(tip)
        self.show_btn.setStatusTip(tip)
        self.emit_btn = QtWidgets.QPushButton()
        self.emit_btn.setFlat(True)
        self.emit_btn.setIconSize(icon_size)
        self.emit_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-emit.png"))
        tip = _("Emit the selected invoice")
        self.emit_btn.setToolTip(tip)
        self.emit_btn.setStatusTip(tip)
        self.remind_btn = QtWidgets.QPushButton()
        self.remind_btn.setFlat(True)
        self.remind_btn.setIconSize(icon_size)
        self.remind_btn.setIcon(QtGui.QIcon(f"{resources}/invoice-remind.png"))
        tip = _("Remind the selected invoice")
        self.remind_btn.setToolTip(tip)
        self.remind_btn.setStatusTip(tip)
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
        self.undo_btn = QtWidgets.QPushButton()
        self.undo_btn.setFlat(True)
        self.undo_btn.setIconSize(icon_size)
        self.undo_btn.setIcon(QtGui.QIcon(f"{resources}/undo.png"))
        tip = _("Revert invoice to its previous status")
        self.undo_btn.setToolTip(tip)
        self.undo_btn.setStatusTip(tip)
        self.history_btn = QtWidgets.QPushButton()
        self.history_btn.setFlat(True)
        self.history_btn.setIconSize(icon_size)
        self.history_btn.setIcon(QtGui.QIcon(f"{resources}/history.png"))
        tip = _("Show invoice history")
        self.history_btn.setToolTip(tip)
        self.history_btn.setStatusTip(tip)

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

        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setContentsMargins(5, 0, 0, 0)
        filter_layout.setSpacing(5)
        filter_layout.addWidget(self.all_btn)
        filter_layout.addWidget(self.period_cmb)
        filter_layout.addWidget(self.status_btn)
        filter_layout.addWidget(self.late_btn)
        filter_layout.addWidget(self.reset_btn)

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.show_btn)
        tool_layout.addWidget(self.history_btn)
        tool_layout.addWidget(self.undo_btn)
        tool_layout.addWidget(self.emit_btn)
        tool_layout.addWidget(self.paid_btn)
        tool_layout.addWidget(self.remind_btn)
        tool_layout.addWidget(self.delete_btn)
        tool_layout.addWidget(self.cancel_btn)
        tool_layout.addSpacing(32)
        tool_layout.addWidget(self.basket_btn)

        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        h_layout.addLayout(filter_layout)
        h_layout.addStretch()
        h_layout.addLayout(tool_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header)
        main_layout.addLayout(h_layout)
        main_layout.addWidget(self._invoice_table)
        self.setLayout(main_layout)

        self.period_cmb.addItem(_("All dates"), userData=Period())
        for filter_ in PeriodFilter.ordered():
            self.period_cmb.addItem(filter_.as_string(), userData=filter_.as_period())

        self.status_menu = QtWidgets.QMenu(self)
        self.status_actions: dict[str, QtWidgets.QCheckBox] = dict()
        # Translators: "All" stands for "All statuses"
        action_ckb = QtWidgets.QCheckBox(_("All"), self.status_menu)
        ckb_action = QtWidgets.QWidgetAction(self.status_menu)
        ckb_action.setDefaultWidget(action_ckb)
        self.status_menu.addAction(ckb_action)
        action_ckb.setChecked(False)
        action_ckb.stateChanged.connect(self.on_all_selected)
        self.status_actions["all"] = action_ckb
        for status in InvoiceStatus:
            action_ckb = QtWidgets.QCheckBox(status.as_string(), self.status_menu)
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

        self.all_btn.toggled.connect(self.on_all_selection)
        self.period_cmb.activated.connect(self.on_period_selection)
        self.late_btn.toggled.connect(self.on_late_selection)
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
        self.history_btn.clicked.connect(self.show_history)
        self.undo_btn.clicked.connect(self.undo)

        self.invoice_html_view.finished.connect(self.on_html_view_finished)

        invoice_model.some_payment_needed.connect(self.check_if_paid)

        self._current_client: Optional[schemas.Client] = None
        self.all_btn.setChecked(False)
        self.late_btn.setChecked(False)

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

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Delete invoice")
        question = _("Do you really want to delete this invoice permanently?")
        reply = QtUtil.question(
            self,  # noqa
            f"{app_name} - {action}",
            f"""
            <p>{question}</p>
            <p><strong>{invoice[CODE]}</strong></p>
            """,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        report = invoice_table.source_model().delete_invoice(invoice[ID])

        if report.status is not CommandStatus.COMPLETED:
            msg = _("Cannot delete invoice %s of client %s") % (
                invoice[ID],
                invoice[CLIENT_NAME],
            )
            reason = _("Reason is:")
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg}</p>
                <p><strong>{reason} {report.reason}</strong></p>
                """,
            )

    @QtCore.pyqtSlot()
    def basket_from_invoice(self) -> None:
        invoice_table = self._invoice_table
        invoice = invoice_table.selected_invoice()

        if invoice[STATUS] is InvoiceStatus.DRAFT:
            self._move_in_basket(invoice)
        else:
            self._copy_in_basket(invoice)

    @QtCore.pyqtSlot()
    def show_history(self) -> None:
        invoice_table = self._invoice_table
        model = invoice_table.source_model()

        invoice_id = invoice_table.selected_invoice()[ID]
        invoice = model.get_invoice(invoice_id)

        a_dialog = StatusLogEditor(invoice)

        if a_dialog.exec():
            model.update_invoice_history(invoice_id=invoice_id, log=a_dialog.status_log)

    @QtCore.pyqtSlot()
    def undo(self) -> None:
        invoice_table = self._invoice_table
        invoice = invoice_table.selected_invoice()

        report, status = self._invoice_table.source_model().revert_to_previous_status(
            invoice[ID]
        )

        if report.status is CommandStatus.COMPLETED:
            self._enable_buttons(status=status)
        else:
            app_name = QtWidgets.QApplication.applicationName()
            action = _("Revert invoice status")
            msg = _("Cannot revert invoice %s to its previous status") % invoice[CODE]
            reason = _("Reason is:")
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg}</p>
                <p><strong>{reason} {report.reason}</strong></p>
                """,
            )

    @QtCore.pyqtSlot(object)
    def set_current_client(self, client: Optional[schemas.Client]) -> None:
        self._current_client = client
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())

        if client is None:
            logger.info(
                _(
                    "No client exists or all clients are hidden, disable invoices interactions"
                )
            )
            self.client_lbl.clear()
            self.client_pix.clear()
            self._enable_filters(False)
            self._enable_buttons(enable=False)
            proxy.set_client_filter(-1)
            return

        # A client is selected and it is visible
        logger.info(_("Show invoices of client: %s"), client.name)
        self._enable_filters(True)
        self.client_lbl.setText(f"{client.name}")
        self.client_pix.setPixmap(
            self.active_pix if client.is_active else self.inactive_pix
        )

        proxy.set_client_filter(client.id)

        with QtCore.QSignalBlocker(self.all_btn):
            self.all_btn.setChecked(False)

        row_count = proxy.rowCount()
        self._invoice_table.select_and_show_row(row_count - 1)
        if row_count < 1:
            self._enable_buttons(enable=False)

    @QtCore.pyqtSlot()
    def set_default_filters(self) -> None:
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.reset_to_defaults()

        with QtCore.QSignalBlocker(self.all_btn):
            self.all_btn.setChecked(False)

        client = self._current_client
        if client is not None:
            self.client_lbl.setText(f"{client.name}")
            self.client_pix.setPixmap(
                self.active_pix if client.is_active else self.inactive_pix
            )

        with QtCore.QSignalBlocker(self.period_cmb):
            self.period_cmb.setCurrentText(PeriodFilter.CURRENT_QUARTER.as_string())

        for status, ckb in self.status_actions.items():
            with QtCore.QSignalBlocker(ckb):
                ckb.setChecked(status != "all" and status != "cancelled")

        with QtCore.QSignalBlocker(self.late_btn):
            self.late_btn.setChecked(False)

        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    @QtCore.pyqtSlot(bool)
    def on_all_selection(self, checked: bool):
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.set_are_all_invoices_visible(checked)

        if checked:
            # Translators: "All" stands for "All clients"
            self.client_lbl.setText(_("All"))
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
                    all(
                        [
                            c.isChecked()
                            for s, c in self.status_actions.items()
                            if s != "all"
                        ]
                    )
                )
        else:
            with QtCore.QSignalBlocker(ckb):
                ckb.setChecked(False)
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())
        proxy.toggle_status(status)
        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    @QtCore.pyqtSlot(bool)
    def on_late_selection(self, state: bool) -> None:
        proxy = cast(InvoiceFilterProxyModel, self._invoice_table.model())

        proxy.set_late_filter(state)

        if state:
            with QtCore.QSignalBlocker(self.all_btn):
                self.all_btn.setChecked(True)

            # Translators: "All" stands for "All clients"
            self.client_lbl.setText(_("All"))
            self.client_pix.setPixmap(self.all_pix)

            with QtCore.QSignalBlocker(self.period_cmb):
                self.period_cmb.setCurrentText(_("All dates"))

            for status, ckb in self.status_actions.items():
                with QtCore.QSignalBlocker(ckb):
                    ckb.setChecked(status == "emitted" or status == "reminded")

        self._invoice_table.select_and_show_row(proxy.rowCount() - 1)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def show_buttons(self, index: QtCore.QModelIndex) -> None:
        if index.isValid():
            proxy_model = cast(InvoiceFilterProxyModel, self._invoice_table.model())
            client = proxy_model.client_from_index(index)
            if not client.is_active:
                self._enable_buttons(enable=False)
            else:
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

    @QtCore.pyqtSlot()
    def check_if_paid(self):
        app_name = QtWidgets.QApplication.applicationName()
        action = _("Payment reminder")
        question = _("Some invoices should be paid: do you want to ckeck them?")
        reply = QtUtil.question(
            self,  # noqa
            f"{app_name} - {action}",
            f"""
            <p>{question}</p>
            """,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        self.late_btn.setChecked(True)

    def _enable_filters(self, enable: bool) -> None:
        self.all_btn.setEnabled(enable)
        self.period_cmb.setEnabled(enable)
        self.status_btn.setEnabled(enable)
        self.reset_btn.setEnabled(enable)

    def _enable_buttons(
        self, *, status: InvoiceStatus = None, enable: bool = True
    ) -> None:
        if enable:
            assert status is not None
            is_draft = status is InvoiceStatus.DRAFT
            is_emitted_or_reminded = (
                status is InvoiceStatus.EMITTED or status is InvoiceStatus.REMINDED
            )
            is_undoable = not is_draft
            self.show_btn.setEnabled(True)
            self.history_btn.setEnabled(True)
            self.undo_btn.setEnabled(is_undoable)
            self.emit_btn.setEnabled(is_draft)
            self.remind_btn.setEnabled(is_emitted_or_reminded)
            self.paid_btn.setEnabled(is_emitted_or_reminded)
            self.delete_btn.setEnabled(is_draft)
            self.cancel_btn.setEnabled(is_emitted_or_reminded)
            self.basket_btn.setEnabled(True)
        else:
            assert status is None
            self.show_btn.setEnabled(False)
            self.history_btn.setEnabled(False)
            self.undo_btn.setEnabled(False)
            self.emit_btn.setEnabled(False)
            self.remind_btn.setEnabled(False)
            self.paid_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
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
            invoice_id, mode=mode, translations=self.translations
        )

        if html is not None:
            status = cast(InvoiceStatus, invoice[STATUS])
            self.invoice_html_view.set_invoice(
                invoice_id, status, html, mode=viewer_mode
            )
            self.invoice_html_view.open()
            return

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Invoice view")
        msg = _("Cannot show invoice %s of client %s") % (
            invoice[CODE],
            invoice[CLIENT_NAME],
        )
        reason = _("Reason is:")
        QtUtil.warning(
            None,  # type: ignore
            f"{app_name} - {action}",
            f"""
            <p>{msg}</p>
            <p><strong>{reason} {report.reason}</strong></p>
            """,
        )

    def _mark_invoice_as(self, status: InvoiceStatus, confirm: bool = False) -> None:
        invoice_table = self._invoice_table
        invoice = invoice_table.selected_invoice()
        status_txt = status.as_string().lower()

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Mark invoice as %s" % status_txt)
        if confirm:
            question = (
                _("Do you really want to mark permanently this invoice as %s?")
                % status_txt
            )
            reply = QtUtil.question(
                self,  # noqa
                f"{app_name} - {action}",
                f"""
                <p>{question}</p>
                <p><strong>{invoice[CODE]}</strong></p>
                """,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return

        report = invoice_table.source_model().mark_invoice_as(invoice[ID], status)

        if report.status is CommandStatus.COMPLETED:
            invoice_table.select_invoice(invoice[ID])
            return

        msg = _("Cannot mark invoice %(id)s as %(status)") % {
            "id": invoice[ID],
            "status": status_txt,
        }
        reason = _("Reason is:")
        QtUtil.warning(
            None,  # type: ignore
            f"{app_name} - {action}",
            f"""
            <p>{msg}</p>
            <p><strong>{reason} {report.reason}</strong></p>
            """,
        )

    def _move_in_basket(self, invoice: InvoiceItem):
        report = self._invoice_table.source_model().move_in_basket(
            invoice[CLIENT_ID], invoice[ID]
        )

        if report.status is CommandStatus.COMPLETED:
            self.basket_updated.emit(invoice[CLIENT_ID])
        else:
            app_name = QtWidgets.QApplication.applicationName()
            action = _("Move invoice in basket")
            msg = _("Cannot move invoice %s in basket of client %s") % (
                invoice[CODE],
                invoice[CLIENT_NAME],
            )
            reason = _("Reason is:")
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg}</p>
                <p><strong>{reason} {report.reason}</strong></p>
                """,
            )

    def _copy_in_basket(self, invoice: InvoiceItem):
        report = self._invoice_table.source_model().copy_in_basket(
            invoice[CLIENT_ID], invoice[ID]
        )

        if report.status is CommandStatus.COMPLETED:
            self.basket_updated.emit(invoice[CLIENT_ID])
        else:
            app_name = QtWidgets.QApplication.applicationName()
            action = _("Copy invoice in basket")
            msg = _("Cannot copy invoice %s in basket of client %s") % (
                invoice[CODE],
                invoice[CLIENT_NAME],
            )
            reason = _("Reason is:")
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg}</p>
                <p><strong>{reason} {report.reason}</strong></p>
                """,
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
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
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
        # To raise currentChanged signal on row selection
        self.setCurrentIndex(QtCore.QModelIndex())
        self.selectRow(row)
        self.scrollTo(
            self.model().index(row, 1),
            QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible,
        )
        proxy = cast(InvoiceFilterProxyModel, self.model())
        for column in range(proxy.columnCount()):
            self.horizontalHeader().setSectionResizeMode(
                column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
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
            self,
            "Test",
            slot=lambda: print("Test"),  # noqa
            icon=QtGui.QIcon(f"{resources}/ok.png"),
            # shortcut="CTRL+ALT+P",
            tip="Test a context menu action",
        )

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
    _status_filter = _("Not cancelled")
    _statuses_filter = ["draft", "emitted", "reminded", "paid"]
    _are_all_invoices_visible = False
    _late_filter = False

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

    @classmethod
    def late_filter(cls) -> bool:
        return cls._late_filter

    def set_late_filter(self, value: bool) -> None:
        if value:
            InvoiceFilterProxyModel._are_all_invoices_visible = True
            InvoiceFilterProxyModel._period_filter = Period()
            InvoiceFilterProxyModel._statuses_filter = ["emitted", "reminded"]
            InvoiceFilterProxyModel._late_filter = True
        else:
            InvoiceFilterProxyModel._late_filter = False
        self.invalidateFilter()

    def reset_to_defaults(self) -> None:
        InvoiceFilterProxyModel._are_all_invoices_visible = False
        InvoiceFilterProxyModel._period_filter = (
            PeriodFilter.CURRENT_QUARTER.as_period()
        )
        InvoiceFilterProxyModel._status_filter = _("Not cancelled")
        InvoiceFilterProxyModel._statuses_filter = [
            "draft",
            "emitted",
            "reminded",
            "paid",
        ]
        InvoiceFilterProxyModel._late_filter = False
        self.invalidateFilter()

    def lessThan(self, left: QtCore.QModelIndex, right: QtCore.QModelIndex) -> bool:
        source_model = self.sourceModel()

        if left.column() == CREATED_ON:
            left_date = source_model.data(
                left, role=InvoiceTableModel.UserRoles.DateRole
            )
            right_date = source_model.data(
                right, role=InvoiceTableModel.UserRoles.DateRole
            )
            return left_date < right_date
        return super().lessThan(left, right)

    def filterAcceptsColumn(
        self, source_column: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        if source_column in (ID, CLIENT_ID, CHANGED_ON):
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

    def filterAcceptsRow(
        self, source_row: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        source_model = self.sourceModel()

        if self._are_all_invoices_visible:
            ok_client = True
        else:
            index = source_model.index(source_row, CLIENT_ID, source_parent)
            client_id = self.sourceModel().data(
                index, QtCore.Qt.ItemDataRole.DisplayRole
            )
            ok_client = int(client_id) == self.client_filter()

        if self._period_filter == Period():
            ok_period = True
        else:
            index = source_model.index(source_row, CREATED_ON, source_parent)
            date_ = source_model.data(index, InvoiceTableModel.UserRoles.DateRole)
            period = self.period_filter()
            ok_period = period.start <= date_ <= period.end

        index = source_model.index(source_row, STATUS, source_parent)
        status = source_model.data(index, InvoiceTableModel.UserRoles.StatusRole)
        ok_status = status.name.lower() in self.statuses_filter()

        if self._late_filter:
            index = source_model.index(source_row, IS_LATE, source_parent)
            ok_late = source_model.data(index, InvoiceTableModel.UserRoles.IsLateRole)
        else:
            ok_late = True

        return ok_client and ok_period and ok_status and ok_late

    def invoice_from_index(self, index: QtCore.QModelIndex) -> InvoiceItem:
        source_model = cast(InvoiceTableModel, self.sourceModel())
        source_index = self.mapToSource(index)
        return source_model.invoice_from_index(source_index)

    def invoice_status_from_index(self, index: QtCore.QModelIndex) -> InvoiceStatus:
        source_model = cast(InvoiceTableModel, self.sourceModel())
        source_index = self.mapToSource(index)
        return source_model.data(source_index, InvoiceTableModel.UserRoles.StatusRole)

    def client_from_index(self, index: QtCore.QModelIndex) -> schemas.Client:
        source_model = cast(InvoiceTableModel, self.sourceModel())
        source_index = self.mapToSource(index)
        return source_model.data(source_index, InvoiceTableModel.UserRoles.ClientRole)
