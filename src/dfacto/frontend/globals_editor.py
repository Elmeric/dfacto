# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from decimal import Decimal
from typing import Union

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import schemas


class GlobalsEditor(QtWidgets.QDialog):
    def __init__(
        self,
        globals_: schemas.Globals,
        fixed_size: bool = True,
        parent=None,
    ) -> None:
        self._globals = globals_
        super().__init__(parent=parent)

        # Prevent resizing the view when required.
        if fixed_size:
            self.setWindowFlags(
                QtCore.Qt.WindowType.Dialog
                | QtCore.Qt.WindowType.MSWindowsFixedSizeDialogHint
            )

        resources = Config.dfacto_settings.resources
        locale = QtCore.QLocale(Config.dfacto_settings.locale)

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
        lbl = _("General invoices information")
        self.intro_lbl.setText(f"""<p><strong>{lbl}</strong</p>""")
        intro_layout = QtWidgets.QHBoxLayout()
        intro_layout.setContentsMargins(0, 0, 0, 0)
        intro_layout.addWidget(self.intro_pix, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(self.intro_lbl, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addStretch()
        intro_widget.setLayout(intro_layout)

        self.due_spn = QtWidgets.QSpinBox()
        self.due_spn.setLocale(locale)
        self.due_spn.setRange(0, 180)
        self.due_spn.setSingleStep(30)
        self.due_spn.setMaximumWidth(100)
        self.due_spn.setSuffix(_(" days"))
        tip = _("Delta from invoice issue date, in days")
        self.due_spn.setToolTip(tip)
        self.due_spn.setStatusTip(tip)

        self.penalty_spn = QtWidgets.QDoubleSpinBox()
        self.penalty_spn.setLocale(locale)
        self.penalty_spn.setMaximum(100.00)
        self.penalty_spn.setSuffix("%")
        self.penalty_spn.setAccelerated(True)
        tip = _("Late payment penalty (annual rate)")
        self.penalty_spn.setToolTip(tip)
        self.penalty_spn.setStatusTip(tip)

        self.discount_spn = QtWidgets.QDoubleSpinBox()
        self.discount_spn.setLocale(locale)
        self.discount_spn.setMaximum(100.00)
        self.discount_spn.setSuffix("%")
        self.discount_spn.setAccelerated(True)
        tip = _("Discount for early payment")
        self.discount_spn.setToolTip(tip)
        self.discount_spn.setStatusTip(tip)

        self.reset_btn = QtWidgets.QPushButton(_("Reset"))

        glob_layout = QtWidgets.QFormLayout()
        glob_layout.setContentsMargins(10, 0, 0, 0)
        glob_layout.setFormAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop
        )
        glob_layout.setHorizontalSpacing(10)
        glob_layout.setFieldGrowthPolicy(
            QtWidgets.QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        lbl1 = _("Due date delta:")
        lbl2 = _("Penalty:")
        lbl3 = _("Discount:")
        glob_layout.addRow(f"<strong>{lbl1}</strong>", self.due_spn)
        glob_layout.addRow(f"<strong>{lbl2}</strong>", self.penalty_spn)
        glob_layout.addRow(f"<strong>{lbl3}</strong>", self.discount_spn)
        glob_layout.addRow("", self.reset_btn)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            QtCore.Qt.Orientation.Horizontal,
            self,
        )
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText(
            _("OK")
        )
        self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        ).setText(_("Cancel"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(intro_widget)
        main_layout.addSpacing(20)
        main_layout.addLayout(glob_layout)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.button_box)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self.due_spn.valueChanged.connect(lambda value: self.check_spn_value(value))
        self.due_spn.lineEdit().textEdited.connect(
            lambda text, spn=self.due_spn: self.check_spn_text(spn, text)
        )
        self.penalty_spn.valueChanged.connect(lambda value: self.check_spn_value(value))
        self.penalty_spn.lineEdit().textEdited.connect(
            lambda text, spn=self.penalty_spn: self.check_spn_text(spn, text)
        )
        self.discount_spn.valueChanged.connect(
            lambda value: self.check_spn_value(value)
        )
        self.discount_spn.lineEdit().textEdited.connect(
            lambda text, spn=self.discount_spn: self.check_spn_text(spn, text)
        )
        self.reset_btn.clicked.connect(self.reset)

        self.reset()

    @property
    def globals(self) -> schemas.GlobalsCreate:
        globals_ = schemas.GlobalsCreate(
            due_delta=self.due_spn.value(),
            penalty_rate=Decimal(str(self.penalty_spn.value())),
            discount_rate=Decimal(str(self.discount_spn.value())),
        )
        return globals_

    @property
    def has_changed(self) -> bool:
        due_delta = self.due_spn.value()
        penalty = Decimal(str(self.penalty_spn.value()))
        discount = Decimal(str(self.discount_spn.value()))

        has_changed = (
            due_delta != self._globals.due_delta
            or penalty != self._globals.penalty_rate
            or discount != self._globals.discount_rate
        )
        return has_changed

    @property
    def is_valid(self) -> bool:
        due_delta = self.due_spn.value()
        penalty = Decimal(str(self.penalty_spn.value()))
        discount = Decimal(str(self.discount_spn.value()))

        return due_delta >= 0 and penalty >= 0.0 and discount >= 0.0

    def check_spn_text(self, spn: QtWidgets.QSpinBox, text: str) -> None:
        if text == spn.suffix():
            spn.setValue(0)

        self._enable_buttons(self.has_changed, self.is_valid)

    def check_spn_value(self, _value: Union[int, float]) -> None:
        self._enable_buttons(self.has_changed, self.is_valid)

    @QtCore.pyqtSlot()
    def reset(self) -> None:
        globals_ = self._globals
        with QtCore.QSignalBlocker(self.due_spn):
            self.due_spn.setValue(globals_.due_delta)
        with QtCore.QSignalBlocker(self.penalty_spn):
            self.penalty_spn.setValue(float(globals_.penalty_rate))
        with QtCore.QSignalBlocker(self.discount_spn):
            self.discount_spn.setValue(float(globals_.discount_rate))
        self._enable_buttons(self.has_changed, self.is_valid)

    def _enable_buttons(self, has_changed: bool, is_valid: bool) -> None:
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(
            has_changed and is_valid
        )
        self.reset_btn.setEnabled(has_changed)
