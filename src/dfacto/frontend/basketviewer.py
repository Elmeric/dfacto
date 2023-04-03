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
from dfacto.backend.api import CommandResponse, CommandStatus
from dfacto.util import qtutil as QtUtil

logger = logging.getLogger(__name__)

BasketItem = list[int, str, float, int, float, float, float, float]

SERVICE, UNIT_PRICE, QUANTITY, RAW_AMOUNT, VAT, VAT_RATE, NET_AMOUNT = range(7)
VAT_COLUMNS = (SERVICE, UNIT_PRICE, QUANTITY, RAW_AMOUNT, VAT, VAT_RATE, NET_AMOUNT)
NOVAT_COLUMNS = (SERVICE, UNIT_PRICE, QUANTITY, NET_AMOUNT)


class BasketTableModel(QtCore.QAbstractTableModel):
    basket_changed = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._headers = [
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

    def set_basket(self, basket: schemas.Basket) -> None:
        self._basket = basket

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
            return self.index(row, 0)

    def clear_basket(self) -> None:
        self.beginResetModel()
        self._items = {}
        self._item_ids = []
        self.endResetModel()

    def load_basket(self) -> None:
        self.clear_basket()
        self.add_items(self._basket.items)

    def add_items(self, items: list[schemas.Item]) -> None:
        dict_items = {
            item.id: [
                item.service.name,
                item.service.unit_price,
                item.quantity,
                item.raw_amount,
                item.service.vat_rate.rate,
                item.vat,
                item.net_amount,
            ]
            for item in items
        }
        row = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), row, row + len(items) - 1)
        self._items.update(dict_items)
        self._item_ids.extend(list(dict_items))
        self.endInsertRows()

    def update_item(self, item_id: int) -> None:
        index = self.index_from_item_id(item_id)
        if index.isValid():
            self.dataChanged.emit(
                index,
                index,
                (QtCore.Qt.ItemDataRole.DisplayRole,),
            )

    def remove_item(self, index: QtCore.QModelIndex) -> CommandResponse:
        row = index.row()
        key = self._item_ids[row]

        response = api.client.remove_item(self._basket.client_id, item_id=key)

        if response.status == CommandStatus.COMPLETED:
            self.beginRemoveRows(QtCore.QModelIndex(), row, row)
            del self._items[key]
            del self._item_ids[row]
            self.endRemoveRows()

        return response

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
            boldFont = QtGui.QFont()
            boldFont.setBold(True)
            return boldFont

        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == QtCore.Qt.Orientation.Horizontal:
            return self._headers[section]

        return int(section + 1)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        if index.isValid():
            column = index.column()

            if column == QUANTITY:
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

                if role == QtCore.Qt.ItemDataRole.FontRole:
                    if column == SERVICE:
                        boldFont = QtGui.QFont()
                        boldFont.setBold(True)
                        return boldFont

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
                item = self._items[item_id]

                if column == QUANTITY:
                    response = api.client.update_item_quantity(
                        self._basket.client_id, item_id=item_id, quantity=value
                    )
                    # self.cmdReported.emit(cmdReport)
                    if response.status == CommandStatus.COMPLETED:
                        item[column] = value
                        self.dataChanged.emit(index, index)
                        self.basket_changed.emit()

                    return response.status == CommandStatus.COMPLETED

                return super().setData(index, value, role)

        return False

    def _item_id_from_index(self, index: QtCore.QModelIndex) -> Optional[int]:
        if index.isValid():
            row = index.row()
            if 0 <= row < self.rowCount():
                return self._item_ids[row]
        return None


class BasketViewer(QtUtil.QFramedWidget):
    selection_changed = QtCore.pyqtSignal(str)  # service name of the selected item

    def __init__(self, basket_model: BasketTableModel, parent=None) -> None:
        super().__init__(parent=parent)

        self.header_lbl = QtWidgets.QLabel("BASKET")
        self.header_lbl.setMaximumHeight(32)

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
        header_layout.setContentsMargins(5, 5, 0, 5)
        header_layout.setSpacing(5)
        header_layout.addWidget(self.header_lbl)
        header.setLayout(header_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header)
        main_layout.addWidget(self._basket_table)
        main_layout.addStretch()
        self.setLayout(main_layout)

        self._basket_table.selection_changed.connect(self.selection_changed)

        self._current_client: Optional[schemas.Client] = None

    @QtCore.pyqtSlot(schemas.Client)
    def set_current_client(self, client: schemas.Client) -> None:
        self._current_client = client
        self.update_basket()

    @QtCore.pyqtSlot(int)
    def update_basket(self, service_id: int = -1) -> None:
        client = self._current_client

        response = api.client.get_basket(client.id)

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Basket not found for client %s - Reason is: %s",
                client.name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Basket not found for client {client.name}", is_warning=True
            )
            return

        basket = response.body
        proxy = self._basket_table.model()
        model = proxy.sourceModel()
        # Register the client id and basket in the model and load the basket content.
        model.set_basket(basket)
        model.load_basket()

        self.header_lbl.setText(
            f"BASKET - {client.name} - Net amount = {basket.net_amount}"
        )

        if service_id < 0:
            QtCore.QTimer.singleShot(0, self._basket_table.select_first_item)
        else:
            response = api.client.get_item_from_service(
                client.id, service_id=service_id
            )

            if response.status is not CommandStatus.COMPLETED:
                logger.warning(
                    "Service %s not found in basket of client %s - Reason is: %s",
                    service_id,
                    client.name,
                    response.reason,
                )
                QtUtil.getMainWindow().show_status_message(
                    f"Service {service_id} not found in basket of client {client.name}",
                    is_warning=True,
                )
                QtCore.QTimer.singleShot(0, self._basket_table.select_first_item)
            else:
                item = response.body
                QtCore.QTimer.singleShot(
                    0, lambda: self._basket_table.select_item(item.id)
                )


