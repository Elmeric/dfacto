# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class BaseSchema:
    def flatten(self) -> dict[str, Any]:
        return asdict(self)
