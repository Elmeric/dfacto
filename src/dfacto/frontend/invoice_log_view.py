# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import datetime
from typing import TYPE_CHECKING, Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend.models import InvoiceStatus
from dfacto.backend.util import DatetimeRange

if TYPE_CHECKING:
    from dfacto.backend.schemas import Invoice


class StatusLogEditor(QtWidgets.QDialog):
    def __init__(
        self,
        invoice: "Invoice",
        fixed_size: bool = True,
        parent=None,
    ) -> None:
        self._invoice = invoice
        self._status_log = invoice.status_log
        super().__init__(parent=parent)

        # Prevent resizing the view when required.
        if fixed_size:
            self.setWindowFlags(
                QtCore.Qt.WindowType.Dialog
                | QtCore.Qt.WindowType.MSWindowsFixedSizeDialogHint
            )

        resources = Config.dfacto_settings.resources

        intro_widget = QtWidgets.QWidget()
        self.intro_pix = QtWidgets.QLabel()
        self.intro_pix.setPixmap(
            QtGui.QPixmap(f"{resources}/invoice-128.png").scaledToHeight(
                96, QtCore.Qt.TransformationMode.SmoothTransformation
            )
        )
        self.intro_lbl = QtWidgets.QLabel()
        self.intro_lbl.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.intro_lbl.setFixedWidth(400)
        self.intro_lbl.setWordWrap(True)
        self.intro_lbl.setText(
            f"""
            <p><strong>History of invoice {invoice.code}</strong</p>
            <p><small>(Each date can be edited to fix datation errors)</small></p>
            """
        )
        intro_layout = QtWidgets.QHBoxLayout()
        intro_layout.setContentsMargins(0, 0, 0, 0)
        intro_layout.addWidget(self.intro_pix, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(self.intro_lbl, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addStretch()
        intro_widget.setLayout(intro_layout)

        log_layout = QtWidgets.QFormLayout()
        log_layout.setContentsMargins(10, 0, 0, 0)
        log_layout.setFormAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop
        )
        log_layout.setHorizontalSpacing(10)
        log_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        self._date_editors: dict[InvoiceStatus, QtWidgets.QDateEdit] = dict()
        labels = {
            InvoiceStatus.DRAFT: "Created on",
            InvoiceStatus.EMITTED: "Issued on",
            InvoiceStatus.REMINDED: "Reminded on",
            InvoiceStatus.PAID: "Paid on",
            InvoiceStatus.CANCELLED: "Cancelled on",
        }
        self._previous_status: dict[InvoiceStatus, Optional[InvoiceStatus]] = {}
        prev_status = None
        for status, log in invoice.status_log.items():
            date_edit = QtWidgets.QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(log.from_.date())
            self._date_editors[status] = date_edit
            self._previous_status[status] = prev_status
            prev_status = status
            if status in (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED):
                date_edit.setEnabled(False)
            date_edit.dateChanged.connect(self.check_date)
            log_layout.addRow(f"<strong>{labels[status]}:</strong>", date_edit)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            QtCore.Qt.Orientation.Horizontal,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(intro_widget)
        main_layout.addSpacing(20)
        main_layout.addLayout(log_layout)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.button_box)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self._enable_buttons(self.is_valid)

    @property
    def status_log(self) -> dict[InvoiceStatus, DatetimeRange]:
        log: dict[InvoiceStatus, DatetimeRange] = {}
        for status, editor in self._date_editors.items():
            from_ = self._status_log[status].from_.date()
            new_date = editor.date().toPyDate()
            if new_date != from_:
                from_ = new_date
            log[status] = DatetimeRange(from_=from_, to=self._status_log[status].to)
            previous_status = self._previous_status[status]
            if previous_status is not None:
                log[previous_status].to = new_date
        return log

    @property
    def is_valid(self) -> bool:
        ok_date = True
        a_date_changed = False
        for status, editor in self._date_editors.items():
            date_= self._date_editors[status].date()
            old_date = self._status_log[status].from_.date()
            prev_status = self._previous_status[status]
            if date_.toPyDate() != old_date:
                a_date_changed = True
            if prev_status is not None:
                prev_date = self._date_editors[prev_status].date()
                ok_date = ok_date and date_ >= prev_date
            if not ok_date:
                break
        if a_date_changed:
            return ok_date
        return False

    @QtCore.pyqtSlot(QtCore.QDate)
    def check_date(self, _date: QtCore.QDate) -> None:
        self._enable_buttons(self.is_valid)

    def _enable_buttons(self, is_valid: bool):
        self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        ).setEnabled(is_valid)
