# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Company:
    name: str
    home: Path
    address: str = ""
    zip_code: str = ""
    city: str = ""
    phone_number: str = ""
    email: str = ""
    siret: str = ""
    rcs: str = ""
    no_vat: bool = False
