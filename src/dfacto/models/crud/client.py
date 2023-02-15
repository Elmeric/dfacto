# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Optional, Union, Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models import models
from dfacto.models import schemas

from .base import CRUDBase, CrudError


class CRUDClient(
    CRUDBase[models.Client, schemas.ClientCreate, schemas.ClientUpdate]
):
    def get_basket(self, dbsession: scoped_session, id_: int) -> Optional[models.Basket]:
        client = dbsession.get(self.model, id_)
        if client is None:
            return None
        return client.basket


client = CRUDClient(models.Client)
