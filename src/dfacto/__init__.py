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
__all__ = ["run_main"]

import logging
import multiprocessing
import sys

from dfacto.frontend import guimain as gui


def except_hook(exc_type, exc_value, _exc_traceback):  # type: ignore[no-untyped-def]
    error_msg = f"{exc_type.__name__}: {exc_value}"
    logger = logging.getLogger(__name__)
    logger.fatal("%s", error_msg, exc_info=False)
    sys.stderr.write(f"\ndfacto - {str(error_msg)}\n\n")
    # for p in multiprocessing.active_children():
    #     p.terminate()
    sys.exit(1)


def run_main() -> None:
    """Program entry point.

    Handles exceptions not trapped earlier.
    """
    sys.excepthook = except_hook
    sys.exit(gui.qt_main())
    # except Exception as e:
    #     logger = logging.getLogger(__name__)
    #     logger.fatal("Fatal error!", exc_info=True)
    #     sys.stderr.write(f"\ndfacto - {str(e)}\n\n")
    #     sys.exit(1)


if __name__ == "__main__":
    run_main()
