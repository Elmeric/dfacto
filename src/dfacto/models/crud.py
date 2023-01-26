# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Type, Optional
import dataclasses

import sqlalchemy as sa
from sqlalchemy.orm import Session

from dfacto.models.model import _VatRate
from dfacto.models.schema import VatRateCreate, VatRateUpdate


class CrudError(Exception):
    pass


class CrudIntegrityError(Exception):
    pass


class CrudVatRate:
    def __init__(self, model: Type[_VatRate]):
        self.model = model

    def get(self, db: Session, id_: int) -> Optional[_VatRate]:
        return db.get(self.model, id_)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 10) -> list[_VatRate]:
        return db.scalars(
                sa.select(self.model).offset(skip).limit(limit)
            ).all()

    def create(self, db: Session, *, obj_in: VatRateCreate) -> _VatRate:
        obj_in_data = dataclasses.asdict(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        try:
            db.commit()
        except sa.exc.SQLAlchemyError as exc:
            db.rollback()
            raise CrudError() from exc
        else:
            db.refresh(db_obj)
            return db_obj

    def update(self, db: Session, *, db_obj: _VatRate, obj_in: VatRateUpdate) -> _VatRate:
        updated = False
        obj_data = vars(db_obj)
        update_data = dataclasses.asdict(obj_in)
        for field in obj_data:
            if field in update_data and getattr(db_obj, field) != update_data[field]:
                setattr(db_obj, field, update_data[field])
                updated = True
        if updated:
            db.add(db_obj)
            try:
                db.commit()
            except sa.exc.SQLAlchemyError as exc:
                db.rollback()
                raise CrudError() from exc
            else:
                db.refresh(db_obj)
                return db_obj
        return db_obj

    def delete(self, db: Session, *, db_obj: _VatRate) -> _VatRate:
        db.delete(db_obj)
        try:
            db.commit()
        except sa.exc.IntegrityError as exc:
            db.rollback()
            raise CrudIntegrityError() from exc
        except sa.exc.SQLAlchemyError as exc:
            db.rollback()
            raise CrudError() from exc
        else:
            return db_obj


crud_vat_rate = CrudVatRate(_VatRate)
