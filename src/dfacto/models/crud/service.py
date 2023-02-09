# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dfacto.models import models
from dfacto.models import schemas

from .base import CRUDBase


class CRUDService(
    CRUDBase[models.Service, schemas.ServiceCreate, schemas.ServiceUpdate]
):
    pass


service = CRUDService(models.Service)
