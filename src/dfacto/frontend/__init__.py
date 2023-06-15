# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dfacto.backend import api, schemas
from dfacto.backend.api import CommandStatus
from dfacto.util import qtutil as QtUtil


def get_current_company() -> schemas.Company:
    response = api.company.get_current()
    if response.status is CommandStatus.COMPLETED:
        company: schemas.Company = response.body
        return company

    # Should not happen as a selected company is mandatory to start the dfacto main window
    QtUtil.raise_fatal_error(f"No selected company - Reason is: {response.reason}")
