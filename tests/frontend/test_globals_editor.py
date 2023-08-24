# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from decimal import Decimal

import PyQt6.QtCore as QtCore
import PyQt6.QtWidgets as QtWidgets
import pytest

from dfacto.backend import schemas
from dfacto.frontend.globals_editor import GlobalsEditor

pytestmark = pytest.mark.frontend


@pytest.fixture(scope="session", autouse=True)
def install_tr():
    import gettext
    from pathlib import Path

    from dfacto.settings import dfacto_settings

    locales_dir = Path(__file__).resolve().parent.parent.parent / "locales"
    translations = gettext.translation(
        "dfacto",
        locales_dir,
        languages=[dfacto_settings.locale],
        fallback=True,
    )
    translations.install()


DUE_DELTA = 15
PENALTY_RATE_D = Decimal("12.0")
PENALTY_RATE_F = 12.0
DISCOUNT_RATE_D = Decimal("2.5")
DISCOUNT_RATE_F = 2.5
FAKE_GLOBALS = schemas.Globals(
    id=1,
    due_delta=DUE_DELTA,
    penalty_rate=PENALTY_RATE_D,
    discount_rate=DISCOUNT_RATE_D,
    is_current=True,
)


def test_init(qtbot):
    editor = GlobalsEditor(FAKE_GLOBALS)
    # editor.show()
    # qtbot.stop()
    qtbot.addWidget(editor)

    assert editor.due_spn.value() == DUE_DELTA
    assert editor.penalty_spn.value() == PENALTY_RATE_F
    assert editor.discount_spn.value() == DISCOUNT_RATE_F
    assert not editor.button_box.button(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
    ).isEnabled()
    assert not editor.reset_btn.isEnabled()


@pytest.mark.parametrize(
    "spn, old, new, attr, res",
    (
        ("due_spn", DUE_DELTA, 45, "due_delta", 45),
        ("penalty_spn", PENALTY_RATE_F, 20.0, "penalty_rate", Decimal("20.0")),
        ("discount_spn", DISCOUNT_RATE_F, 3.0, "discount_rate", Decimal("3.0")),
    ),
)
def test_change(spn, old, new, attr, res, qtbot):
    editor = GlobalsEditor(FAKE_GLOBALS)
    qtbot.addWidget(editor)

    spn_box = getattr(editor, spn)
    spn_box.setValue(new)

    result = getattr(editor.globals, attr)
    assert result == res
    assert editor.button_box.button(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
    ).isEnabled()
    assert editor.reset_btn.isEnabled()

    spn_box.setValue(old)

    assert not editor.button_box.button(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
    ).isEnabled()
    assert not editor.reset_btn.isEnabled()


@pytest.mark.parametrize("spn", ("due_spn", "penalty_spn", "discount_spn"))
def test_clear(spn, qtbot):
    editor = GlobalsEditor(FAKE_GLOBALS)
    qtbot.addWidget(editor)

    spn_box = getattr(editor, spn)
    suffix = spn_box.suffix()
    spn_box.selectAll()

    def check_suffix(txt: str) -> bool:
        return txt == suffix

    with qtbot.wait_signal(
        spn_box.lineEdit().textEdited, timeout=1000, check_params_cb=check_suffix
    ):
        qtbot.keyClick(spn_box, QtCore.Qt.Key.Key_Delete)

    assert spn_box.value() == 0
    assert editor.button_box.button(
        QtWidgets.QDialogButtonBox.StandardButton.Ok
    ).isEnabled()
    assert editor.reset_btn.isEnabled()
