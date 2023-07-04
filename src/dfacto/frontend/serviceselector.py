# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from copy import copy
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.util import qtutil as QtUtil

from .serviceeditor import Service, ServiceEditor

if TYPE_CHECKING:
    from .basketviewer import BasketTableModel

logger = logging.getLogger(__name__)


class BasketController(QtWidgets.QWidget):
    _service_id: int
    _quantity: int = 0
    _folded: bool = True
    _model: Optional["BasketTableModel"] = None
    _current_index: QtCore.QModelIndex = QtCore.QModelIndex()

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

        self.basket_btn.clicked.connect(self.add_first)
        self.add_btn.clicked.connect(self.increase)
        self.minus_btn.clicked.connect(self.decrease)
        self.quantity_lbl.editingFinished.connect(self.input_quantity)

        self.reset(0)

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, qty: int) -> None:
        success = False
        if qty == 0:
            # On update, 0 means "remove from basket"
            self._fold()
            success = self.model().setData(self._current_index, qty)
        elif qty > 0:
            if self._folded:
                # add first quantity (1) in basket
                self._unfold()
                success = self.model().add_service_to_basket(self._service_id, qty)
                if success:
                    self._current_index = self.model().index_from_service_id(
                        self._service_id
                    )
            else:
                # Increment or decrement the basket quantity
                success = self.model().setData(self._current_index, qty)

        if success:
            self.reset(qty)
        else:
            self.reset(self._quantity)

    @QtCore.pyqtSlot()
    def add_first(self) -> None:
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
        if not obj.isModified():  # noqa
            # Ignore second signal
            return
        obj.setModified(False)  # noqa

        qty_str = self.quantity_lbl.text()
        quantity = 0 if qty_str == "" else int(qty_str)
        try:
            self.quantity = min(self._max, max(0, quantity))
        except ValueError:
            # Ignore invalid input and display the previous quantity
            self.quantity_lbl.setText(str(self._quantity))

    def model(self) -> "BasketTableModel":
        return self._model

    def set_model(self, model: "BasketTableModel") -> None:
        self._model = model
        model.dataChanged.connect(self.on_data_changed)

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def on_data_changed(
        self, top_left: QtCore.QModelIndex, _bottom_right: QtCore.QModelIndex
    ) -> None:
        self.reset(self.model().quantity_from_index(top_left))

    def current_service(self) -> int:
        return self._service_id

    def set_current_service(self, service_id: int) -> None:
        self._service_id = service_id

        quantity = self.model().quantity_in_basket(service_id)
        self.reset(quantity)

        self._current_index = self.model().index_from_service_id(service_id)

    def update_basket(self, service_id: int) -> None:
        model = self.model()
        if model.is_service_in_basket(service_id):
            model.update_service_in_basket(service_id)

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