class BasketTable(QtWidgets.QTableView):
    selection_changed = QtCore.pyqtSignal(str)  # service name of the selected item

    def __init__(self, basket_model: BasketTableModel, parent=None) -> None:
        super().__init__(parent=parent)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
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
        # self._basket_table_model = basket_model
        # self._basket_table_model.cmdReported.connect(self.showCommandReport)
        proxy_model.setSourceModel(basket_model)
        self.setModel(proxy_model)

        self.clicked.connect(self.on_click)
        self.selectionModel().selectionChanged.connect(self.on_item_selection)  # noqa

        if proxy_model.rowCount() > 0:
            self.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
            for column in range(proxy_model.columnCount()):
                self.horizontalHeader().setSectionResizeMode(
                    column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                )
            QtCore.QTimer.singleShot(0, self.select_first_item)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def on_click(self, index: QtCore.QModelIndex) -> None:
        self._edit_quantity(index.row())

        proxy_model = self.model()
        source_model = proxy_model.sourceModel()
        source_index = proxy_model.mapToSource(index)
        service_name = source_model.item_from_index(source_index)[SERVICE]
        self.selection_changed.emit(service_name)

    @QtCore.pyqtSlot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_item_selection(
        self, selected: QtCore.QItemSelection, _deselected: QtCore.QItemSelection
    ) -> None:
        if selected.indexes():
            current_index = selected.indexes()[-1]

            if current_index.isValid():
                self._edit_quantity(current_index.row())

                proxy_model = self.model()
                source_model = proxy_model.sourceModel()
                source_index = proxy_model.mapToSource(current_index)
                service_name = source_model.item_from_index(source_index)[0]
                self.selection_changed.emit(service_name)

        self.selection_changed.emit("")

    def select_first_item(self) -> None:
        self.selectRow(0)

    def select_item(self, item_id: int) -> None:
        proxy_model = self.model()
        source_model = proxy_model.sourceModel()
        source_index: QtCore.QModelIndex = source_model.index_from_item_id(item_id)
        proxy_index = proxy_model.mapFromSource(source_index)
        if proxy_index.isValid():
            self.selectRow(proxy_index.row())

    def _edit_quantity(self, row: int) -> None:
        proxy_model = self.model()
        quantity_index = proxy_model.index(row, QUANTITY)
        self.setCurrentIndex(quantity_index)
        self.edit(quantity_index)


class BasketTableDelegate(QtWidgets.QStyledItemDelegate):
    # class BasketTableDelegate(QtUtil.NoFocusDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

    def createEditor(
        self,
        parent: QtWidgets.QWidget,
        options: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> QtWidgets:
        proxy_model = index.model()
        sourceIndex = proxy_model.mapToSource(index)
        column = sourceIndex.column()

        if column == QUANTITY:
            editor = QtWidgets.QSpinBox(parent)
            editor.setFrame(False)
            editor.setMaximum(100)
            editor.setAccelerated(True)
            price_tip = "Service quantity, from 1 to 100"
            editor.setToolTip(price_tip)
            editor.setStatusTip(price_tip)
            return editor

        return super().createEditor(parent, options, index)

    def setEditorData(
        self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex
    ) -> None:
        proxy = index.model()
        sourceIndex = proxy.mapToSource(index)
        column = sourceIndex.column()

        if column == QUANTITY:
            editor: QtWidgets.QSpinBox
            value = str(index.model().data(index, QtCore.Qt.ItemDataRole.EditRole))
            if value:
                editor.setValue(int(value))
                return

        super().setEditorData(editor, index)

    def setModelData(
        self,
        editor: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ) -> None:
        sourceIndex = model.mapToSource(index)
        column = sourceIndex.column()

        if column == QUANTITY:
            editor: QtWidgets.QSpinBox
            value = editor.value()
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
        sourceIndex = proxy.mapToSource(index)
        column = sourceIndex.column()

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
        if self._isVatVisible:
            if sourceColumn in VAT_COLUMNS:
                return True
            return False
        else:
            if sourceColumn in NOVAT_COLUMNS:
                return True
            return False
