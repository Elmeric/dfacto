# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Dfacto is a tool to manage invoices for your company.

Requires Python >= 3.8

Usage:
    ''python -m dfacto''
"""

__all__ = ["IS_FROZEN", "DEV_MODE", "run_main"]

import logging
import os
import sys
from typing import Final

from dfacto.util.logutil import LogConfig

logger = logging.getLogger(__name__)

log_config: LogConfig

IS_FROZEN: Final[bool] = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
DEV_MODE: Final[bool] = os.environ.get("DFACTO_DEV", "0") != "0"


def except_hook(exc_type, exc_value, _exc_traceback):  # type: ignore[no-untyped-def]
    error_msg = f"{exc_type.__name__}: {exc_value}"
    logger.fatal("%s", error_msg, exc_info=False)
    sys.stderr.write(f"\ndfacto - {str(error_msg)}\n\n")
    logger.info("Dfacto is closing...")
    log_config.stop_logging()
    sys.exit(1)


def run_main() -> None:
    """Program entry point."""
    global log_config  # pylint: disable=global-statement

    # Handles exceptions not trapped earlier.
    sys.excepthook = except_hook

    # Load settings and initialize the dfacto_settings singleton instance.
    from dfacto.settings import (  # pylint: disable=import-outside-toplevel
        dfacto_settings,
    )

    # Initialize and start the log server.
    log_config = LogConfig(
        dfacto_settings.app_dirs.user_log_dir / "dfacto.log",
        dfacto_settings.log_level,
        log_on_console=True,
    )
    log_config.init_logging()

    logger.info("Dfacto is starting...")

    # Log the running mode for information.
    if IS_FROZEN:
        logger.info("Running in a PyInstaller bundle")
    else:
        logger.info("Running in a normal Python process")
    if DEV_MODE:
        logger.info("Running in Development mode")
    else:
        logger.info("Running in Production mode")

    # Import the main UI (it will import backend modules) and launch it.
    from dfacto.frontend import guimain  # pylint: disable=import-outside-toplevel

    ret = guimain.qt_main()

    logger.info("Dfacto is closing...")
    # Stop the log server.
    log_config.stop_logging()

    sys.exit(ret)


if __name__ == "__main__":
    run_main()
