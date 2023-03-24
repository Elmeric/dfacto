# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from copy import copy
from enum import IntEnum

import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
from dfacto.util import qtutil as QtUtil

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from .serviceeditor import Service, ServiceEditor

logger = logging.getLogger(__name__)


class ServiceListItem(QtWidgets.QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ServiceSelector(QtWidgets.QWidget):
    class UserRoles(IntEnum):
        ServiceRole = QtCore.Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        resources = Config.dfacto_settings.resources

        # self.setSizePolicy(
        #     QtWidgets.QSizePolicy.Policy.Preferred,
        #     QtWidgets.QSizePolicy.Policy.Maximum
        # )

        self.service_editor = ServiceEditor()

        icon_size = QtCore.QSize(32, 32)
        self.new_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/add.png"), "")
        self.new_btn.setIconSize(icon_size)
        self.new_btn.setFlat(True)
        self.delete_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/remove.png"), "")
        self.delete_btn.setIconSize(icon_size)
        self.delete_btn.setFlat(True)
        self.edit_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/edit.png"), "")
        self.edit_btn.setIconSize(icon_size)
        self.edit_btn.setFlat(True)
        self.add_to_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/add-to-basket.png"), "")
        self.add_to_btn.setIconSize(icon_size)
        self.add_to_btn.setFlat(True)
        self.qty_selector = QtWidgets.QSpinBox()
        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setSpacing(0)
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.addWidget(self.new_btn)
        tool_layout.addWidget(self.delete_btn)
        tool_layout.addWidget(self.edit_btn)
        tool_layout.addWidget(self.add_to_btn)
        tool_layout.addWidget(self.qty_selector)
        tool_layout.addStretch()

        self.services_lst = QtWidgets.QListWidget()
        self.services_lst.setAlternatingRowColors(True)
        self.services_lst.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        # self.services_lst.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.services_lst.setStyleSheet(
            "QListView::item{border: 1px solid transparent;}"
            "QListView::item:selected{color: blue;}"
            "QListView::item:selected{background-color: rgba(0,0,255,64);}"
            "QListView::item:selected:hover{border-color: rgba(0,0,255,128);}"
            "QListView::item:hover{background: rgba(0,0,255,32);}"
        )
        self.services_lst.setItemDelegate(QtUtil.NoFocusDelegate(self))
        self.services_lst.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.services_lst.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.services_lst.setResizeMode(QtWidgets.QListWidget.ResizeMode.Adjust)
        # self.services_lst.setSizeAdjustPolicy(QtWidgets.QListWidget.SizeAdjustPolicy.AdjustToContents)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(5, 0, 0, 5)
        main_layout.addWidget(self.service_editor)
        main_layout.addLayout(tool_layout)
        main_layout.addWidget(self.services_lst)
        self.setLayout(main_layout)

        self.services_lst.currentItemChanged.connect(self.show_service)
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

        self._forbidden_names: list[str] = []

    @property
    def current_service(self) -> schemas.Service:
        current_item = self.services_lst.currentItem()
        return current_item.data(ServiceSelector.UserRoles.ServiceRole)

    @property
    def editor_mode(self) -> ServiceEditor.Mode:
        return self.service_editor.mode

    def load_services(self) -> None:
        response = api.service.get_all()

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot load the services list - Reason is: %s",
                response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                "Cannot load the services list",
                is_warning=True
            )
            return

        for service in response.body:
            self._add_item_from_service(service)

        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        self.services_lst.setCurrentRow(0)

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def show_service(
        self,
        _current: QtWidgets.QListWidgetItem,
        _previous: QtWidgets.QListWidgetItem
    ) -> None:
        self._show_in_editor(self.current_service)

    @QtCore.pyqtSlot()
    def open_editor(self, mode: ServiceEditor.Mode) -> None:
        if mode is ServiceEditor.Mode.EDIT:
            forbidden_names = copy(self._forbidden_names)
            forbidden_names.remove(self.current_service.name)

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

        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Delete service",
            f"""
            <p>Do you really want to delete this service permanently?</p>
            <p><strong>{service.name}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        _deleted_item = self.services_lst.takeItem(row)
        del _deleted_item

        response = api.service.delete(service.id)
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot delete service %s - Reason is: %s",
                service.name, response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot delete service {service.name}",
                is_warning=True
            )
            return

        self._forbidden_names.remove(service.name)

        self.services_lst.setCurrentRow(max(0, row - 1))
        self.services_lst.setFocus()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()

        if key == QtCore.Qt.Key.Key_Delete:
            self.delete_service()
            return

        super().keyPressEvent(event)

    def _add_item_from_service(
        self, service: schemas.Service
    ) -> QtWidgets.QListWidgetItem:
        item = QtWidgets.QListWidgetItem(service.name)
        item.setData(ServiceSelector.UserRoles.ServiceRole, service)
        self.services_lst.addItem(item)

        self._forbidden_names.append(service.name)

        return item

    def _show_in_editor(self, service: schemas.Service) -> None:
        self.service_editor.show_service(service)

    def _update_service(self, service: Service) -> None:
        origin_service = self.current_service
        old_name = origin_service.name

        updated_service = {}

        if (name := service.name) != old_name:
            updated_service["name"] = name
        if (price := service.unit_price) != origin_service.unit_price:
            updated_service["unit_price"] = price
        if (value := service.vat_rate_id) != origin_service.vat_rate.id:
            updated_service["vat_rate_id"] = value

        response = api.service.update(
            origin_service.id,
            obj_in=schemas.ServiceUpdate(**updated_service)
        )
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot update the selected service %s - Reason is: %s",
                old_name, response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot update the selected service {old_name}",
                is_warning=True
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

        self.services_lst.setFocus()

    def _add_service(self, service: Service) -> None:
        response = api.service.add(obj_in=schemas.ServiceCreate(*service))

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot create the new service %s - Reason is: %s",
                service.name, response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot create the new service {service.name}",
                is_warning=True
            )
            self._show_in_editor(self.current_service)
            return

        QtUtil.getMainWindow().show_status_message(f"Service update success!")

        item = self._add_item_from_service(response.body)

        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        row = self.services_lst.row(item)
        self.services_lst.setCurrentRow(row)
        self.services_lst.setFocus()
