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

from .clienteditor import Client, ClientEditor

logger = logging.getLogger(__name__)


class ClientSelector(QtUtil.QFramedWidget):
    class UserRoles(IntEnum):
        ClientRole = QtCore.Qt.ItemDataRole.UserRole + 1

    client_selected = QtCore.pyqtSignal(schemas.Client)

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

        resources = Config.dfacto_settings.resources

        self.active_icon = QtGui.QIcon(f"{resources}/client-active.png")
        self.inactive_icon = QtGui.QIcon(f"{resources}/client-inactive.png")

        header_lbl = QtWidgets.QLabel("CLIENTS LIST")
        header_lbl.setMaximumHeight(32)

        small_icon_size = QtCore.QSize(24, 24)
        self.inactive_ckb = QtWidgets.QCheckBox("")
        self.inactive_ckb.setToolTip("Include inactive accounts")
        self.inactive_ckb.setStatusTip("Include inactive accounts")
        self.inactive_ckb.setIconSize(small_icon_size)
        self.inactive_ckb.setIcon(self.inactive_icon)

        self.client_editor = ClientEditor()

        icon_size = QtCore.QSize(32, 32)
        self.new_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/add.png"), "")
        self.new_btn.setIconSize(icon_size)
        self.new_btn.setToolTip("Create a new client")
        self.new_btn.setStatusTip("Create a new client")
        self.new_btn.setFlat(True)
        self.delete_btn = QtWidgets.QPushButton(
            QtGui.QIcon(f"{resources}/remove.png"), ""
        )
        self.delete_btn.setToolTip("Delete the selected client (Delete)")
        self.delete_btn.setStatusTip("Delete the selected client (Delete)")
        self.delete_btn.setIconSize(icon_size)
        self.delete_btn.setFlat(True)
        self.edit_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/edit.png"), "")
        self.edit_btn.setIconSize(icon_size)
        self.edit_btn.setToolTip("Edit the selected client")
        self.edit_btn.setStatusTip("Edit the selected client")
        self.edit_btn.setFlat(True)
        self.activate_btn = QtWidgets.QPushButton(self.active_icon, "")
        self.activate_btn.setIconSize(icon_size)
        self.activate_btn.setToolTip("Toggle activation state for the selected client")
        self.activate_btn.setStatusTip(
            "Toggle activation state for the selected client"
        )
        self.activate_btn.setFlat(True)
        self.activate_btn.setCheckable(True)

        self.clients_lst = QtUtil.UndeselectableListWidget()

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
        header_layout.addWidget(self.inactive_ckb)
        header.setLayout(header_layout)

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.new_btn)
        tool_layout.addWidget(self.delete_btn)
        tool_layout.addWidget(self.edit_btn)
        tool_layout.addStretch()
        tool_layout.addWidget(self.activate_btn)

        selector_widget = QtWidgets.QWidget()
        selector_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        )
        editor_layout = QtWidgets.QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addLayout(tool_layout)
        editor_layout.addWidget(self.clients_lst)
        selector_widget.setLayout(editor_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.client_editor)
        main_layout.addWidget(header)
        main_layout.addWidget(selector_widget)
        main_layout.addStretch()
        self.setLayout(main_layout)

        self.clients_lst.itemSelectionChanged.connect(self.on_client_selection)
        self.clients_lst.itemActivated.connect(
            lambda: self.open_editor(mode=ClientEditor.Mode.EDIT)
        )
        self.clients_lst.itemDoubleClicked.connect(
            lambda: self.open_editor(mode=ClientEditor.Mode.EDIT)
        )
        self.edit_btn.clicked.connect(
            lambda: self.open_editor(mode=ClientEditor.Mode.EDIT)
        )
        self.new_btn.clicked.connect(
            lambda: self.open_editor(mode=ClientEditor.Mode.ADD)
        )
        self.delete_btn.clicked.connect(self.delete_client)
        self.activate_btn.clicked.connect(self.toggle_client_activation)
        self.inactive_ckb.stateChanged.connect(self.on_inactive_selection)
        self.client_editor.finished.connect(self.apply)

        self.inactive_ckb.setChecked(False)

        self._forbidden_names: list[str] = []

    @property
    def current_client(self) -> Optional[schemas.Client]:
        current_item = self.clients_lst.currentItem()
        if current_item is None:
            return
        return current_item.data(ClientSelector.UserRoles.ClientRole)

    @property
    def editor_mode(self) -> ClientEditor.Mode:
        return self.client_editor.mode

    def load_clients(self) -> None:
        self.clients_lst.clear()
        self.client_editor.clear()

        response = api.client.get_all()

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot load the clients list - Reason is: %s", response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                "Cannot load the clients list", is_warning=True
            )
            return

        for client in response.body:
            self._add_item_from_client(client, not self.inactive_ckb.isChecked())

        self.clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        self.clients_lst.setCurrentRow(0)

        self._enable_buttons(self.clients_lst.count() > 0)

    @QtCore.pyqtSlot(int)
    def on_inactive_selection(self, _checked: int):
        self.load_clients()

    @QtCore.pyqtSlot()
    def on_client_selection(self) -> None:
        current_client = self.current_client
        if current_client is None:
            self.activate_btn.setChecked(False)
            return

        self.activate_btn.setChecked(current_client.is_active)
        self._show_in_editor(current_client)
        self.client_selected.emit(current_client)

    @QtCore.pyqtSlot()
    def open_editor(self, mode: ClientEditor.Mode) -> None:
        if mode is ClientEditor.Mode.EDIT:
            current_client = self.current_client
            assert current_client is not None

            forbidden_names = copy(self._forbidden_names)
            forbidden_names.remove(current_client.name)

            self.client_editor.edit_client(forbidden_names)

        if mode is ClientEditor.Mode.ADD:
            self.client_editor.add_client(self._forbidden_names)

    @QtCore.pyqtSlot(QtWidgets.QDialog.DialogCode)
    def apply(self, result: QtWidgets.QDialog.DialogCode) -> None:
        if result == QtWidgets.QDialog.DialogCode.Rejected:
            self._show_in_editor(self.current_client)
            self.clients_lst.setFocus()
            return

        if self.editor_mode is ClientEditor.Mode.EDIT:
            self._update_client(self.client_editor.client)

        elif self.editor_mode is ClientEditor.Mode.ADD:
            self._add_client(self.client_editor.client)

    @QtCore.pyqtSlot()
    def delete_client(self) -> None:
        row = self.clients_lst.currentRow()
        client = self.current_client
        assert client is not None

        reply = QtWidgets.QMessageBox.warning(
            self,  # noqa
            f"{QtWidgets.QApplication.applicationName()} - Delete client",
            f"""
            <p>Do you really want to delete this client permanently?</p>
            <p><strong>{client.name}</strong></p>
            """,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return

        response = api.client.delete(client.id)
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot delete client %s - Reason is: %s",
                client.name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot delete client {client.name}", is_warning=True
            )
            return

        _deleted_item = self.clients_lst.takeItem(row)
        del _deleted_item

        self._forbidden_names.remove(client.name)

        if self.clients_lst.count() == 0:
            self._show_in_editor(None)
            self._enable_buttons(False)
            self.new_btn.setFocus()
        else:
            self.clients_lst.setCurrentRow(row - 1)
            self.clients_lst.setFocus()

    @QtCore.pyqtSlot()
    def toggle_client_activation(self) -> None:
        client = self.current_client
        assert client is not None
        row = self.clients_lst.currentRow()

        if client.is_active:
            reply = QtWidgets.QMessageBox.warning(
                self,  # noqa
                f"{QtWidgets.QApplication.applicationName()} - De-activate client",
                f"""
                <p>Do you really want to de-activate this client: its basket will be emptied?</p>
                <p><strong>{client.name}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                self.activate_btn.setChecked(True)
                return
            action = "de-activate"
            response = api.client.set_inactive(client.id)
        else:
            action = "activate"
            response = api.client.set_active(client.id)

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot %s client %s - Reason is: %s",
                action,
                client.name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot {action} client {client.name}", is_warning=True
            )
            return

        self.load_clients()

        if response.body.is_active or self.inactive_ckb.isChecked():
            # client is still displayed: select it
            self.clients_lst.setCurrentRow(row)
        else:
            # client is no more displayed: select the previous one if any
            self.clients_lst.setCurrentRow(max(0, row - 1))

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()

        if key == QtCore.Qt.Key.Key_Delete:
            self.delete_client()
            return

        super().keyPressEvent(event)

    def _enable_buttons(self, enable: bool) -> None:
        self.delete_btn.setEnabled(enable)
        self.edit_btn.setEnabled(enable)
        self.activate_btn.setEnabled(enable)

    def _add_item_from_client(
        self, client: schemas.Client, active_only: bool = True
    ) -> Optional[QtWidgets.QListWidgetItem]:
        self._forbidden_names.append(client.name)

        if client.is_active or not active_only:
            item = QtWidgets.QListWidgetItem(client.name)
            icon = self.active_icon if client.is_active else self.inactive_icon
            item.setIcon(icon)
            item.setData(ClientSelector.UserRoles.ClientRole, client)
            self.clients_lst.addItem(item)
            return item

    def _show_in_editor(self, client: Optional[schemas.Client]) -> None:
        self.client_editor.show_client(client)

    def _update_client(self, client: Client) -> None:
        origin_client = self.current_client
        assert origin_client is not None
        old_name = origin_client.name

        updated_client = {}
        updated_address = schemas.Address(
            origin_client.address.address,
            origin_client.address.zip_code,
            origin_client.address.city,
        )
        is_address_updated = False

        if (name := client.name) != old_name:
            updated_client["name"] = name
        if (address := client.address) != origin_client.address.address:
            updated_address.address = address
            is_address_updated = True
        if (zip_code := client.zip_code) != origin_client.address.zip_code:
            updated_address.zip_code = zip_code
            is_address_updated = True
        if (city := client.city) != origin_client.address.city:
            updated_address.city = city
            is_address_updated = True
        if is_address_updated:
            updated_client["address"] = updated_address
        if (email := client.email) != origin_client.email:
            updated_client["email"] = email

        response = api.client.update(
            origin_client.id, obj_in=schemas.ClientUpdate(**updated_client)
        )
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot update the selected client %s - Reason is: %s",
                old_name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot update the selected client {old_name}", is_warning=True
            )
            self._show_in_editor(origin_client)
            return

        QtUtil.getMainWindow().show_status_message(f"Client update success!")

        new_client = response.body

        current_item = self.clients_lst.currentItem()
        current_item.setData(ClientSelector.UserRoles.ClientRole, new_client)
        self._show_in_editor(new_client)

        if (new_name := client.name) is not None:
            current_item.setText(new_name)
            idx = self._forbidden_names.index(old_name)
            self._forbidden_names[idx] = new_name
            self.clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)

        self.clients_lst.setFocus()

    def _add_client(self, client: Client) -> None:
        new_client = {
            "name": client.name,
            "address": schemas.Address(client.address, client.zip_code, client.city),
            "email": client.email,
        }
        response = api.client.add(obj_in=schemas.ClientCreate(**new_client))

        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot create the new client %s - Reason is: %s",
                client.name,
                response.reason,
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot create the new client {client.name}", is_warning=True
            )
            self._show_in_editor(self.current_client)
            return

        QtUtil.getMainWindow().show_status_message(f"Client update success!")

        item = self._add_item_from_client(response.body)

        self.clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        row = self.clients_lst.row(item)
        self.clients_lst.setCurrentRow(row)
        self._enable_buttons(True)
        self.clients_lst.setFocus()
