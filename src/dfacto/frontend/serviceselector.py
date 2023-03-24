# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from enum import IntEnum

import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
from dfacto.util import qtutil as QtUtil

from dfacto import settings as Config
from dfacto.backend import api
from dfacto.backend.api import CommandStatus

logger = logging.getLogger(__name__)


class ServiceListItem(QtWidgets.QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ServiceSelector(QtWidgets.QWidget):
    class UserRoles(IntEnum):
        IdRole = QtCore.Qt.ItemDataRole.UserRole + 1

    service_selected = QtCore.pyqtSignal(int)
    edition_selected = QtCore.pyqtSignal(int)
    add_selected = QtCore.pyqtSignal(int)
    add_to_selected = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        resources = Config.dfacto_settings.resources

        # self.setSizePolicy(
        #     QtWidgets.QSizePolicy.Policy.Preferred,
        #     QtWidgets.QSizePolicy.Policy.Maximum
        # )

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
        main_layout.addLayout(tool_layout)
        main_layout.addWidget(self.services_lst)
        self.setLayout(main_layout)

        self.services_lst.currentItemChanged.connect(self.show_service)
        self.services_lst.itemActivated.connect(self.edit_service)
        self.services_lst.itemDoubleClicked.connect(self.edit_service)
        self.edit_btn.clicked.connect(self.edit_service)
        self.new_btn.clicked.connect(self.add_service)
        self.delete_btn.clicked.connect(self.delete_service)

        self.forbidden_names = []

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
            item = QtWidgets.QListWidgetItem(service.name)
            item.setData(ServiceSelector.UserRoles.IdRole, service.id)
            self.services_lst.addItem(item)
            self.forbidden_names.append(service.name)

        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        self.services_lst.setCurrentRow(0)

    @QtCore.pyqtSlot(str, str)
    def update_service(self, old_name: str, new_name: str) -> None:
        current_item = self.services_lst.currentItem()
        current_item.setText(new_name)
        idx = self.forbidden_names.index(old_name)
        self.forbidden_names[idx] = new_name
        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        self.services_lst.setFocus()

    @QtCore.pyqtSlot(str, int)
    def update_service_list(self, name: str, id_: int) -> None:
        item = QtWidgets.QListWidgetItem(name)
        item.setData(ServiceSelector.UserRoles.IdRole, id_)
        self.services_lst.addItem(item)
        self.forbidden_names.append(name)
        self.services_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        row = self.services_lst.row(item)
        self.services_lst.setCurrentRow(row)
        self.services_lst.setFocus()

    @QtCore.pyqtSlot(QtWidgets.QListWidgetItem, QtWidgets.QListWidgetItem)
    def show_service(
        self, current_item: QtWidgets.QListWidgetItem, _previous: QtWidgets.QListWidgetItem
    ) -> None:
        service_id = current_item.data(ServiceSelector.UserRoles.IdRole)
        self.service_selected.emit(service_id)

    @QtCore.pyqtSlot()
    def edit_service(self) -> None:
        current_item = self.services_lst.currentItem()
        service_id = current_item.data(ServiceSelector.UserRoles.IdRole)
        self.edition_selected.emit(service_id)

    @QtCore.pyqtSlot()
    def add_service(self) -> None:
        current_item = self.services_lst.currentItem()
        service_id = current_item.data(ServiceSelector.UserRoles.IdRole)
        self.add_selected.emit(service_id)

    @QtCore.pyqtSlot()
    def delete_service(self) -> None:
        row = self.services_lst.currentRow()
        current_item = self.services_lst.currentItem()
        service_id = current_item.data(ServiceSelector.UserRoles.IdRole)
        service_name = current_item.text()

        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Delete service",
            f"""
            <p>Do you really want to delete this service permanently?</p>
            <p><strong>{service_name}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        _deleted_item = self.services_lst.takeItem(row)
        del _deleted_item

        response = api.service.delete(service_id)
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot delete service %s - Reason is: %s",
                service_name, response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot delete service {service_name}",
                is_warning=True
            )
            return

        self.forbidden_names.remove(service_name)
        self.services_lst.setCurrentRow(max(0, row - 1))
        self.services_lst.setFocus()
