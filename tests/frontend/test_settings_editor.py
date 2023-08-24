# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path

import PyQt6.QtWidgets as QtWidgets
import pytest

from dfacto.frontend.settingsview import SettingsView

pytestmark = pytest.mark.frontend


@pytest.fixture(scope="session", autouse=True)
def install_tr():
    import gettext

    from dfacto.settings import dfacto_settings

    locales_dir = Path(__file__).resolve().parent.parent.parent / "locales"
    translations = gettext.translation(
        "dfacto",
        locales_dir,
        languages=[dfacto_settings.locale],
        fallback=True,
    )
    translations.install()


COMPANY_FOLDER = "DFacto-Test"
FONT_SIZE = 0
LOG_LEVEL = "DEBUG"
QT_SCALE_FACTOR_S = "1.1"
QT_SCALE_FACTOR_F = 1.1
QT_SCALE_DELTA = 1


@pytest.fixture
def init_settings(tmp_path):
    from dfacto.settings import dfacto_settings

    default_company_folder = tmp_path.joinpath(COMPANY_FOLDER).as_posix()
    dfacto_settings.default_company_folder = default_company_folder
    dfacto_settings.font_size = FONT_SIZE
    dfacto_settings.log_level = LOG_LEVEL
    dfacto_settings.qt_scale_factor = QT_SCALE_FACTOR_S
    dfacto_settings.save()

    return dfacto_settings


def test_init(qtbot, init_settings):
    settings = init_settings

    editor = SettingsView()
    # editor.show()
    # qtbot.stop()
    qtbot.addWidget(editor)

    assert editor.default_dir_selector.text() == settings.default_company_folder
    assert editor.log_level_cmb.currentText() == LOG_LEVEL
    assert editor.font_spn.value() == FONT_SIZE
    assert editor.scale_spn.value() == QT_SCALE_FACTOR_F
    assert editor.scale_sld.value() == QT_SCALE_DELTA


def test_change_company_folder(qtbot, init_settings):
    settings = init_settings
    new = "path/to/test"

    editor = SettingsView()
    qtbot.addWidget(editor)

    editor.default_dir_selector.setText(new)
    editor.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).click()
    assert settings.default_company_folder == new


def test_change_log_level(qtbot, init_settings):
    settings = init_settings
    new = "ERROR"

    editor = SettingsView()
    qtbot.addWidget(editor)

    editor.log_level_cmb.setCurrentText(new)
    editor.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).click()
    assert settings.log_level == new


def test_change_scale_factor(qtbot, init_settings):
    settings = init_settings

    new = 1.5
    new_delta = 5
    editor = SettingsView()
    qtbot.addWidget(editor)

    editor.scale_spn.setValue(new)
    assert editor.scale_sld.value() == new_delta
    editor.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).click()
    assert settings.qt_scale_factor == str(new)

    new = 1.3
    new_delta = 3
    editor.scale_sld.setValue(new_delta)
    assert editor.scale_spn.value() == new
    editor.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).click()
    assert settings.qt_scale_factor == str(new)


def test_change_font_size(qtbot, init_settings):
    settings = init_settings
    new = 2

    editor = SettingsView()
    qtbot.addWidget(editor)

    editor.font_spn.setValue(new)
    editor.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).click()
    assert settings.font_size == new


def test_reset(qtbot, init_settings):
    settings = init_settings

    editor = SettingsView()
    qtbot.addWidget(editor)

    editor.reset_btn.click()
    assert editor.default_dir_selector.text() == settings.DEFAULT_COMPANY_FOLDER
    assert editor.log_level_cmb.currentText() == settings.DEFAULT_LOG_LEVEL
    assert editor.font_spn.value() == settings.DEFAULT_FONT_SIZE
    assert editor.scale_spn.value() == float(settings.DEFAULT_QT_SCALE_FACTOR)
    assert editor.scale_sld.value() == int(
        10 * (float(settings.DEFAULT_QT_SCALE_FACTOR) - 1)
    )
