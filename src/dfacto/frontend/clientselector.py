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

    client_selected = QtCore.pyqtSignal(object)

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
        self.setLayout(main_layout)

        self.clients_lst.itemSelectionChanged.connect(self.select_current_client)
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
        self.inactive_ckb.toggled.connect(self.on_inactive_selection)
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

    @property
    def has_visible_client(self) -> bool:
        clients_lst = self.clients_lst
        for row in range(clients_lst.count()):
            if not clients_lst.item(row).isHidden():
                return True
        return False

    def load_clients(self) -> None:
        clients_lst = self.clients_lst
        # Prevent emission of a client selection signal before the client list is loaded
        with QtCore.QSignalBlocker(clients_lst):
            clients_lst.clear()
        self.client_editor.clear()

        response = api.client.get_all()

        if response.status is CommandStatus.COMPLETED:
            for client in response.body:
                self._add_item_from_client(client, not self.inactive_ckb.isChecked())

            clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
            self._select_first_visible_item()

            self._enable_buttons(self.has_visible_client)
            return

        QtUtil.raise_fatal_error(
            f"Cannot load the clients list"
            f" - Reason is: {response.reason}"
        )

    @QtCore.pyqtSlot(bool)
    def on_inactive_selection(self, checked: bool):
        active_only = not checked
        clients_lst = self.clients_lst
        for row in range(clients_lst.count()):
            item = clients_lst.item(row)
            client: schemas.Client = item.data(ClientSelector.UserRoles.ClientRole)
            item.setHidden(active_only and not client.is_active)

        clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
        self._select_first_visible_item()

        self._enable_buttons(self.has_visible_client)

    @QtCore.pyqtSlot()
    def select_current_client(self) -> None:
        current_client = self.current_client
        if current_client is None:
            self.activate_btn.setChecked(False)
            self.client_selected.emit(None)
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
        client = self.current_client
        assert client is not None
        clients_lst = self.clients_lst
        row = clients_lst.currentRow()

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

        if response.status is CommandStatus.COMPLETED:
            with QtCore.QSignalBlocker(clients_lst.model()):
                _deleted_item = clients_lst.takeItem(row)
                del _deleted_item

            self._forbidden_names.remove(client.name)

            if not self.has_visible_client:
                self._show_in_editor(None)
                self._enable_buttons(False)
                self.new_btn.setFocus()
            else:
                self._select_first_visible_item(before=row - 1)
                clients_lst.setFocus()
            return

        if response.status is CommandStatus.FAILED:
            QtUtil.raise_fatal_error(
                f"Cannot delete client {client.name}"
                f" - Reason is: {response.reason}"
            )
        if response.status is CommandStatus.REJECTED:
            QtWidgets.QMessageBox.warning(
                None,  # type: ignore
                f"Dfacto - Delete client",
                f"""
                <p>Cannot delete client {client.name}</p>
                <p><strong>Reason is: {response.reason}</strong></p>
                """,
                QtWidgets.QMessageBox.StandardButton.Close,
            )

    @QtCore.pyqtSlot()
    def toggle_client_activation(self) -> None:
        client = self.current_client
        assert client is not None
        clients_lst = self.clients_lst
        row = clients_lst.currentRow()

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

        if response.status is CommandStatus.COMPLETED:
            with QtCore.QSignalBlocker(clients_lst.model()):
                _deleted_item = clients_lst.takeItem(row)
                del _deleted_item

            new_client: schemas.Client = response.body
            active_only = not self.inactive_ckb.isChecked()
            new_item = self._add_item_from_client(
                new_client, active_only
            )
            clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
            row = clients_lst.row(new_item)

            clients_lst.clearSelection()
            if new_client.is_active or not active_only:
                # client is still displayed: select it
                clients_lst.setCurrentRow(row)
            else:
                # client is no more displayed: select the previous one if any
                self._select_first_visible_item(before=row - 1)
            return

        QtUtil.raise_fatal_error(
            f"Cannot {action} client {client.name}"
            f" - Reason is: {response.reason}"
        )

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

        item = QtWidgets.QListWidgetItem(client.name)
        icon = self.active_icon if client.is_active else self.inactive_icon
        item.setIcon(icon)
        item.setData(ClientSelector.UserRoles.ClientRole, client)
        self.clients_lst.addItem(item)
        item.setHidden(active_only and not client.is_active)
        return item

    def _show_in_editor(self, client: Optional[schemas.Client]) -> None:
        self.client_editor.show_client(client)

    def _select_first_visible_item(self, before: int = -1) -> None:
        clients_lst = self.clients_lst
        if before == -1:
            start = 0
            stop = clients_lst.count()
            step = 1
        else:
            start = before
            stop = -1
            step = -1
        found = False
        for row in range(start, stop, step):
            if not clients_lst.item(row).isHidden():
                clients_lst.setCurrentRow(row)
                break
        if not found:
            self.select_current_client()

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

        if response.status is CommandStatus.COMPLETED:
            new_client = response.body

            clients_lst = self.clients_lst
            current_item = clients_lst.currentItem()
            current_item.setData(ClientSelector.UserRoles.ClientRole, new_client)
            self._show_in_editor(new_client)

            if (new_name := client.name) is not None:
                current_item.setText(new_name)
                idx = self._forbidden_names.index(old_name)
                self._forbidden_names[idx] = new_name
                clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)

            clients_lst.setFocus()
            return

        QtUtil.raise_fatal_error(
            f"Cannot update the selected client {old_name}"
            f" - Reason is: {response.reason}"
        )

    def _add_client(self, client: Client) -> None:
        new_client = {
            "name": client.name,
            "address": schemas.Address(client.address, client.zip_code, client.city),
            "email": client.email,
        }
        response = api.client.add(obj_in=schemas.ClientCreate(**new_client))

        if response.status is CommandStatus.COMPLETED:
            item = self._add_item_from_client(response.body)

            clients_lst = self.clients_lst
            clients_lst.sortItems(QtCore.Qt.SortOrder.AscendingOrder)
            row = clients_lst.row(item)
            clients_lst.setCurrentRow(row)
            self._enable_buttons(True)
            clients_lst.setFocus()
            return

        QtUtil.raise_fatal_error(
            f"Cannot create the new client {client.name}"
            f" - Reason is: {response.reason}"
        )
