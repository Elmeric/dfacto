# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dfacto.models.models import Service
from dfacto.models.schemas.service import ServiceCreate, ServiceUpdate

from .base import CRUDBase


class CRUDService(CRUDBase[Service, ServiceCreate, ServiceUpdate]):
    pass


service = CRUDService(Service)
