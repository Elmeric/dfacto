# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from typing import Union, Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import models, schemas

from .base import CRUDBase, CrudError, CrudIntegrityError


class CRUDService(
    CRUDBase[models.Service, schemas.ServiceCreate, schemas.ServiceUpdate]
):

    def create(self, dbsession: Session, *, obj_in: schemas.ServiceCreate) -> models.Service:
        db_obj = self.model()
        dbsession.add(db_obj)
        try:
            dbsession.flush([db_obj])
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

        obj_in_data = obj_in.flatten()
        obj_in_data["service_id"] = db_obj.id
        revision = models.ServiceRevision(**obj_in_data)
        dbsession.add(revision)
        try:
            dbsession.flush([revision])
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

        db_obj.rev_id = revision.id

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
        else:
            dbsession.refresh(db_obj)
            return db_obj

    def update(
        self,
        dbsession: Session,
        *,
        db_obj: models.Service,
        obj_in: Union[schemas.ServiceUpdate, dict[str, Any]],
    ) -> models.Service:
        updated = False
        current_rev = db_obj.revisions[db_obj.rev_id]

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.flatten()

        for field in ("name", "unit_price", "vat_rate_id"):
            if (
                field in update_data
                and update_data[field] is not None
                and getattr(current_rev, field) != update_data[field]
            ):
                updated = True
            else:
                update_data[field] = getattr(current_rev, field)
        update_data["service_id"] = db_obj.id

        if updated:
            revision = models.ServiceRevision(**update_data)
            dbsession.add(revision)
            try:
                dbsession.flush([revision])
            except SQLAlchemyError as exc:
                dbsession.rollback()
                raise CrudError() from exc
            db_obj.rev_id = revision.id
            try:
                dbsession.commit()
            except SQLAlchemyError as exc:
                dbsession.rollback()
                raise CrudError() from exc
            else:
                dbsession.refresh(db_obj)
                return db_obj
        return db_obj


service = CRUDService(models.Service)
