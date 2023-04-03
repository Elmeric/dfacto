# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from copy import copy
from enum import IntEnum
from typing import Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.util import qtutil as QtUtil

from .serviceeditor import Service, ServiceEditor

logger = logging.getLogger(__name__)


class ServiceSelector(QtUtil.QFramedWidget):
    class UserRoles(IntEnum):
        ServiceRole = QtCore.Qt.ItemDataRole.UserRole + 1

    basket_changed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None) -> None:
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
        self.add_to_selector = QtUtil.BasketController(
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
        tool_layout.addWidget(self.add_to_selector)

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
        main_layout.addStretch()
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
        self.add_to_selector.quantity_changed.connect(self.update_basket)
        self.service_editor.finished.connect(self.apply)

        self._forbidden_names: list[str] = []
        self.current_client: Optional[schemas.Client] = None

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

        response = api.service.get_all()

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot load the services list - Reason is: %s", response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                "Cannot load the services list", is_warning=True
            )
            return

        for service in response.body:
            self._add_item_from_service(service)

        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        self.services_lst.setCurrentRow(0)

        self._enable_buttons(self.services_lst.count() > 0)

    @QtCore.pyqtSlot(schemas.Client)
    def set_current_client(self, client: schemas.Client) -> None:
        self.current_client = client
        self.update_basket_controller()

    @QtCore.pyqtSlot()
    def on_service_selection(self) -> None:
        current_service = self.current_service
        if current_service is None:
            return

        self._show_in_editor(current_service)
        self.update_basket_controller()

    @QtCore.pyqtSlot()
    def open_editor(self, mode: ServiceEditor.Mode) -> None:
        if mode is ServiceEditor.Mode.EDIT:
            current_service = self.current_service
            assert current_service is not None

            forbidden_names = copy(self._forbidden_names)
            forbidden_names.remove(current_service.name)

            self.service_editor.edit_service(forbidden_names)

        if mode is ServiceEditor.Mode.ADD:
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

        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Delete service",
            f"""
            <p>Do you really want to delete this service permanently?</p>
            <p><strong>{service.name}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        response = api.service.delete(service.id)
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot delete service %s - Reason is: %s",
                service.name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot delete service {service.name}", is_warning=True
            )
            return

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

    @QtCore.pyqtSlot(int)
    def update_basket(self, delta: int) -> None:
        assert self.current_service is not None

        if delta == 0:
            success = self._remove_from_basket()
        else:
            success = self._add_to_basket(delta)

        if success:
            self.basket_changed.emit(self.current_service.id if delta != 0 else -1)
        else:
            quantity = self.add_to_selector.quantity
            self.add_to_selector.reset(quantity - delta)

    def update_basket_controller(self) -> None:
        current_service = self.current_service
        current_client = self.current_client
        if current_client is None or current_service is None:
            quantity = 0
        else:
            response = api.client.get_quantity_in_basket(
                self.current_client.id, service_id=current_service.id
            )
            if response.status is not CommandStatus.COMPLETED:
                logger.warning(
                    "Cannot retrieve service usage - Reason is: %s", response.reason
                )
                QtUtil.getMainWindow().show_status_message(
                    f"Cannot retrieve service usage", is_warning=True
                )
                quantity = 0
            else:
                quantity = response.body
        self.add_to_selector.reset(quantity)

    @QtCore.pyqtSlot(str)
    def select_service_by_name(self, name: str) -> None:
        if name == "":
            return

        items = self.services_lst.findItems(name, QtCore.Qt.MatchFlag.MatchExactly)
        if len(items) > 0:
            row = self.services_lst.row(items[0])
            if row != self.services_lst.currentRow():
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
        self.add_to_selector.setEnabled(enable)

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

        updated_service = {}

        if (name := service.name) != old_name:
            updated_service["name"] = name
        if (price := service.unit_price) != origin_service.unit_price:
            updated_service["unit_price"] = price
        if (value := service.vat_rate_id) != origin_service.vat_rate.id:
            updated_service["vat_rate_id"] = value

        response = api.service.update(
            origin_service.id, obj_in=schemas.ServiceUpdate(**updated_service)
        )
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot update the selected service %s - Reason is: %s",
                old_name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot update the selected service {old_name}", is_warning=True
            )
            self._show_in_editor(origin_service)
            return

        QtUtil.getMainWindow().show_status_message(f"Service update success!")

        new_service = response.body

        current_item = self.services_lst.currentItem()
        current_item.setData(ServiceSelector.UserRoles.ServiceRole, new_service)
        self._show_in_editor(new_service)

        if (new_name := service.name) is not None:
            current_item.setText(new_name)
            idx = self._forbidden_names.index(old_name)
            self._forbidden_names[idx] = new_name
            self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)

        self.basket_changed.emit(new_service.id)

        self.services_lst.setFocus()

    def _add_service(self, service: Service) -> None:
        response = api.service.add(obj_in=schemas.ServiceCreate(*service))

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot create the new service %s - Reason is: %s",
                service.name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot create the new service {service.name}", is_warning=True
            )
            self._show_in_editor(self.current_service)
            return

        QtUtil.getMainWindow().show_status_message(f"Service update success!")

        item = self._add_item_from_service(response.body)

        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        row = self.services_lst.row(item)
        self.services_lst.setCurrentRow(row)
        self._enable_buttons(True)
        self.services_lst.setFocus()

    def _remove_from_basket(self) -> bool:
        response = api.client.remove_from_basket(
            self.current_client.id,
            service_id=self.current_service.id,
        )
        if response.status is not CommandStatus.COMPLETED:
            logger.warning("Cannot remove service - Reason is: %s", response.reason)
            QtUtil.getMainWindow().show_status_message(
                f"Cannot remove service", is_warning=True
            )
        return response.status is CommandStatus.COMPLETED

    def _add_to_basket(self, qty: int) -> bool:
        response = api.client.add_to_basket(
            self.current_client.id, service_id=self.current_service.id, quantity=qty
        )
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot add service to basket - Reason is: %s", response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot add service to basket", is_warning=True
            )
        return response.status is CommandStatus.COMPLETED