class ServiceSelector(QtUtil.QFramedWidget):
    class UserRoles(IntEnum):
        ServiceRole = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(self, basket_model: "BasketTableModel", parent=None) -> None:
        super().__init__(parent=parent)

        resources = Config.dfacto_settings.resources

        header_lbl = QtWidgets.QLabel("SERVICES LIST")
        header_lbl.setMaximumHeight(32)

        self.service_editor = ServiceEditor()

        icon_size = QtCore.QSize(32, 32)
        self.new_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/add.png"), "")
        self.new_btn.setIconSize(icon_size)
        self.new_btn.setToolTip("Create a new service")
        self.new_btn.setStatusTip("Create a new service")
        self.new_btn.setFlat(True)
        self.delete_btn = QtWidgets.QPushButton(
            QtGui.QIcon(f"{resources}/remove.png"), ""
        )
        self.delete_btn.setToolTip("Delete the selected service (Delete)")
        self.delete_btn.setStatusTip("Delete the selected service (Delete)")
        self.delete_btn.setIconSize(icon_size)
        self.delete_btn.setFlat(True)
        self.edit_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/edit.png"), "")
        self.edit_btn.setIconSize(icon_size)
        self.edit_btn.setToolTip("Edit the selected service")
        self.edit_btn.setStatusTip("Edit the selected service")
        self.edit_btn.setFlat(True)

        self.basket_controller = BasketController(
            basket_icon=QtGui.QIcon(f"{resources}/add-to-basket.png"),
            add_icon=QtGui.QIcon(f"{resources}/add-blue.png"),
            minus_icon=QtGui.QIcon(f"{resources}/minus-blue.png"),
        )

        self.services_lst = QtUtil.UndeselectableListWidget()

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
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        header.setLayout(header_layout)

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.new_btn)
        tool_layout.addWidget(self.delete_btn)
        tool_layout.addWidget(self.edit_btn)
        tool_layout.addStretch()
        tool_layout.addWidget(self.basket_controller)

        selector_widget = QtWidgets.QWidget()
        selector_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        editor_layout = QtWidgets.QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addLayout(tool_layout)
        editor_layout.addWidget(self.services_lst)
        selector_widget.setLayout(editor_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.service_editor)
        main_layout.addWidget(header)
        main_layout.addWidget(selector_widget)
        self.setLayout(main_layout)

        self.services_lst.itemSelectionChanged.connect(self.on_service_selection)
        self.services_lst.itemActivated.connect(
            lambda: self.open_editor(mode=ServiceEditor.Mode.EDIT)
        )
        self.services_lst.itemDoubleClicked.connect(
            lambda: self.open_editor(mode=ServiceEditor.Mode.EDIT)
        )
        self.edit_btn.clicked.connect(
            lambda: self.open_editor(mode=ServiceEditor.Mode.EDIT)
        )
        self.new_btn.clicked.connect(
            lambda: self.open_editor(mode=ServiceEditor.Mode.ADD)
        )
        self.delete_btn.clicked.connect(self.delete_service)
        self.service_editor.finished.connect(self.apply)

        self.basket_controller.set_model(basket_model)
        self._forbidden_names: list[str] = []

    @property
    def current_service(self) -> Optional[schemas.Service]:
        current_item = self.services_lst.currentItem()
        if current_item is None:
            return
        return current_item.data(ServiceSelector.UserRoles.ServiceRole)

    @property
    def editor_mode(self) -> ServiceEditor.Mode:
        return self.service_editor.mode

    def load_services(self) -> None:
        self.services_lst.clear()
        self.service_editor.clear()
        self._forbidden_names = []

        response = api.service.get_all(current_only=True)

        if response.status is not CommandStatus.COMPLETED:
            QtUtil.raise_fatal_error(
                f"Cannot load the services list - Reason is: {response.reason}"
            )

        for service in response.body:
            self._add_item_from_service(service)

        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        self.services_lst.setCurrentRow(0)

        self._enable_buttons(self.services_lst.count() > 0)

    @QtCore.pyqtSlot()
    def on_service_selection(self) -> None:
        current_service = self.current_service
        if current_service is None:
            return

        self._show_in_editor(current_service)
        self.basket_controller.set_current_service(current_service.id)

    @QtCore.pyqtSlot()
    def open_editor(self, mode: ServiceEditor.Mode) -> None:
        if mode is ServiceEditor.Mode.EDIT:
            current_service = self.current_service
            assert current_service is not None

            forbidden_names = copy(self._forbidden_names)
            forbidden_names.remove(current_service.name)

            self.service_editor.edit_service(forbidden_names)

            return

        # mode is ServiceEditor.Mode.ADD:
        self.service_editor.add_service(self._forbidden_names)

    @QtCore.pyqtSlot(QtWidgets.QDialog.DialogCode)
    def apply(self, result: QtWidgets.QDialog.DialogCode) -> None:
        if result == QtWidgets.QDialog.DialogCode.Rejected:
            self._show_in_editor(self.current_service)
            self.services_lst.setFocus()
            return

        if self.editor_mode is ServiceEditor.Mode.EDIT:
            self._update_service(self.service_editor.service)

        elif self.editor_mode is ServiceEditor.Mode.ADD:
            self._add_service(self.service_editor.service)

    @QtCore.pyqtSlot()
    def delete_service(self) -> None:
        row = self.services_lst.currentRow()
        service = self.current_service
        assert service is not None

        reply = QtUtil.question(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Delete service",
            f"""
            <p>Do you really want to delete this service permanently?</p>
            <p><strong>{service.name}</strong></p>
            """,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        response = api.service.delete(
            service.id,
        )

        if response.status is CommandStatus.COMPLETED:
            _deleted_item = self.services_lst.takeItem(row)
            del _deleted_item

            self._forbidden_names.remove(service.name)

            if self.services_lst.count() == 0:
                self._show_in_editor(None)
                self._enable_buttons(False)
                self.new_btn.setFocus()
            else:
                self.services_lst.setCurrentRow(row - 1)
                self.services_lst.setFocus()
            return

        if response.status is CommandStatus.REJECTED:
            QtUtil.warning(
                None,  # type: ignore
                f"Dfacto - Delete service",
                f"""
                <p>Cannot delete service {service.name}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
            )
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot delete service {service.name}"
                f" - Reason is: {response.reason}"
            )

    @QtCore.pyqtSlot(str)
    def select_service_by_name(self, name: str) -> None:
        if name == "":
            with QtCore.QSignalBlocker(self.services_lst.selectionModel()):
                self.services_lst.clearSelection()
            self.services_lst.setCurrentRow(0)
            return

        items = self.services_lst.findItems(name, QtCore.Qt.MatchFlag.MatchExactly)
        if len(items) > 0:
            row = self.services_lst.row(items[0])
            with QtCore.QSignalBlocker(self.services_lst.selectionModel()):
                self.services_lst.clearSelection()
            self.services_lst.setCurrentRow(row)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()

        if key == QtCore.Qt.Key.Key_Delete:
            self.delete_service()
            return

        super().keyPressEvent(event)

    def _enable_buttons(self, enable: bool) -> None:
        self.delete_btn.setEnabled(enable)
        self.edit_btn.setEnabled(enable)
        self.basket_controller.setEnabled(enable)

    def _add_item_from_service(
        self, service: schemas.Service
    ) -> QtWidgets.QListWidgetItem:
        item = QtWidgets.QListWidgetItem(service.name)
        item.setData(ServiceSelector.UserRoles.ServiceRole, service)
        self.services_lst.addItem(item)

        self._forbidden_names.append(service.name)

        return item

    def _show_in_editor(self, service: Optional[schemas.Service]) -> None:
        self.service_editor.show_service(service)

    def _update_service(self, service: Service) -> None:
        origin_service = self.current_service
        assert origin_service is not None
        old_name = origin_service.name

        updated_data = {}

        if (name := service.name) != old_name:
            updated_data["name"] = name
        if (price := service.unit_price) != origin_service.unit_price:
            updated_data["unit_price"] = price
        if (value := service.vat_rate_id) != origin_service.vat_rate.id:
            updated_data["vat_rate_id"] = value

        response = api.service.update(
            origin_service.id, obj_in=schemas.ServiceUpdate(**updated_data)
        )
        if response.status is not CommandStatus.COMPLETED:
            QtUtil.raise_fatal_error(
                f"Cannot update the selected service {old_name}"
                f" - Reason is: {response.reason}"
            )

        updated_service: schemas.Service = response.body

        current_item = self.services_lst.currentItem()
        current_item.setData(ServiceSelector.UserRoles.ServiceRole, updated_service)
        self._show_in_editor(updated_service)

        if (new_name := service.name) is not None:
            current_item.setText(new_name)
            idx = self._forbidden_names.index(old_name)
            self._forbidden_names[idx] = new_name
            self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)

        # Propagate changes to the basket
        self.basket_controller.update_basket(updated_service.id)

        self.services_lst.setFocus()

    def _add_service(self, service: Service) -> None:
        response = api.service.add(obj_in=schemas.ServiceCreate(*service))

        if response.status is not CommandStatus.COMPLETED:
            QtUtil.raise_fatal_error(
                f"Cannot create the new service {service.name}"
                f" - Reason is: {response.reason}"
            )

        item = self._add_item_from_service(response.body)

        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        row = self.services_lst.row(item)
        self.services_lst.setCurrentRow(row)
        self._enable_buttons(True)
        self.services_lst.setFocus()
