"""The SettingsView displays and update the DfactoSettings model.

Available interactions on the DcfsSettings model are:
    Select the Dfacto data default directory.
    Select the application log level.
    Change the UI font size.
    Change the UI scale factor.
    Reset Dfacto settings to their default values.
"""
import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui
import PyQt6.QtWidgets as QtWidgets

from dfacto import settings as Config
from dfacto.util import qtutil as QtUtil

__all__ = ["SettingsView"]


class SettingsView(QtWidgets.QDialog):
    """Displays and interacts with a DfactoSettings model.

    The SettingsView is composed of:
        The Dfacto data default directory selector.
        The log level selector.
        A spinbox to change the base font size increment.
        A coupled spinbox and slider to change the scale factor.
        The reset to defaults button.
        The dialog OK / Cancel buttons.

    Args:
        parent: a QtMainView.
        *args, **kwargs: Any other positional and keyword argument are passed to
            the parent QDialog along with the parent argument.

    Attributes:
        parent: parent window of the Settings view.
        default_dir_selector: the Dfacto data default directory selector.
        log_level_cmb: the log level selector.
        font_spn: a spinbox to change the base font size increment.
        scale_sld: a slider to change the scale factor.
        scale_spn: a spinbox to change the scale factor.
    """

    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, parent=parent, **kwargs)

        self.parent = parent

        app_name = QtWidgets.QApplication.applicationName()
        action = _("Settings")
        self.setWindowTitle(f"{app_name} - {action}")
        # Prevent resizing the view (its size is handled by the window content).
        self.setWindowFlags(
            QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        locale = Config.dfacto_settings.locale
        select_icon = QtGui.QIcon(
            f"{Config.dfacto_settings.resources}/browse-folder.png"
        )
        self.default_dir_selector = QtUtil.DirectorySelector(
            label=_("Dfacto data default directory:"),
            placeHolder=_("Absolute path"),
            selectIcon=select_icon,
            tip=_("Select the Dfacto data default directory"),
            directoryGetter=lambda: str(Config.dfacto_settings.default_company_folder),
            parent=self,
        )
        self.default_dir_selector.pathSelected.connect(
            lambda path: self.default_dir_selector.setText(path)
        )

        info_lbl = QtWidgets.QLabel(
            _("(Change to these settings will be applied on next start)")
        )

        log_level_lbl = QtWidgets.QLabel(_("Log level:"))
        self.log_level_cmb = QtWidgets.QComboBox()
        tip = _("Select the logging level")
        self.log_level_cmb.setToolTip(tip)
        self.log_level_cmb.setStatusTip(tip)
        self.log_level_cmb.addItems(("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))

        font_lbl = QtWidgets.QLabel(_("Font size delta:"))
        self.font_spn = QtWidgets.QSpinBox()
        self.font_spn.setRange(0, 10)
        self.font_spn.setSingleStep(1)
        self.font_spn.setMaximumWidth(100)
        self.font_spn.setSuffix(" pt")
        tip = _(
            "Increase the base font size by the selected value (between 0 and 10 pt)"
        )
        self.font_spn.setToolTip(tip)
        self.font_spn.setStatusTip(tip)

        scale_lbl = QtWidgets.QLabel(_("Scale factor:"))
        self.scale_sld = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.scale_sld.setRange(0, 10)
        scale_lbl.setBuddy(self.scale_sld)
        self.scale_spn = QtWidgets.QDoubleSpinBox()
        self.scale_spn.setLocale(QtCore.QLocale(locale))
        self.scale_spn.setRange(1, 2)
        self.scale_spn.setDecimals(1)
        self.scale_spn.setSingleStep(0.1)
        self.scale_spn.setMaximumWidth(100)
        tip = _("Apply a global scaling to the Dfacto UI")
        self.scale_spn.setToolTip(tip)
        self.scale_spn.setStatusTip(tip)
        self.scale_sld.setToolTip(tip)
        self.scale_sld.setStatusTip(tip)
        self.scale_spn.valueChanged.connect(self.select_qt_scale_factor_from_float)
        self.scale_sld.valueChanged.connect(self.select_qt_scale_factor_from_int)

        self.reset_btn = QtWidgets.QPushButton(_("Reset to defaults"))
        self.reset_btn.clicked.connect(self.reset_to_defaults)

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

        edit_layout = QtWidgets.QGridLayout()
        edit_layout.addWidget(self.default_dir_selector, 0, 0, 1, 3)
        vertical_spacer = QtWidgets.QSpacerItem(
            20,
            40,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        edit_layout.addItem(vertical_spacer, 2, 0, 1, 1)
        edit_layout.addWidget(info_lbl, 3, 0, 1, 3)
        edit_layout.addWidget(log_level_lbl, 4, 0)
        edit_layout.addWidget(self.log_level_cmb, 4, 1, 1, 3)
        edit_layout.addWidget(font_lbl, 5, 0)
        edit_layout.addWidget(self.font_spn, 5, 1, 1, 1)
        edit_layout.addWidget(scale_lbl, 6, 0)
        edit_layout.addWidget(self.scale_spn, 6, 1, 1, 1)
        edit_layout.addWidget(self.scale_sld, 6, 2, 1, 1)
        vertical_spacer = QtWidgets.QSpacerItem(
            20,
            40,
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        edit_layout.addItem(vertical_spacer, 7, 0, 1, 1)
        edit_layout.addWidget(self.reset_btn, 8, 0, 1, 1)
        edit_layout.addWidget(self.button_box, 9, 1, 1, 2)

        self.setLayout(edit_layout)

        self.default_dir_selector.setText(Config.dfacto_settings.default_company_folder)
        self.log_level_cmb.setCurrentText(Config.dfacto_settings.log_level)
        self.font_spn.setValue(Config.dfacto_settings.font_size)
        self.scale_spn.setValue(float(Config.dfacto_settings.qt_scale_factor))

    @QtCore.pyqtSlot()
    def accept(self):
        """Apply the new settings and leave the dialog"""
        Config.dfacto_settings.default_company_folder = self.default_dir_selector.text()
        Config.dfacto_settings.qt_scale_factor = str(self.scale_spn.value())
        Config.dfacto_settings.log_level = self.log_level_cmb.currentText()
        Config.dfacto_settings.font_size = self.font_spn.value()

        super().accept()

    @QtCore.pyqtSlot(int)
    def select_qt_scale_factor_from_int(self, value):
        """Propagate the scale factor from slider to spinbox.

        Convert the slider int value to a floating value for the spinbox.

        Args:
            value: the new scale factor value selected on the slider.
        """
        value = value / 10 + 1
        with QtCore.QSignalBlocker(self.scale_spn):
            self.scale_spn.setValue(value)

    @QtCore.pyqtSlot(float)
    def select_qt_scale_factor_from_float(self, value):
        """Propagate the scale factor from spinbox to slider.

        Convert the spinbox float value to an int value for the slider.

        Args:
            value: the new scale factor value selected on the spinbox.
        """
        with QtCore.QSignalBlocker(self.scale_sld):
            self.scale_sld.setValue(int(10 * (value - 1)))

    @QtCore.pyqtSlot()
    def reset_to_defaults(self):
        """Restore the dialog with default settings values"""
        # Retrieve the settings class to access its setting's default values.
        settings_class = type(Config.dfacto_settings)
        self.default_dir_selector.setText(
            settings_class.default_company_folder.default_value
        )
        self.log_level_cmb.setCurrentText(settings_class.log_level.default_value)
        self.font_spn.setValue(settings_class.font_size.default_value)
        self.scale_spn.setValue(float(settings_class.qt_scale_factor.default_value))
