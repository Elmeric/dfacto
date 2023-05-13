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
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.util import qtutil as QtUtil

logger = logging.getLogger(__name__)

Service = namedtuple("Service", ["name", "unit_price", "vat_rate_id"])


class ServiceEditor(QtWidgets.QWidget):
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

        header_lbl = QtWidgets.QLabel("SERVICE INFO")
        header_lbl.setMaximumHeight(32)

        icon_size = QtCore.QSize(32, 32)
        self.ok_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/ok.png"), "")
        self.ok_btn.setIconSize(icon_size)
        self.ok_btn.setToolTip("Confirm service edition (Alt+Enter)")
        self.ok_btn.setStatusTip("Confirm service edition (Alt+Enter)")
        self.ok_btn.setFlat(True)
        self.cancel_btn = QtWidgets.QPushButton(
            QtGui.QIcon(f"{resources}/cancel.png"), ""
        )
        self.cancel_btn.setIconSize(icon_size)
        self.cancel_btn.setToolTip("Cancel service edition (Esc)")
        self.cancel_btn.setStatusTip("Cancel service edition (Esc)")
        self.cancel_btn.setFlat(True)

        self.name_text = QtUtil.FittedLineEdit()
        self.name_text.setValidator(
            QtGui.QRegularExpressionValidator(
                QtCore.QRegularExpression("[A-Z][A-Za-z0-9_ ]*")
            )
        )
        name_tip = "Service designation, shall be a unique alphanumeric sentence starting with an uppercase letter"
        self.name_text.setToolTip(name_tip)
        self.name_text.setStatusTip(name_tip)

        self.price_spin = QtWidgets.QDoubleSpinBox()
        self.price_spin.setMaximum(10000.00)
        self.price_spin.setPrefix("€ ")
        self.price_spin.setAccelerated(True)
        self.price_spin.setGroupSeparatorShown(True)
        price_tip = "Service unit price, in euros, limited to 10 000 €"
        self.price_spin.setToolTip(price_tip)
        self.price_spin.setStatusTip(price_tip)

        self.vat_cmb = QtWidgets.QComboBox()

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
        tool_layout.addWidget(self.ok_btn)
        tool_layout.addWidget(self.cancel_btn)
        tool_layout.addStretch()

        service_layout = QtWidgets.QFormLayout()
        service_layout.setContentsMargins(5, 5, 5, 5)
        service_layout.setSpacing(5)
        service_layout.addRow("Service:", self.name_text)
        service_layout.addRow("Unit price:", self.price_spin)
        service_layout.addRow("VAT rate:", self.vat_cmb)

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
        self.price_spin.lineEdit().textEdited.connect(self.check_price)
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self._forbidden_names: list[str] = []
        self.mode = ServiceEditor.Mode.SHOW
        self._load_vat_rates()

    def _load_vat_rates(self):
        response = api.vat_rate.get_all()

        if response.status is not CommandStatus.COMPLETED:
            QtUtil.raise_fatal_error(
                f"Cannot retrieve the VAT rates"
                f" - Reason is: {response.reason}"
            )

        vat_rates: list[schemas.VatRate] = response.body

        for vat_rate in vat_rates:
            self.vat_cmb.addItem(
                f"{vat_rate.rate} % ({vat_rate.name})", userData=vat_rate.id
            )
        self.vat_cmb.model().sort(0)

    @property
    def mode(self) -> Mode:
        return self._mode

    @mode.setter
    def mode(self, mode: Mode) -> None:
        self._mode = mode

        if mode is ServiceEditor.Mode.SHOW:
            show_buttons = False
            read_only = True
        else:
            show_buttons = True
            read_only = False

        self.ok_btn.setVisible(show_buttons)
        self.cancel_btn.setVisible(show_buttons)

        self.name_text.setDisabled(read_only)
        self.price_spin.setDisabled(read_only)
        self.vat_cmb.setDisabled(read_only)

        self._enable_buttons(self.is_valid)

    @property
    def service(self):
        return Service(
            name=self.name_text.text(),
            unit_price=self.price_spin.value(),
            vat_rate_id=self.vat_cmb.currentData(),
        )

    @property
    def is_valid(self) -> bool:
        if self._mode not in (ServiceEditor.Mode.EDIT, ServiceEditor.Mode.ADD):
            return True

        name_ok = (
            self.name_text.text() != ""
            and self.name_text.text() not in self._forbidden_names
        )
        price_ok = self.price_spin.value() >= 0.0

        return name_ok and price_ok

    @QtCore.pyqtSlot(str)
    def check_name(self, _text: str) -> None:
        self._enable_buttons(self.is_valid)

    @QtCore.pyqtSlot(str)
    def check_price(self, text: str) -> None:
        if text == "":
            self.price_spin.setValue(0.0)

        self._enable_buttons(self.is_valid)

    def show_service(self, service: Optional[schemas.Service]) -> None:
        if service is None:
            self.clear()
        else:
            vat_rate = service.vat_rate

            self.name_text.setText(service.name)
            self.price_spin.setValue(service.unit_price)
            self.vat_cmb.setCurrentText(f"{vat_rate.rate} % ({vat_rate.name})")

        self.mode = ServiceEditor.Mode.SHOW

    @QtCore.pyqtSlot()
    def accept(self) -> None:
        self.finished.emit(QtWidgets.QDialog.DialogCode.Accepted)

    @QtCore.pyqtSlot()
    def reject(self) -> None:
        self.finished.emit(QtWidgets.QDialog.DialogCode.Rejected)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        alt = event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier

        if self._mode in (ServiceEditor.Mode.ADD, ServiceEditor.Mode.EDIT):
            if key == QtCore.Qt.Key.Key_Escape:
                self.reject()
                return
            if alt and key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return) and self.is_valid:
                self.accept()
                return

        super().keyPressEvent(event)

    def edit_service(self, forbidden_names: list[str]) -> None:
        self._forbidden_names = forbidden_names

        self.mode = ServiceEditor.Mode.EDIT

        self.name_text.setFocus()

    def add_service(self, forbidden_names: list[str]) -> None:
        self._forbidden_names = forbidden_names

        self.clear()

        self.mode = ServiceEditor.Mode.ADD

        self.name_text.setFocus()

    def clear(self) -> None:
        self.name_text.clear()
        self.price_spin.clear()
        self.price_spin.setValue(0.0)
        self.vat_cmb.setCurrentIndex(0)

    def _enable_buttons(self, is_valid: bool):
        self.ok_btn.setEnabled(is_valid)
