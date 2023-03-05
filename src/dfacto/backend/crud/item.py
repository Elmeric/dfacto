# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dfacto.backend import models, schemas

from .base import CRUDBase


class CRUDItem(CRUDBase[models.Item, schemas.ItemCreate, schemas.ItemUpdate]):
    pass


item = CRUDItem(models.Item)
