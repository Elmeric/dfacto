# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from typing import Any, Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.util import qtutil as QtUtil

logger = logging.getLogger(__name__)

BasketItem = list[int, str, float, int, float, float, float, float]

ID, SERVICE, UNIT_PRICE, QUANTITY, RAW_AMOUNT, VAT_RATE, VAT, NET_AMOUNT = range(8)
VAT_COLUMNS = (SERVICE, UNIT_PRICE, QUANTITY, RAW_AMOUNT, VAT_RATE, VAT, NET_AMOUNT)
NOVAT_COLUMNS = (SERVICE, UNIT_PRICE, QUANTITY, NET_AMOUNT)


class BasketTableModel(QtCore.QAbstractTableModel):
    basket_updated = QtCore.pyqtSignal(schemas.Basket)

    def __init__(self) -> None:
        super().__init__()
        self._headers = [
            "Id",
            "Service",
            "Unit price",
            "Quantity",
            "Raw amount",
            "VAT rate",
            "VAT",
            "Net amount",
        ]
        self._basket: Optional[schemas.Basket] = None
        self._items: dict[int, BasketItem] = {}
        self._item_ids: list[int] = []
        self._services_map: dict[int, int] = {}

    def set_basket(self, client_id: int) -> bool:
        basket = self._get_basket_of_client(client_id)
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

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"Dfacto - Add to basket",
                f"""
                <p>Cannot add service to basket of client {self._basket.client.name}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot add service to basket of client {client_id}"
                f" - Reason is: {response.reason}"
            )

    def remove_item_from_basket(self, item_id: int) -> bool:
        client_id = self._basket.client_id
        response = api.client.remove_item(client_id, item_id=item_id)

        if response.status is CommandStatus.COMPLETED:
            self.remove_item(item_id)
            return self._update_basket(client_id)

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"Dfacto - Remove item from basket",
                f"""
                <p>Cannot remove service from basket of client {self._basket.client.name}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot remove item from the basket of client {client_id}"
                f" - Reason is: {response.reason}"
            )

    def update_item_quantity_in_basket(self, item_id: int, quantity: int) -> bool:
        client_id = self._basket.client_id
        response = api.client.update_item_quantity(
            client_id, item_id=item_id, quantity=quantity
        )
        # self.cmdReported.emit(cmdReport)
        if response.status is CommandStatus.COMPLETED:
            self.update_item(response.body)
            return self._update_basket(client_id)

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"Dfacto - Update basket",
                f"""
                <p>Cannot update basket of client {self._basket.client.name}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot update item quantity in the basket of client {client_id}"
                f" - Reason is: {response.reason}"
            )

    def update_service_in_basket(self, service_id: int) -> bool:
        client_id = self._basket.client_id
        response = api.client.get_item_from_service(client_id, service_id=service_id)

        if response.status is CommandStatus.COMPLETED:
            self.update_item(response.body)
            return self._update_basket(client_id)

        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"Dfacto - Update basket",
                f"""
                <p>Cannot update basket of client {self._basket.client.name}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )
            return False

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Service {service_id} not found in basket of client {client_id}"
                f" - Reason is: {response.reason}"
            )

    def empty_basket(self) -> bool:
        client_id = self._basket.client_id
        response = api.client.clear_basket(client_id)

        if response.status is CommandStatus.COMPLETED:
            self.clear_items()
            return self._update_basket(self._basket.client_id)

        QtUtil.raise_fatal_error(
            f"Cannot empty basket of client {client_id}"
            f" - Reason is: {response.reason}"
        )
        return False

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
            self._items[item.id] = [
                item.service.id,
                item.service.name,
                item.service.unit_price,
                item.quantity,
                item.amount.raw,
                item.service.vat_rate.rate,
                item.amount.vat,
                item.amount.net,
            ]
            self._services_map[item.service.id] = item.id

        self.endInsertRows()

    def add_item(self, item: schemas.Item) -> None:
        self.add_items([item])

    def update_item(self, item: schemas.Item) -> None:
        start_index = self.index_from_item_id(item.id)
        if start_index.isValid():
            self._items[item.id] = [
                item.service.id,
                item.service.name,
                item.service.unit_price,
                item.quantity,
                item.amount.raw,
                item.service.vat_rate.rate,
                item.amount.vat,
                item.amount.net,
            ]
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
                    return "Select 'Quantity' field to edit"

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
                    print(f"setData: row: {row}, quantity: {value}")
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
    def _get_basket_of_client(client_id: int) -> Optional[schemas.Basket]:
        response = api.client.get_basket(client_id)

        if response.status is CommandStatus.COMPLETED:
            basket: schemas.Basket = response.body
            return basket

        QtUtil.raise_fatal_error(
            f"Cannot retrieve the basket of client {client_id}"
            f" - Reason is: {response.reason}"
        )

    def _update_basket(self, client_id: int) -> bool:
        basket = self._get_basket_of_client(client_id)
        self._basket = basket
        self.basket_updated.emit(basket)
        return basket is not None


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

        self.header_lbl = QtWidgets.QLabel("BASKET")
        self.header_lbl.setMaximumHeight(32)
        self.client_pix = QtWidgets.QLabel()
        self.client_pix.setPixmap(self.active_pix)
        self.client_lbl = QtWidgets.QLabel()

        icon_size = QtCore.QSize(48, 48)
        self.clear_btn = QtWidgets.QPushButton(
            QtGui.QIcon(f"{resources}/clear-basket.png"), ""
        )
        self.clear_btn.setIconSize(icon_size)
        self.clear_btn.setToolTip("Remove all items from basket")
        self.clear_btn.setStatusTip("Remove all items from basket")
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
        self.invoicing_btn.setToolTip("Create invoice from basket")
        self.invoicing_btn.setStatusTip("Create invoice from basket")
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

    @QtCore.pyqtSlot(schemas.Client)
    def set_current_client(self, client: schemas.Client) -> None:
        self._current_client = client
        self.client_lbl.setText(f"{client.name}")
        self.client_pix.setPixmap(
            self.active_pix if client.is_active else self.inactive_pix
        )

        print(f"Load basket of client: {client.id}")
        success = self._basket_table.load_basket(client.id)
        if not success or self._basket_table.model().rowCount() < 1:
            self._enable_buttons(False)

    @QtCore.pyqtSlot(schemas.Basket)
    def update_summary(self, basket: schemas.Basket) -> None:
        print(f"update total")
        nbsp = "\u00A0"
        if basket is None or len(basket.items) == 0:
            item_count = "Basket is empty".replace(" ", nbsp)
            total = 0
            total_str = "\nNothing to invoice".replace(" ", nbsp)
        else:
            count = len(basket.items)
            if count == 1:
                item_count = f"<strong>1</strong>{nbsp}item{nbsp}in{nbsp}basket\n"
            else:
                item_count = f"<strong>{count}</strong>{nbsp}items{nbsp}in{nbsp}basket"
            total = basket.amount.net
            total_str = f"\nTotal{nbsp}to{nbsp}invoice:{nbsp}<strong>{total}</strong>"

        self.summary_lbl.setText(f"{item_count}{total_str}")
        self._enable_buttons(total > 0)

    @QtCore.pyqtSlot()
    def clear_basket(self) -> None:
        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Delete service",
            f"""
            <p>Do you really want to empty the basket for this client?</p>
            <p><strong>{self._current_client.name}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
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

        QtUtil.raise_fatal_error(
            f"Cannot create invoice for {self._current_client.name}"
            f" - Reason is: {response.reason}"
        )

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

            print(f"Edit qty - proxy ({proxy_index.row()}, {proxy_index.column()})")
            print(f"Edit qty - source ({source_index.row()}, {source_index.column()})")
            print()
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
        print(f"Rows inserted: {first}, {last}")
        if last < 0:
            # No rows was inserted
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
        print(f"Rows removed: {first}, {last}")
        if last < 0:
            # No rows was removed
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
    ) -> QtWidgets:
        proxy_model = index.model()
        source_index = proxy_model.mapToSource(index)
        column = source_index.column()

        if column == QUANTITY:
            editor = QtWidgets.QSpinBox(parent)
            editor.setFrame(False)
            editor.setMaximum(100)
            editor.setAccelerated(True)
            price_tip = "Service quantity, from 1 to 100"
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
                print(f"setModelData: row: {source_index.row()}, quantity: {value}")
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
    _isVatVisible = True

    @classmethod
    def isVatVisible(cls) -> bool:
        return cls._isVatVisible

    def setIsVatVisible(self, value: bool) -> None:
        BasketFilterProxyModel._isVatVisible = value
        self.invalidateFilter()

    def filterAcceptsColumn(
        self, sourceColumn: int, sourceParent: QtCore.QModelIndex
    ) -> bool:
        if sourceColumn == ID:
            return False
        if self._isVatVisible:
            if sourceColumn in VAT_COLUMNS:
                return True
            return False
        else:
            if sourceColumn in NOVAT_COLUMNS:
                return True
            return False
