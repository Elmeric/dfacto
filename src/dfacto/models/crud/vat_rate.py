# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Union, Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models import models
from dfacto.models import schemas

from .base import CRUDBase, CrudError, CrudIntegrityError


class CRUDVatRate(
    CRUDBase[models.VatRate, schemas.VatRateCreate, schemas.VatRateUpdate]
):
    def get_default(self, dbsession: scoped_session) -> models.VatRate:
        return dbsession.scalars(
            select(self.model).where(self.model.is_default == True)
        ).first()

    def set_default(self, dbsession: scoped_session, obj_id: int) -> None:
        old = self.get_default(dbsession)
        new = self.get(dbsession, obj_id)
        old.is_default = False
        new.is_default = True
        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def update(
        self,
        dbsession: scoped_session,
        *,
        db_obj: models.VatRate,
        obj_in: Union[schemas.VatRateUpdate, dict[str, Any]],
    ) -> models.VatRate:
        if isinstance(obj_in, dict):
            is_default = obj_in.get("is_default", None)
            if (is_default and not db_obj.is_default) or (not is_default and db_obj.is_default):
                raise CrudIntegrityError
        return super().update(dbsession, db_obj=db_obj, obj_in=obj_in)


vat_rate = CRUDVatRate(models.VatRate)
