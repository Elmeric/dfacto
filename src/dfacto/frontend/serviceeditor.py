# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from copy import copy
from enum import Enum, auto
from typing import Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
from dfacto.util import qtutil as QtUtil

from dfacto import settings as Config
from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus

logger = logging.getLogger(__name__)


class ServiceEditor(QtWidgets.QWidget):
    class Mode(Enum):
        SHOW = auto()
        EDIT = auto()
        ADD = auto()

    service_added = QtCore.pyqtSignal(str, int)
    service_updated = QtCore.pyqtSignal(str, str)
    edition_cancelled = QtCore.pyqtSignal()

    def __init__(self, mode: Mode = Mode.SHOW, parent=None):
        self.mode = mode
        super().__init__(parent=parent)

        self._service_id: Optional[int] = None

        resources = Config.dfacto_settings.resources

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Maximum
        )

        icon_size = QtCore.QSize(32, 32)
        self.ok_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/ok.png"), "")
        self.ok_btn.setIconSize(icon_size)
        self.ok_btn.setFlat(True)
        self.cancel_btn = QtWidgets.QPushButton(QtGui.QIcon(f"{resources}/cancel.png"), "")
        self.cancel_btn.setIconSize(icon_size)
        self.cancel_btn.setFlat(True)
        tool_layout = QtWidgets.QHBoxLayout()
        tool_layout.setSpacing(0)
        tool_layout.setContentsMargins(0, 0, 0, 0)
        tool_layout.addWidget(self.ok_btn)
        tool_layout.addWidget(self.cancel_btn)
        tool_layout.addStretch()

        self.name_text = QtUtil.FittedLineEdit()
        self.name_text.setValidator(
            QtGui.QRegularExpressionValidator(
                QtCore.QRegularExpression("[A-Z][A-Za-z0-9_ ]*")
            )
        )
        self.name_text.textEdited.connect(self.check_name)

        self.price_spin = QtWidgets.QDoubleSpinBox()
        self.price_spin.setMaximum(10000.00)
        self.price_spin.setAccelerated(True)
        self.price_spin.setGroupSeparatorShown(True)
        self.price_spin.lineEdit().textEdited.connect(self.check_price)

        self.vat_cmb = QtWidgets.QComboBox()
        response = api.vat_rate.get_all()
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot retrive the VAT rates - Reason is: %s",
                response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot retrive the VAT rates: try to restart Dfacto.\n"
                f"If the problem persists, contact your admin",
                is_warning=True
            )
            return
        vat_rates: list[schemas.VatRate] = response.body
        for vat_rate in vat_rates:
            self.vat_cmb.addItem(f"{vat_rate.rate} ({vat_rate.name})", userData=vat_rate.id)
        self.vat_cmb.model().sort(0)

        service_layout = QtWidgets.QFormLayout()
        service_layout.addRow("Service:", self.name_text)
        service_layout.addRow("Unit price:", self.price_spin)
        service_layout.addRow("VAT rate:", self.vat_cmb)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(5, 0, 0, 5)
        main_layout.addLayout(tool_layout)
        main_layout.addLayout(service_layout)
        self.setLayout(main_layout)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        self.origin_service = None
        self.forbidden_names = []
        self.set_mode(mode)

    @property
    def is_valid(self) -> bool:
        # name_ok = self.name_text.text() not in self.forbidden_names
        name_ok = self.name_text.text() != "" and self.name_text.text() not in self.forbidden_names
        price_ok = self.price_spin.value() >= 0.0
        if self.mode in (ServiceEditor.Mode.EDIT, ServiceEditor.Mode.ADD):
            return name_ok and price_ok
        return True

    @QtCore.pyqtSlot(str)
    def check_name(self, _text: str) -> None:
        self._enable_buttons(self.is_valid)

    @QtCore.pyqtSlot(str)
    def check_price(self, text: str) -> None:
        if text == "":
            self.price_spin.setValue(0.0)
        self._enable_buttons(self.is_valid)

    @QtCore.pyqtSlot(bool)
    def set_mode(self, mode: Mode) -> None:
        self.mode = mode
        if mode is ServiceEditor.Mode.SHOW:
            show_buttons = False
            read_only = True
        else:
            show_buttons = True
            read_only = False
        self.ok_btn.setVisible(show_buttons)
        self.cancel_btn.setVisible(show_buttons)
        self.name_text.setReadOnly(read_only)
        self.price_spin.setReadOnly(read_only)
        self.vat_cmb.setDisabled(read_only)
        self._enable_buttons(self.is_valid)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        # ctrl = event.modifiers() & QtCore.Qt.ControlModifier  # noqa
        # shift = event.modifiers() & QtCore.Qt.ShiftModifier  # noqa
        alt = event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier

        if self.mode in (ServiceEditor.Mode.ADD, ServiceEditor.Mode.EDIT):
            if key == QtCore.Qt.Key.Key_Escape:
                self.reject()
                return
            if alt and key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return):
                self.accept()
                return

        super().keyPressEvent(event)

    @QtCore.pyqtSlot(int)
    def show_service(self, service_id: int) -> None:
        response = api.service.get(service_id)
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot load the selected service %s - Reason is: %s",
                service_id, response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot load the selected service {service_id}",
                is_warning=True
            )
            return

        self._service_id = service_id
        service: schemas.Service = response.body
        self.origin_service = service
        self.name_text.setText(service.name)
        self.price_spin.setValue(service.unit_price)
        vat_rate = service.vat_rate
        self.vat_cmb.setCurrentText(f"{vat_rate.rate} ({vat_rate.name})")
        self.set_mode(ServiceEditor.Mode.SHOW)

    @QtCore.pyqtSlot(list)
    def edit_service(self, forbidden_names: list[str]) -> None:
        self.forbidden_names = copy(forbidden_names)
        self.forbidden_names.remove(self.origin_service.name)
        self.set_mode(ServiceEditor.Mode.EDIT)
        self.name_text.setFocus()

    @QtCore.pyqtSlot(list)
    def add_service(self, forbidden_names: list[str]) -> None:
        self.forbidden_names = copy(forbidden_names)
        self.name_text.clear()
        self.price_spin.clear()
        self.price_spin.setValue(0.0)
        self.vat_cmb.setCurrentIndex(0)
        self.set_mode(ServiceEditor.Mode.ADD)
        self.name_text.setFocus()

    @QtCore.pyqtSlot()
    def accept(self) -> None:
        if self.mode is ServiceEditor.Mode.EDIT:
            self._update_service()
        elif self.mode is ServiceEditor.Mode.ADD:
            self._create_service()

    @QtCore.pyqtSlot()
    def reject(self) -> None:
        self.show_service(self._service_id)
        self.edition_cancelled.emit()

    def _update_service(self):
        updated_service = {}

        for field, widget, attr in (
            ("name", self.name_text, "text"),
            ("unit_price", self.price_spin, "value"),
        ):
            if (value := getattr(widget, attr)()) != getattr(self.origin_service, field):
                updated_service[field] = value
        if (value := self.vat_cmb.currentData()) != self.origin_service.vat_rate.id:
            updated_service["vat_rate_id"] = value

        response = api.service.update(
            self._service_id,
            obj_in=schemas.ServiceUpdate(**updated_service)
        )
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot update the selected service %s - Reason is: %s",
                self.origin_service.name, response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot update the selected service {self.origin_service.name}",
                is_warning=True
            )
            self.reject()
            return

        QtUtil.getMainWindow().show_status_message(f"Service update success!")
        old_name = self.origin_service.name
        self.show_service(self._service_id)
        if (new_name := self.name_text.text()) != old_name:
            self.service_updated.emit(old_name, new_name)

    def _create_service(self):
        response = api.service.add(
            obj_in=schemas.ServiceCreate(
                name=self.name_text.text(),
                unit_price=self.price_spin.value(),
                vat_rate_id=self.vat_cmb.currentData()
            )
        )
        if response.status is not CommandStatus.COMPLETED:
            logger.warning(
                "Cannot create the new service %s - Reason is: %s",
                self.name_text.text(), response.reason
            )
            QtUtil.getMainWindow().show_status_message(
                f"Cannot create the new service {self.name_text.text()}",
                is_warning=True
            )
            self.reject()
            return

        QtUtil.getMainWindow().show_status_message(f"Service update success!")
        service: schemas.Service = response.body
        self.show_service(service.id)
        self.service_added.emit(service.name, service.id)

    def _enable_buttons(self, is_valid: bool):
        self.ok_btn.setEnabled(is_valid)
