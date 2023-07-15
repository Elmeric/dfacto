# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from enum import Enum, auto
from pathlib import Path
from typing import Iterable, Optional

import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.backend import schemas
from dfacto.util import qtutil as QtUtil


class AddCompanyDialog(QtWidgets.QDialog):
    class Mode(Enum):
        NEW = auto()
        ADD = auto()
        EDIT = auto()

    def __init__(
        self,
        forbidden_names: Iterable[str] = None,
        mode: Mode = Mode.ADD,
        fixed_size: bool = True,
        parent=None,
    ) -> None:
        self.mode = mode
        self.forbidden_names = forbidden_names or []
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
        intro_layout = QtWidgets.QHBoxLayout()
        intro_layout.setContentsMargins(0, 0, 0, 0)
        intro_layout.addWidget(self.intro_pix, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(self.intro_lbl, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addStretch()
        intro_widget.setLayout(intro_layout)

        name_lbl = QtWidgets.QLabel(_("Name:"))
        self.name_text = QtUtil.FittedLineEdit()
        self.name_text.setPlaceholderText(_("Company name"))
        self.name_text.setValidator(
            QtGui.QRegularExpressionValidator(
                QtCore.QRegularExpression("[A-Z][A-Za-z0-9_ ]*")
            )
        )
        self.name_text.textEdited.connect(self.check_name)
        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(name_lbl)
        name_layout.addWidget(self.name_text)

        select_icon = QtGui.QIcon(
            f"{Config.dfacto_settings.resources}/browse-folder.png"
        )
        self.home_dir_selector = QtUtil.DirectorySelector(
            label=_("Dfacto data location:"),
            placeHolder=_("Absolute path to your Dfacto data"),
            selectIcon=select_icon,
            tip=_("Select where to store your company's Dfacto data"),
            directoryGetter=lambda: str(Config.dfacto_settings.default_company_folder),
            parent=self,
        )
        self.home_dir_selector.pathSelected.connect(self.check_home)

        self.vat_ckb = QtWidgets.QCheckBox(_("No VAT obligation"))

        self.extension_widget = QtWidgets.QWidget()

        self.address_text = QtUtil.FittedLineEdit()
        self.address_text.setPlaceholderText(_("Company address"))
        self.zipcode_text = QtUtil.FittedLineEdit()
        self.zipcode_text.setPlaceholderText(_("Company zip code"))
        self.zipcode_text.setInputMask("99999;_")
        self.zipcode_text.setValidator(
            QtGui.QRegularExpressionValidator(QtCore.QRegularExpression(r"[0-9_]{5}"))
        )
        self.zipcode_text.setCursorPosition(0)
        self.city_text = QtUtil.FittedLineEdit()
        self.city_text.setPlaceholderText(_("Company city"))
        self.phone_text = QtUtil.FittedLineEdit()
        self.phone_text.setPlaceholderText(_("Company phone number"))
        self.phone_text.setInputMask("+33 9 99 99 99 99;_")
        self.email_text = QtUtil.FittedLineEdit()
        self.email_text.setPlaceholderText(_("Company email"))
        self.siret_text = QtUtil.FittedLineEdit()
        self.siret_text.setPlaceholderText(_("Company siret"))
        self.rcs_text = QtUtil.FittedLineEdit()
        self.rcs_text.setPlaceholderText(_("Company RCS"))
        locale = QtCore.QLocale(Config.dfacto_settings.locale)
        self.penalty_spin = QtWidgets.QDoubleSpinBox()
        self.penalty_spin.setLocale(locale)
        self.penalty_spin.setMaximum(100.00)
        self.penalty_spin.setSuffix("%")
        self.penalty_spin.setAccelerated(True)
        tip = _("Late payment penalty (annual rate)")
        self.penalty_spin.setToolTip(tip)
        self.penalty_spin.setStatusTip(tip)
        self.discount_spin = QtWidgets.QDoubleSpinBox()
        self.discount_spin.setLocale(locale)
        self.discount_spin.setMaximum(100.00)
        self.discount_spin.setSuffix("%")
        self.discount_spin.setAccelerated(True)
        tip = _("Discount for early payment")
        self.discount_spin.setToolTip(tip)
        self.discount_spin.setStatusTip(tip)

        extension_layout = QtWidgets.QFormLayout()
        extension_layout.setContentsMargins(10, 0, 0, 0)
        extension_layout.addRow(_("Address:"), self.address_text)
        extension_layout.addRow(_("Zip code:"), self.zipcode_text)
        extension_layout.addRow(_("City:"), self.city_text)
        extension_layout.addRow(_("Phone:"), self.phone_text)
        extension_layout.addRow(_("Email:"), self.email_text)
        extension_layout.addRow(_("Siret:"), self.siret_text)
        extension_layout.addRow(_("RCS:"), self.rcs_text)
        extension_layout.addRow(_("Penalty:"), self.penalty_spin)
        extension_layout.addRow(_("Discount:"), self.discount_spin)
        self.extension_widget.setLayout(extension_layout)

        self.details_btn = QtWidgets.QPushButton(_("Details..."))
        self.details_btn.setCheckable(True)
        self.details_btn.toggled.connect(self.toggle_details)
        self.details_lbl = QtWidgets.QLabel()
        self.details_lbl.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.details_lbl.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
        )
        details_layout = QtWidgets.QHBoxLayout()
        details_layout.addWidget(self.details_btn)
        details_layout.addWidget(self.details_lbl)
        details_layout.addStretch()

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
        main_layout.addLayout(name_layout)
        main_layout.addWidget(self.home_dir_selector)
        main_layout.addWidget(self.vat_ckb)
        main_layout.addSpacing(20)
        main_layout.addLayout(details_layout)
        main_layout.addWidget(self.extension_widget)
        main_layout.addWidget(self.button_box)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self.set_mode(mode)
        self.vat_ckb.setChecked(True)
        self.penalty_spin.setValue(12.0)
        self.discount_spin.setValue(1.5)
        self.extension_widget.hide()
        self._enable_buttons(self.is_valid)
        self.name_text.setFocus()

    @property
    def company(self) -> schemas.CompanyCreate:
        return schemas.CompanyCreate(
            name=self.name_text.text(),
            home=Path(self.home_dir_selector.text()) / self.name_text.text(),
            address=schemas.Address(
                address=self.address_text.text(),
                zip_code=self.zipcode_text.text(),
                city=self.city_text.text(),
            ),
            phone_number=self.phone_text.text(),
            email=self.email_text.text(),
            siret=self.siret_text.text(),
            rcs=self.rcs_text.text(),
            no_vat=self.vat_ckb.isChecked(),
            penalty_rate=str(self.penalty_spin.value()),
            discount_rate=str(self.discount_spin.value()),
        )

    @property
    def updated_company(self) -> schemas.CompanyUpdate:
        updated_profile = {}

        for field, widget in (
            ("address", self.address_text),
            ("zip_code", self.zipcode_text),
            ("city", self.city_text),
        ):
            origin_address = self.origin_profile.address
            if widget.text() != getattr(origin_address, field):
                updated_address = schemas.Address(
                    address=self.address_text.text(),
                    zip_code=self.zipcode_text.text(),
                    city=self.city_text.text(),
                )
                updated_profile["address"] = updated_address
                break

        for field, widget in (
            ("name", self.name_text),
            ("phone_number", self.phone_text),
            ("email", self.email_text),
            ("siret", self.siret_text),
            ("rcs", self.rcs_text),
        ):
            if (text := widget.text()) != getattr(self.origin_profile, field):
                updated_profile[field] = text

        no_vat = self.vat_ckb.isChecked()
        if no_vat != self.origin_profile.no_vat:
            updated_profile["no_vat"] = no_vat

        penalty = str(self.penalty_spin.value())
        if penalty != self.origin_profile.penalty_rate:
            updated_profile["penalty_rate"] = penalty
        discount = str(self.discount_spin.value())
        if discount != self.origin_profile.discount_rate:
            updated_profile["discount_rate"] = discount

        return schemas.CompanyUpdate(**updated_profile)

    @property
    def is_valid(self) -> bool:
        name_ok = self.name_text.text() not in self.forbidden_names
        if self.mode in (AddCompanyDialog.Mode.NEW, AddCompanyDialog.Mode.ADD):
            return (
                self.name_text.text() != ""
                and name_ok
                and self.home_dir_selector.text() != ""
            )
        if self.mode is AddCompanyDialog.Mode.EDIT:
            return self.name_text.text() != "" and name_ok

    @QtCore.pyqtSlot(str)
    def check_name(self, _text: str) -> None:
        self._enable_buttons(self.is_valid)

    @QtCore.pyqtSlot(str)
    def check_home(self, path: str) -> None:
        self.home_dir_selector.setText(path)
        self._enable_buttons(self.is_valid)

    def reset(self) -> None:
        self.name_text.clear()
        self.name_text.updateGeometry()
        self.home_dir_selector.clear()
        self.home_dir_selector.setEnabled(True)
        self.address_text.clear()
        self.zipcode_text.clear()
        self.city_text.clear()
        self.phone_text.clear()
        self.email_text.clear()
        self.siret_text.clear()
        self.rcs_text.clear()
        self.vat_ckb.setChecked(False)
        self.penalty_spin.setValue(12.0)
        self.discount_spin.setValue(1.5)
        self.set_mode(AddCompanyDialog.Mode.ADD)
        self._enable_buttons(self.is_valid)

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode
        app_name = "<strong>Dfacto</strong>"
        intro2 = _("Before starting, we need some information about you...")
        details = _(
            "Detailed information is not mandatory, you can edit your company profile later on."
        )
        if mode is AddCompanyDialog.Mode.NEW:
            intro1 = _("Welcome to %s, your invoicing companion!") % app_name
            self.intro_lbl.setText(
                f"""
                <p>{intro1}</p>
                <p>{intro2}</p>
                """
            )
            self.vat_ckb.setEnabled(True)
            self.details_lbl.setText(f"<p><small>({details})</small></p>")
            self.setWindowTitle(_("Create your first company profile"))
        elif mode is AddCompanyDialog.Mode.ADD:
            intro1 = _("%s is happy to host your new company!") % app_name
            self.intro_lbl.setText(
                f"""
                <p>{intro1}</p>
                <p>{intro2}</p>
                """
            )
            self.vat_ckb.setEnabled(True)
            self.details_lbl.setText(f"<p><small>({details})</small></p>")
            self.setWindowTitle(_("Add a new company profile"))
        else:
            intro1 = _("The world is changing: update your company profile here...")
            self.intro_lbl.setText(f"<p>{intro1}</p>")
            self.vat_ckb.setEnabled(False)
            self.details_lbl.clear()
            self.setWindowTitle(_("Edit your company profile"))

    def edit_profile(self, profile: schemas.Company) -> None:
        self.origin_profile = profile
        self.name_text.setText(profile.name)
        self.name_text.updateGeometry()
        self.home_dir_selector.setText(profile.home.as_posix())
        self.home_dir_selector.setEnabled(False)
        self.address_text.setText(profile.address.address)
        self.zipcode_text.setText(profile.address.zip_code)
        self.city_text.setText(profile.address.city)
        self.phone_text.setText(profile.phone_number)
        self.email_text.setText(profile.email)
        self.siret_text.setText(profile.siret)
        self.rcs_text.setText(profile.rcs)
        self.vat_ckb.setChecked(profile.no_vat)
        self.penalty_spin.setValue(float(profile.penalty_rate))
        self.discount_spin.setValue(float(profile.discount_rate))
        self.set_mode(AddCompanyDialog.Mode.EDIT)
        self.details_btn.setChecked(True)
        self._enable_buttons(self.is_valid)

    @QtCore.pyqtSlot(bool)
    def toggle_details(self, state: bool):
        self.extension_widget.setVisible(state)
        self.adjustSize()

    def _enable_buttons(self, is_valid: bool):
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(
            is_valid
        )


class SelectCompanyDialog(QtWidgets.QDialog):
    def __init__(
        self, profiles: Iterable[schemas.Company], fixed_size: bool = True, parent=None
    ) -> None:
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
        app_name = "<strong>Dfacto</strong>"
        intro1 = _("Welcome back to %s, your invoicing companion!") % app_name
        intro2 = _("Select a company profile to start with...")
        self.intro_lbl.setText(
            f"""
            <p>{intro1}</p>
            <p>{intro2}</p>
            """
        )
        intro_layout = QtWidgets.QHBoxLayout()
        intro_layout.setContentsMargins(0, 0, 0, 0)
        intro_layout.addWidget(self.intro_pix, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(self.intro_lbl, 0, QtCore.Qt.AlignmentFlag.AlignCenter)
        intro_layout.addStretch()
        intro_widget.setLayout(intro_layout)

        self.profile_cmb = QtWidgets.QComboBox()
        for profile in profiles:
            self.profile_cmb.addItem(profile.name, userData=profile)
        self.profile_cmb.model().sort(0)
        self.profile_cmb.activated.connect(self.on_profile_selection)

        self.home_lbl = QtWidgets.QLabel()

        self.create_btn = QtWidgets.QPushButton(_("New..."))
        self.create_btn.clicked.connect(self.new)
        self.create_lbl = QtWidgets.QLabel()
        msg = _("Your company is not in the list: create yours!")
        self.create_lbl.setText(f"<p>{msg}</p>")
        create_layout = QtWidgets.QHBoxLayout()
        create_layout.addWidget(self.create_lbl)
        create_layout.addWidget(self.create_btn)
        create_layout.addStretch()

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
        main_layout.addWidget(self.profile_cmb)
        main_layout.addWidget(self.home_lbl)
        main_layout.addSpacing(20)
        main_layout.addLayout(create_layout)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.button_box)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self.profile_cmb.setCurrentIndex(0)
        self._enable_buttons(self.is_valid)
        self.new = False
        self.profile_cmb.setFocus()

    @property
    def company(self) -> Optional[schemas.Company]:
        if self.new:
            return None
        return self.profile_cmb.currentData()

    @property
    def is_valid(self) -> bool:
        return self.profile_cmb.currentIndex() >= 0

    @QtCore.pyqtSlot(int)
    def on_profile_selection(self, index: int) -> None:
        self.home_lbl.setText(self.profile_cmb.itemData(index).home.as_posix())
        self.new = False
        self._enable_buttons(self.is_valid)

    @QtCore.pyqtSlot()
    def new(self) -> None:
        self.new = True
        self.accept()

    def _enable_buttons(self, is_valid: bool):
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(
            is_valid
        )
