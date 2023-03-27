# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Any, Optional, Union

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import models, schemas

from .base import CRUDBase, CrudError


class CRUDVatRate(
    CRUDBase[models.VatRate, schemas.VatRateCreate, schemas.VatRateUpdate]
):
    def get_default(self, dbsession: Session) -> Optional[models.VatRate]:
        try:
            db_obj = dbsession.scalars(
                select(self.model).where(self.model.is_default == True)
            ).first()
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return db_obj

    def set_default(
        self,
        dbsession: Session,
        *,
        old_default: models.VatRate,
        new_default: models.VatRate,
    ) -> None:
        old_default.is_default = False
        new_default.is_default = True
        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def update(
        self,
        dbsession: Session,
        *,
        db_obj: models.VatRate,
        obj_in: Union[schemas.VatRateUpdate, dict[str, Any]],
    ) -> models.VatRate:
        if isinstance(obj_in, dict):
            is_default = obj_in.get("is_default", None)
            assert (not is_default or db_obj.is_default) and (
                is_default or not db_obj.is_default
            ), "Use 'set_default' instead"

        return super().update(dbsession, db_obj=db_obj, obj_in=obj_in)


vat_rate = CRUDVatRate(models.VatRate)
