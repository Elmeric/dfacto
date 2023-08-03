# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Dfacto is a tool to manage invoices for your company.

Requires Python >= 3.9

Usage:
    ''python -m dfacto''
"""

__all__ = ["IS_FROZEN", "DEV_MODE", "run_main"]

import gettext
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from dfacto.util.logutil import LogConfig
from dfacto.util.qtutil import select_locale
from dfacto.util.settings import SettingsError

if TYPE_CHECKING:

    def _(_text: str) -> str:
        ...


logger = logging.getLogger(__name__)

log_config: LogConfig

IS_FROZEN: Final[bool] = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
DEV_MODE: Final[bool] = os.environ.get("DFACTO_DEV", "0") != "0"


def except_hook(exc_type, exc_value, _exc_traceback):  # type: ignore[no-untyped-def]
    from dfacto import __about__  # pylint: disable=import-outside-toplevel

    error_msg = f"{exc_type.__name__}: {exc_value}"
    logger.fatal("%s", error_msg, exc_info=False)
    sys.stderr.write(f"\ndfacto - {str(error_msg)}\n\n")
    logger.info(_("%(app_name)s is closing..."), {"app_name": __about__.__title__})
    log_config.stop_logging()
    sys.exit(1)


def run_main() -> None:
    """Program entry point."""

    # Handles exceptions not trapped earlier.
    sys.excepthook = except_hook

    # Load settings and initialize the dfacto_settings singleton instance.
    from dfacto.settings import (  # pylint: disable=import-outside-toplevel
        dfacto_settings,
    )

    # Initialize and start the log server.
    global log_config  # pylint: disable=global-statement
    log_config = LogConfig(
        dfacto_settings.app_dirs.user_log_dir / "dfacto.log",
        dfacto_settings.log_level,
        log_on_console=True,
    )
    log_config.init_logging()

    # Select UI language: use locale defined in the settings or ask user if None
    locale_ = dfacto_settings.locale
    if locale_ is None:
        locale_ = select_locale(f"{dfacto_settings.resources}/invoice-32.ico")
        dfacto_settings.locale = locale_
        try:
            dfacto_settings.save()
        except SettingsError as e:
            logger.warning(
                f"Cannot save the selected locale in settings file - Reason is: {e}"
            )

    # Load and install the translation for the selected locale
    locales_dir = Path(__file__).resolve().parent.parent.parent / "locales"
    translations = gettext.translation(
        "dfacto",
        locales_dir,
        languages=[locale_],
        fallback=True,
    )
    translations.install()

    # Import __about__ after translation is installed
    from dfacto import __about__  # pylint: disable=import-outside-toplevel

    app_name = __about__.__title__
    logger.info(_("%(app_name)s is starting..."), {"app_name": app_name})
    logger.info(
        _("Using preferred locale: %(locale)s in %(dir)s"),
        {"locale": locale_, "dir": locales_dir.as_posix()},
    )

    # Log the running mode for information.
    if IS_FROZEN:
        logger.info(_("Running in a PyInstaller bundle"))
    else:
        logger.info(_("Running in a normal Python process"))
    if DEV_MODE:
        logger.info(_("Running in Development mode"))
    else:
        logger.info(_("Running in Production mode"))

    # Import the main UI (it will import backend modules) and launch it.
    from dfacto.frontend import guimain  # pylint: disable=import-outside-toplevel

    ret = guimain.qt_main(translations)

    logger.info(_("%(app_name)s is closing..."), {"app_name": app_name})
    # Stop the log server.
    log_config.stop_logging()

    sys.exit(ret)


if __name__ == "__main__":
    run_main()
