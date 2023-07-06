# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from collections import namedtuple
from enum import Enum, auto
from typing import Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import schemas
from dfacto.util import qtutil as QtUtil

logger = logging.getLogger(__name__)

Client = namedtuple("Client", ["name", "address", "zip_code", "city", "email"])


class ClientEditor(QtWidgets.QWidget):
    class Mode(Enum):
        SHOW = auto()
        EDIT = auto()
        ADD = auto()

    finished = QtCore.pyqtSignal(QtWidgets.QDialog.DialogCode)

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)

        resources = Config.dfacto_settings.resources

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum
        )

        header_lbl = QtWidgets.QLabel(_("CLIENT INFO"))
        header_lbl.setMaximumHeight(32)
        self.active_pix = QtWidgets.QLabel()
        self.active_pix.setPixmap(
            QtGui.QPixmap(f"{resources}/client-active.png").scaledToHeight(
                24, QtCore.Qt.TransformationMode.SmoothTransformation
            )
        )
        self.inactive_pix = QtWidgets.QLabel()
        self.inactive_pix.setPixmap(
            QtGui.QPixmap(f"{resources}/client-inactive.png").scaledToHeight(
                24, QtCore.Qt.TransformationMode.SmoothTransformation
            )
        )

        icon_size = QtCore.QSize(32, 32)
        self.ok_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/ok.png"), "")
        self.ok_btn.setIconSize(icon_size)
        tip = _("Confirm client edition (Alt+Enter)")
        self.ok_btn.setToolTip(tip)
        self.ok_btn.setStatusTip(tip)
        self.ok_btn.setFlat(True)
        self.cancel_btn = QtWidgets.QPushButton(
            QtGui.QIcon(f"{resources}/cancel.png"), ""
        )
        self.cancel_btn.setIconSize(icon_size)
        tip = _("Cancel client edition (Esc)")
        self.cancel_btn.setToolTip(tip)
        self.cancel_btn.setStatusTip(tip)
        self.cancel_btn.setFlat(True)

        self.name_text = QtUtil.FittedLineEdit()
        self.name_text.setValidator(
            QtGui.QRegularExpressionValidator(
                QtCore.QRegularExpression("[A-Z][A-Za-z0-9_ ]*")
            )
        )
        name_tip = _(
            "Client name, shall be a unique alphanumeric sentence "
            "starting with an uppercase letter"
        )
        self.name_text.setToolTip(name_tip)
        self.name_text.setStatusTip(name_tip)

        self.address_text = QtUtil.FittedLineEdit()
        address_tip = _("Client address: building num, street")
        self.address_text.setToolTip(address_tip)
        self.address_text.setStatusTip(address_tip)

        self.zipcode_text = QtUtil.FittedLineEdit()
        zipcode_tip = _("Client address: zip code (five digit)")
        self.zipcode_text.setToolTip(zipcode_tip)
        self.zipcode_text.setStatusTip(zipcode_tip)
        self.zipcode_text.setValidator(
            QtGui.QRegularExpressionValidator(QtCore.QRegularExpression(r"[0-9_]{5}"))
        )
        self.zipcode_text.setCursorPosition(0)

        self.city_text = QtUtil.FittedLineEdit()
        city_tip = _("Client address: city")
        self.city_text.setToolTip(city_tip)
        self.city_text.setStatusTip(city_tip)

        self.email_text = QtUtil.FittedLineEdit()
        email_tip = _("Client email")
        self.email_text.setToolTip(email_tip)
        self.email_text.setStatusTip(email_tip)

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
        header_layout.setContentsMargins(5, 5, 10, 5)
        header_layout.setSpacing(5)
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.active_pix)
        header_layout.addWidget(self.inactive_pix)
        header.setLayout(header_layout)

        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.setSpacing(0)
        tool_layout.addWidget(self.ok_btn)
        tool_layout.addWidget(self.cancel_btn)
        tool_layout.addStretch()

        service_layout = QtWidgets.QFormLayout()
        service_layout.setContentsMargins(5, 5, 5, 5)
        service_layout.setSpacing(5)
        service_layout.addRow(_("Client:"), self.name_text)
        service_layout.addRow(_("Address:"), self.address_text)
        service_layout.addRow(_("Zip code:"), self.zipcode_text)
        service_layout.addRow(_("City:"), self.city_text)
        service_layout.addRow(_("Email:"), self.email_text)

        editor_widget = QtWidgets.QWidget()
        editor_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum
        )
        editor_layout = QtWidgets.QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        editor_layout.addLayout(tool_layout)
        editor_layout.addLayout(service_layout)
        editor_widget.setLayout(editor_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(header)
        main_layout.addWidget(editor_widget)
        self.setLayout(main_layout)

        self.name_text.textEdited.connect(self.check_name)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self._forbidden_names: list[str] = []
        self.mode = ClientEditor.Mode.SHOW

    @property
    def mode(self) -> Mode:
        return self._mode

    @mode.setter
    def mode(self, mode: Mode) -> None:
        self._mode = mode

        if mode is ClientEditor.Mode.SHOW:
            show_buttons = False
            read_only = True
        else:
            show_buttons = True
            read_only = False

        self.ok_btn.setVisible(show_buttons)
        self.cancel_btn.setVisible(show_buttons)

        self.name_text.setDisabled(read_only)
        self.address_text.setDisabled(read_only)
        self.zipcode_text.setDisabled(read_only)
        self.city_text.setDisabled(read_only)
        self.email_text.setDisabled(read_only)

        self._enable_buttons(self.is_valid)

    @property
    def client(self):
        return Client(
            name=self.name_text.text(),
            address=self.address_text.text(),
            zip_code=self.zipcode_text.text(),
            city=self.city_text.text(),
            email=self.email_text.text(),
        )

    @property
    def is_valid(self) -> bool:
        if self._mode not in (ClientEditor.Mode.EDIT, ClientEditor.Mode.ADD):
            return True

        name_ok = (
            self.name_text.text() != ""
            and self.name_text.text() not in self._forbidden_names
        )

        return name_ok

    @QtCore.pyqtSlot(str)
    def check_name(self, _text: str) -> None:
        self._enable_buttons(self.is_valid)

    def show_client(self, client: Optional[schemas.Client]) -> None:
        if client is None:
            self.clear()
        else:
            self.name_text.setText(client.name)
            self.address_text.setText(client.address.address)
            self.zipcode_text.setText(client.address.zip_code)
            self.city_text.setText(client.address.city)
            self.email_text.setText(client.email)
            self.active_pix.setVisible(client.is_active)
            self.inactive_pix.setVisible(not client.is_active)

        self.mode = ClientEditor.Mode.SHOW

    @QtCore.pyqtSlot()
    def accept(self) -> None:
        self.finished.emit(QtWidgets.QDialog.DialogCode.Accepted)

    @QtCore.pyqtSlot()
    def reject(self) -> None:
        self.finished.emit(QtWidgets.QDialog.DialogCode.Rejected)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        alt = event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier

        if self._mode in (ClientEditor.Mode.ADD, ClientEditor.Mode.EDIT):
            if key == QtCore.Qt.Key.Key_Escape:
                self.reject()
                return
            if (
                alt
                and key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return)
                and self.is_valid
            ):
                self.accept()
                return

        super().keyPressEvent(event)

    def edit_client(self, forbidden_names: list[str]) -> None:
        self._forbidden_names = forbidden_names

        self.mode = ClientEditor.Mode.EDIT

        self.name_text.setFocus()

    def add_client(self, forbidden_names: list[str]) -> None:
        self._forbidden_names = forbidden_names

        self.clear()

        self.mode = ClientEditor.Mode.ADD

        self.name_text.setFocus()

    def clear(self) -> None:
        self.name_text.clear()
        self.address_text.clear()
        self.zipcode_text.clear()
        self.city_text.clear()
        self.email_text.clear()
        self.active_pix.hide()
        self.inactive_pix.hide()

    def _enable_buttons(self, is_valid: bool):
        self.ok_btn.setEnabled(is_valid)
