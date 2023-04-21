# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Fotocop is a tool to copy images from a movable support such as a SD Card
onto your local HDD.

Images can be renamed according to a user-defined pattern and using EXIF data.

Requires Python >= 3.6.1

Usage:
    ''python -m fotocop''
"""
__all__ = ["run_main"]

import logging
import sys

from dfacto.frontend import guimain as gui


def except_hook(cls, exception, traceback_):
    error_msg = f"{cls.__name__}: {exception}"
    # error_msg = "".join(traceback.format_exception(cls, exception, traceback_))
    logger = logging.getLogger(__name__)
    logger.fatal("%s", error_msg, exc_info=False)


def run_main():
    """Program entry point.

    Handles exceptions not trapped earlier.
    """
    sys.excepthook = except_hook
    try:
        sys.exit(gui.qt_main())
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.fatal("Fatal error!", exc_info=True)
        sys.stderr.write(f"\ndfacto - {str(e)}\n\n")
        sys.exit(1)


if __name__ == "__main__":
    run_main()
