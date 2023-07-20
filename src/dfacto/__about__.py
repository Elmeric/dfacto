# Directly modelled on Donald Stufft's readme_renderer code:
# https://github.com/pypa/readme_renderer/blob/master/readme_renderer/__about__.py

from typing import TYPE_CHECKING

if TYPE_CHECKING:

    def _(_text: str) -> str:
        ...


__all__ = [
    "__title__",
    "__summary__",
    "__uri__",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__copyright__",
]

__title__ = "Dfacto"
# pylint: disable-next=assignment-from-no-return
__summary__ = _("Your invoicing assistant!")
__uri__ = "https://github.com/Elmeric/dfacto"

__version__ = "1.1.1"

__author__ = "Eric Lemoine"
__email__ = "erik.lemoine@gmail.com"

__license__ = "BSD 3-Clause"
__copyright__ = f"Copyright 2023 {__author__}"
