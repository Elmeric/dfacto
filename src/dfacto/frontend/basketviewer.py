# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from decimal import Decimal
from typing import Any, Optional, cast

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.util import qtutil as QtUtil

from . import get_current_company

logger = logging.getLogger(__name__)

BasketItem = tuple[int, str, Decimal, int, Decimal, Decimal, Decimal, Decimal]

ID, SERVICE, UNIT_PRICE, QUANTITY, RAW_AMOUNT, VAT_RATE, VAT, NET_AMOUNT = range(8)
VAT_COLUMNS = (SERVICE, UNIT_PRICE, QUANTITY, RAW_AMOUNT, VAT_RATE, VAT, NET_AMOUNT)
NOVAT_COLUMNS = (SERVICE, UNIT_PRICE, QUANTITY, RAW_AMOUNT)


class BasketTableModel(QtCore.QAbstractTableModel):
    basket_updated = QtCore.pyqtSignal(schemas.Basket)

    def __init__(self) -> None:
        super().__init__()
        self._headers = [
            _("Id"),
            _("Service"),
            _("Unit price"),
            _("Quantity"),
            _("Amount"),
            _("VAT rate"),
            _("VAT"),
            _("Net amount"),
        ]
        self._basket: Optional[schemas.Basket] = None
        self._items: dict[int, BasketItem] = {}
        self._item_ids: list[int] = []
        self._services_map: dict[int, int] = {}

    def set_basket(self, client_id: int) -> bool:
        basket = self.get_basket_of_client(client_id)
        self._basket = basket
        self.basket_updated.emit(basket)
        if basket is not None:
            self.clear_items()
            self.add_items(basket.items)
            return True
        return False

    def add_service_to_basket(self, service_id: int, quantity: int) -> bool:
        client_id = self._basket.client_id
        response = api.client.add_to_basket(
            client_id, service_id=service_id, quantity=quantity
        )

        if response.status is CommandStatus.COMPLETED:
            self.add_item(response.body)
            return self._update_basket(client_id)

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Add to basket")
        msg = _("Cannot add service to basket of client")
        reason = _("Reason is:")
        if response.status is CommandStatus.REJECTED:
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg} {self._basket.client.name}</p>
                <p><strong>{reason} {response.reason}</strong></p>
                """,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(f"{msg} {client_id} - {reason} {response.reason}")

    def remove_item_from_basket(self, item_id: int) -> bool:
        client_id = self._basket.client_id
        response = api.client.remove_item(client_id, item_id=item_id)

        if response.status is CommandStatus.COMPLETED:
            self.remove_item(item_id)
            return self._update_basket(client_id)

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Remove item from basket")
        msg = _("Cannot remove item from basket of client")
        reason = _("Reason is:")
        if response.status is CommandStatus.REJECTED:
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg} {self._basket.client.name}</p>
                <p><strong>{reason} {response.reason}</strong></p>
                """,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(f"{msg} {client_id} - {reason} {response.reason}")

    def update_item_quantity_in_basket(self, item_id: int, quantity: int) -> bool:
        client_id = self._basket.client_id
        response = api.client.update_item_quantity(
            client_id, item_id=item_id, quantity=quantity
        )
        if response.status is CommandStatus.COMPLETED:
            self.update_item(response.body)
            return self._update_basket(client_id)

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Update item quantity in basket")
        msg = _("Cannot update item quantity in basket of client")
        reason = _("Reason is:")
        if response.status is CommandStatus.REJECTED:
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg} {self._basket.client.name}</p>
                <p><strong>{reason} {response.reason}</strong></p>
                """,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(f"{msg} {client_id} - {reason} {response.reason}")

    def update_service_in_basket(self, service_id: int) -> bool:
        client_id = self._basket.client_id
        response = api.client.get_item_from_service(client_id, service_id=service_id)

        if response.status is CommandStatus.COMPLETED:
            self.update_item(response.body)
            return self._update_basket(client_id)

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Update service in basket")
        msg = _("Cannot update service in basket of client")
        reason = _("Reason is:")
        if response.status is CommandStatus.REJECTED:
            QtUtil.warning(
                None,  # type: ignore
                f"{app_name} - {action}",
                f"""
                <p>{msg} {self._basket.client.name}</p>
                <p><strong>{reason} {response.reason}</strong></p>
                """,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(f"{msg} {client_id} - {reason} {response.reason}")

    def empty_basket(self) -> bool:
        client_id = self._basket.client_id
        response = api.client.clear_basket(client_id)

        if response.status is CommandStatus.COMPLETED:
            self.clear_items()
            return self._update_basket(self._basket.client_id)

        msg = _("Cannot empty basket of client")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} {client_id} - {reason} {response.reason}")

    def item_from_index(self, index: QtCore.QModelIndex) -> Optional[BasketItem]:
        item_id = self._item_id_from_index(index)
        if item_id is not None:
            return self._items[item_id]
        return None

    def index_from_item_id(self, item_id: int) -> QtCore.QModelIndex:
        try:
            row = self._item_ids.index(item_id)
        except ValueError:
            return QtCore.QModelIndex()
        else:
            return self.index(row, SERVICE)

    def index_from_service_id(self, service_id: int) -> QtCore.QModelIndex:
        try:
            item_id = self._services_map[service_id]
        except KeyError:
            return QtCore.QModelIndex()

        try:
            row = self._item_ids.index(item_id)
        except ValueError:
            return QtCore.QModelIndex()
        else:
            return self.index(row, QUANTITY)

    def item_from_service_id(self, service_id: int) -> Optional[BasketItem]:
        try:
            item_id = self._services_map[service_id]
        except KeyError:
            return
        return self._items[item_id]

    def quantity_from_index(self, index: QtCore.QModelIndex) -> int:
        item_id = self._item_id_from_index(index)
        if item_id is None:
            return 0
        return self._items[item_id][QUANTITY]

    def quantity_in_basket(self, service_id: int) -> int:
        try:
            item_id = self._services_map[service_id]
        except KeyError:
            return 0
        return self._items[item_id][QUANTITY]

    def is_service_in_basket(self, service_id: int) -> bool:
        try:
            _item_id = self._services_map[service_id]
        except KeyError:
            return False
        return True

    def clear_items(self) -> None:
        self.beginResetModel()
        self._items = {}
        self._item_ids = []
        self._services_map = {}
        self.endResetModel()

    def add_items(self, items: list[schemas.Item]) -> None:
        row = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), row, row + len(items) - 1)

        for item in items:
            self._item_ids.append(item.id)
            self._items[item.id] = (
                item.service_id,
                item.current_service.name,
                item.current_service.unit_price,
                item.quantity,
                item.current_amount.raw,
                item.current_service.vat_rate.rate,
                item.current_amount.vat,
                item.current_amount.net,
            )
            self._services_map[item.service.id] = item.id

        self.endInsertRows()

    def add_item(self, item: schemas.Item) -> None:
        self.add_items([item])

    def update_item(self, item: schemas.Item) -> None:
        start_index = self.index_from_item_id(item.id)
        if start_index.isValid():
            self._items[item.id] = (
                item.service_id,
                item.current_service.name,
                item.current_service.unit_price,
                item.quantity,
                item.current_amount.raw,
                item.current_service.vat_rate.rate,
                item.current_amount.vat,
                item.current_amount.net,
            )
            end_index = start_index.sibling(start_index.row(), NET_AMOUNT)
            self.dataChanged.emit(
                start_index,
                end_index,
                (QtCore.Qt.ItemDataRole.DisplayRole,),
            )

    def remove_item(self, item_id: int) -> None:
        index = self.index_from_item_id(item_id)
        if index.isValid():
            row = index.row()
            service_id = self._items[item_id][ID]
            self.beginRemoveRows(QtCore.QModelIndex(), row, row)
            del self._items[item_id]
            del self._item_ids[row]
            del self._services_map[service_id]
            self.endRemoveRows()

    def rowCount(self, index: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._item_ids)

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

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if index.isValid():
            column = index.column()

            if column == QUANTITY and self._basket.is_active:
                flags = QtCore.Qt.ItemFlag.ItemIsEditable | super().flags(index)
                return flags

            return super().flags(index)

        return QtCore.Qt.ItemFlag.NoItemFlags

    def data(
        self, index: QtCore.QModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if index.isValid():
            row = index.row()
            column = index.column()

            if 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
                item = self._items[self._item_ids[row]]

                if role in (
                    QtCore.Qt.ItemDataRole.DisplayRole,
                    QtCore.Qt.ItemDataRole.EditRole,
                ):
                    if 0 <= column < len(item):
                        return str(item[column])

                if role in (
                    QtCore.Qt.ItemDataRole.StatusTipRole,
                    QtCore.Qt.ItemDataRole.ToolTipRole,
                ):
                    return _("Select 'Quantity' field to edit")

                if role == QtCore.Qt.ItemDataRole.FontRole:
                    if column == SERVICE:
                        bold_font = QtGui.QFont()
                        bold_font.setBold(True)
                        return bold_font

        return None

    def setData(
        self,
        index: QtCore.QModelIndex,
        value: Any,
        role: int = QtCore.Qt.ItemDataRole.EditRole,
    ) -> bool:
        if index.isValid() and role == QtCore.Qt.ItemDataRole.EditRole:
            row = index.row()
            column = index.column()

            if 0 <= row < self.rowCount() and 0 <= column < self.columnCount():
                item_id = self._item_ids[row]

                if column == QUANTITY:
                    if value == 0:
                        return self.remove_item_from_basket(item_id)
                    else:
                        return self.update_item_quantity_in_basket(
                            item_id=item_id, quantity=value
                        )

                return super().setData(index, value, role)

        return False

    def _item_id_from_index(self, index: QtCore.QModelIndex) -> Optional[int]:
        if index.isValid():
            row = index.row()
            if 0 <= row < self.rowCount():
                return self._item_ids[row]
        return None

    @staticmethod
    def get_basket_of_client(client_id: int) -> schemas.Basket:
        response = api.client.get_basket(client_id)

        if response.status is CommandStatus.COMPLETED:
            basket: schemas.Basket = response.body
            return basket

        msg = _("Cannot retrieve the basket of client")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(f"{msg} {client_id} - {reason} {response.reason}")

    def _update_basket(self, client_id: int) -> bool:
        basket = self.get_basket_of_client(client_id)
        self._basket = basket
        self.basket_updated.emit(basket)
        return True


class BasketViewer(QtUtil.QFramedWidget):
    selection_changed = QtCore.pyqtSignal(str)  # service name of the selected item
    invoice_created = QtCore.pyqtSignal(schemas.Invoice)

    def __init__(self, basket_model: BasketTableModel, parent=None) -> None:
        super().__init__(parent=parent)

        resources = Config.dfacto_settings.resources

        self.active_pix = QtGui.QPixmap(
            f"{resources}/client-active.png"
        ).scaledToHeight(24, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.inactive_pix = QtGui.QPixmap(
            f"{resources}/client-inactive.png"
        ).scaledToHeight(24, QtCore.Qt.TransformationMode.SmoothTransformation)
        basket_pix = QtGui.QPixmap(f"{resources}/basket.png")

        self.header_lbl = QtWidgets.QLabel(_("BASKET"))
        self.header_lbl.setMaximumHeight(32)
        self.client_pix = QtWidgets.QLabel()
        self.client_pix.setPixmap(self.active_pix)
        self.client_lbl = QtWidgets.QLabel()

        icon_size = QtCore.QSize(48, 48)
        self.clear_btn = QtWidgets.QPushButton(
            QtGui.QIcon(f"{resources}/clear-basket.png"), ""
        )
        self.clear_btn.setIconSize(icon_size)
        tip = _("Remove all items from basket")
        self.clear_btn.setToolTip(tip)
        self.clear_btn.setStatusTip(tip)
        self.clear_btn.setFlat(True)

        self.basket_pix = QtWidgets.QLabel()
        self.basket_pix.setPixmap(basket_pix)
        self.summary_lbl = QtWidgets.QLabel()
        self.summary_lbl.setMargin(5)
        # self.summary_lbl.setFrameStyle(
        #     QtWidgets.QFrame.Shape.StyledPanel | QtWidgets.QFrame.Shadow.Raised
        # )
        self.summary_lbl.setWordWrap(True)
        self.summary_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.invoicing_btn = QtWidgets.QPushButton(
            QtGui.QIcon(f"{resources}/invoice-add.png"), ""
        )
        self.invoicing_btn.setIconSize(icon_size)
        tip = _("Create invoice from basket")
        self.invoicing_btn.setToolTip(tip)
        self.invoicing_btn.setStatusTip(tip)
        self.invoicing_btn.setFlat(True)

        self._basket_table = BasketTable(basket_model)

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
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.clear_btn)
        tool_layout.addStretch()
        tool_layout.addWidget(self.basket_pix)
        tool_layout.addWidget(self.summary_lbl)
        tool_layout.addWidget(self.invoicing_btn)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header)
        main_layout.addLayout(tool_layout)
        main_layout.addWidget(self._basket_table)
        self.setLayout(main_layout)

        self.clear_btn.clicked.connect(self.clear_basket)
        self.invoicing_btn.clicked.connect(self.create_invoice)
        self._basket_table.selection_changed.connect(self.selection_changed)
        basket_model.basket_updated.connect(self.update_summary)

        self._current_client: Optional[schemas.Client] = None

    @QtCore.pyqtSlot(object)
    def set_current_client(self, client: Optional[schemas.Client]) -> None:
        proxy = cast(BasketFilterProxyModel, self._basket_table.model())
        proxy.set_is_vat_visible(not get_current_company().no_vat)

        self._current_client = client

        if client is None:
            logger.info(_("No client exists, disable basket interactions"))
            self.client_lbl.clear()
            self.client_pix.clear()
            self._basket_table.model().sourceModel().clear_items()
            self._enable_buttons(False)
            return

        # A client is selected
        logger.info(_("Loading basket of client: %s"), client.name)
        self.client_lbl.setText(f"{client.name}")
        self.client_pix.setPixmap(
            self.active_pix if client.is_active else self.inactive_pix
        )

        success = self._basket_table.load_basket(client.id)
        if not success or self._basket_table.model().rowCount() < 1:
            self._enable_buttons(False)

    @QtCore.pyqtSlot(schemas.Basket)
    def update_summary(self, basket: schemas.Basket) -> None:
        nbsp = "\u00A0"
        if basket is None or len(basket.items) == 0:
            item_count = _("Basket is empty").replace(" ", nbsp)
            total = 0
            total_str = _("Nothing to invoice").replace(" ", nbsp)
        else:
            count = len(basket.items)
            if count == 1:
                lbl1 = _(" item in basket").replace(" ", nbsp)
                item_count = f"<strong>1</strong>{lbl1}"
            else:
                lbl1 = _(" items in basket").replace(" ", nbsp)
                item_count = f"<strong>{count}</strong>{lbl1}"
            company = get_current_company()
            total = basket.amount.raw if company.no_vat else basket.amount.net
            lbl2 = _("Total to invoice: ").replace(" ", nbsp)
            total_str = f"{lbl2}<strong>{total}</strong>"

        self.summary_lbl.setText(f"{item_count}\n{total_str}")
        self._enable_buttons(total > 0)

    @QtCore.pyqtSlot()
    def clear_basket(self) -> None:
        app_name = QtWidgets.QApplication.applicationName()
        action = _("Clear basket")
        question = _("Do you really want to empty the basket of this client?")
        reply = QtUtil.question(
            self,  # noqa
            f"{app_name} - {action}",
            f"""
            <p>{question}</p>
            <p><strong>{self._current_client.name}</strong></p>
            """,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        success = self._basket_table.clear_basket()
        self._enable_buttons(not success)

    @QtCore.pyqtSlot()
    def create_invoice(self) -> None:
        response = api.client.invoice_from_basket(
            self._current_client.id, clear_basket=True
        )

        if response.status is CommandStatus.COMPLETED:
            self.invoice_created.emit(response.body)
            success = self._basket_table.clear_basket()
            self._enable_buttons(not success)
            return

        msg = _("Cannot create invoice for client")
        reason = _("Reason is:")
        QtUtil.raise_fatal_error(
            f"{msg} {self._current_client.name} - {reason} {response.reason}"
        )

    @QtCore.pyqtSlot(int)
    def on_basket_update(self, client_id: int) -> None:
        current_client = self._current_client
        if current_client is None:
            return

        client = current_client
        if current_client.id != client_id:
            basket = self._basket_table.source_model().get_basket_of_client(client_id)
            client = basket.client
            app_name = QtWidgets.QApplication.applicationName()
            action = _("Basket update")
            question = _(
                "Basket content of the following client has changed. Do you want to see it?"
            )
            reply = QtUtil.question(
                self,  # noqa
                f"{app_name} - {action}",
                f"""
                <p>{question}</p>
                <p><strong>{client.name}</strong></p>
                """,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return

        self.set_current_client(client)

    def _enable_buttons(self, enable: bool) -> None:
        self.clear_btn.setEnabled(enable)
        self.basket_pix.setEnabled(enable)
        self.invoicing_btn.setEnabled(enable)


class BasketTable(QtWidgets.QTableView):
    selection_changed = QtCore.pyqtSignal(str)  # service name of the selected item

    def __init__(self, basket_model: BasketTableModel, parent=None) -> None:
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
        self.setItemDelegate(BasketTableDelegate(self))
        self.setSortingEnabled(True)

        proxy_model = BasketFilterProxyModel()
        # proxy_model.setFilterKeyColumn(SERVICE)
        proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        # basket_model.cmdReported.connect(self.showCommandReport)
        proxy_model.setSourceModel(basket_model)
        self.setModel(proxy_model)

        # Prevent deselection: one row is always selected and a current index exists
        old_selection_model = self.selectionModel()
        new_selection_model = QtUtil.UndeselectableSelectionModel(
            self.model(), old_selection_model.parent()
        )
        self.setSelectionModel(new_selection_model)
        old_selection_model.deleteLater()

        self.clicked.connect(self.edit_quantity)
        self.selectionModel().currentChanged.connect(self.edit_quantity)
        basket_model.rowsInserted.connect(self.on_rows_inserted)
        basket_model.rowsRemoved.connect(self.on_rows_removed)

        if proxy_model.rowCount() > 0:
            self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
            for column in range(proxy_model.columnCount()):
                self.horizontalHeader().setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                )

    def source_model(self) -> BasketTableModel:
        return cast(BasketTableModel, self.model().sourceModel())

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def edit_quantity(self, proxy_index: QtCore.QModelIndex) -> None:
        if proxy_index.isValid():
            proxy_model = self.model()
            source_model = proxy_model.sourceModel()
            source_index = proxy_model.mapToSource(proxy_index)
            quantity_src_index = source_model.index(source_index.row(), QUANTITY)
            quantity_pxy_index = proxy_model.mapFromSource(quantity_src_index)
            # quantity_pxy_index = proxy_index.sibling(proxy_index.row(), QUANTITY - 1)
            service_name = source_model.item_from_index(source_index)[SERVICE]

            with QtCore.QSignalBlocker(self.selectionModel()):
                self.setCurrentIndex(quantity_pxy_index)
            self.edit(quantity_pxy_index)
            self.selection_changed.emit(service_name)
        else:
            self.selection_changed.emit("")

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def on_rows_inserted(
        self, _parent: QtCore.QModelIndex, first: int, last: int
    ) -> None:
        if last < 0:
            # No rows were inserted
            self.selection_changed.emit("")
            return
        proxy_model = self.model()
        source_model = proxy_model.sourceModel()
        source_index = source_model.index(first, SERVICE)
        proxy_index = proxy_model.mapFromSource(source_index)
        self.selectRow(proxy_index.row())

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def on_rows_removed(
        self, _parent: QtCore.QModelIndex, first: int, last: int
    ) -> None:
        if last < 0:
            # No rows were removed
            return
        self.select_first_item()

    def load_basket(self, client_id: int) -> bool:
        proxy = self.model()
        model = proxy.sourceModel()

        # Register the client and load its basket in the model.
        success = model.set_basket(client_id)

        if success:
            # Sort the basket table on first proxy column (Service name) and resize columns
            # to fit their content
            self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
            for column in range(proxy.columnCount()):
                self.horizontalHeader().setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                )

        return success

    def clear_basket(self) -> bool:
        proxy = self.model()
        model = proxy.sourceModel()
        success = model.empty_basket()
        if success:
            self.selection_changed.emit("")
        return success

    def select_first_item(self) -> None:
        self.selectRow(0)

    def select_item(self, item_id: int) -> None:
        proxy_model = self.model()
        source_model = proxy_model.sourceModel()
        source_index: QtCore.QModelIndex = source_model.index_from_item_id(item_id)
        proxy_index = proxy_model.mapFromSource(source_index)
        if proxy_index.isValid():
            self.selectRow(proxy_index.row())


class BasketTableDelegate(QtWidgets.QStyledItemDelegate):
    # class BasketTableDelegate(QtUtil.NoFocusDelegate):
    previous_quantity: Optional[int]

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

    def createEditor(
        self,
        parent: QtWidgets.QWidget,
        options: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> QtWidgets.QWidget:
        proxy_model = index.model()
        source_index = proxy_model.mapToSource(index)
        column = source_index.column()

        if column == QUANTITY:
            editor = QtWidgets.QSpinBox(parent)
            editor.setFrame(False)
            editor.setMaximum(100)
            editor.setAccelerated(True)
            price_tip = _("Service quantity, from 1 to 100")
            editor.setToolTip(price_tip)
            editor.setStatusTip(price_tip)
            self.previous_quantity = None
            return editor

        return super().createEditor(parent, options, index)

    def setEditorData(
        self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex
    ) -> None:
        proxy = index.model()
        source_index = proxy.mapToSource(index)
        column = source_index.column()

        if column == QUANTITY:
            editor: QtWidgets.QSpinBox
            value = str(index.model().data(index, QtCore.Qt.ItemDataRole.EditRole))
            if value:
                self.previous_quantity = int(value)
                editor.setValue(int(value))
                return

        super().setEditorData(editor, index)

    def setModelData(
        self,
        editor: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ) -> None:
        source_index = model.mapToSource(index)
        column = source_index.column()

        if column == QUANTITY:
            editor: QtWidgets.QSpinBox
            value = editor.value()
            if value != self.previous_quantity:
                model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)
            return

        super().setModelData(editor, model, index)

    def updateEditorGeometry(
        self,
        editor: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        proxy = index.model()
        source_index = proxy.mapToSource(index)
        column = source_index.column()

        if column == QUANTITY:
            rect = option.rect
            rect.setWidth(rect.width())
            editor.setGeometry(option.rect)
            return

        super().updateEditorGeometry(editor, option, index)


class BasketFilterProxyModel(QtCore.QSortFilterProxyModel):
    _is_vat_visible = True

    def __init__(self):
        super().__init__()
        company = get_current_company()
        self.set_is_vat_visible(not company.no_vat)

    @classmethod
    def is_vat_visible(cls) -> bool:
        return cls._is_vat_visible

    def set_is_vat_visible(self, value: bool) -> None:
        BasketFilterProxyModel._is_vat_visible = value
        self.invalidateFilter()

    def filterAcceptsColumn(
        self, source_column: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        if source_column == ID:
            return False
        if self._is_vat_visible:
            if source_column in VAT_COLUMNS:
                return True
            return False
        else:
            if source_column in NOVAT_COLUMNS:
                return True
            return False
