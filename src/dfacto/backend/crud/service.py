# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import datetime
from random import randint
from typing import Any, Optional, Union, cast

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import models, schemas

from .base import CRUDBase, CrudError


class CRUDService(
    CRUDBase[models.Service, schemas.ServiceCreate, schemas.ServiceUpdate]
):
    def get(
        self,
        dbsession: Session,
        obj_id: tuple[int, int],  # type: ignore[override]
    ) -> Optional[models.Service]:
        try:
            obj = dbsession.get(self.model, obj_id)
        except SQLAlchemyError as exc:
            raise CrudError from exc
        return obj

    def get_all(
        self, dbsession: Session, current_only: bool = True
    ) -> list[models.Service]:
        if current_only:
            return self._get_all_current(dbsession)
        return self._get_all(dbsession)

    def _get_all_current(self, dbsession: Session) -> list[models.Service]:
        try:
            obj_list = cast(
                list[models.Service],
                dbsession.scalars(
                    # pylint: disable-next=singleton-comparison
                    select(self.model).where(self.model.is_current == True)
                ).all(),
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        return obj_list

    def _get_all(self, dbsession: Session) -> list[models.Service]:
        try:
            obj_list = cast(
                list[models.Service], dbsession.scalars(select(self.model)).all()
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        return obj_list

    def get_current(self, dbsession: Session, obj_id: int) -> models.Service:
        try:
            service_ = dbsession.scalars(
                select(self.model).where(self.model.id == obj_id)
                # pylint: disable-next=singleton-comparison
                .where(self.model.is_current == True)
            ).one()
        except SQLAlchemyError as exc:
            raise CrudError from exc
        return service_

    def create(
        self, dbsession: Session, *, obj_in: schemas.ServiceCreate
    ) -> models.Service:
        obj_in_data = obj_in.flatten()
        obj_in_data["id"] = randint(1, 100000)
        obj_in_data["version"] = 1
        db_obj = self.model(**obj_in_data)
        dbsession.add(db_obj)
        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
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
        assert db_obj.is_current

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.flatten()

        for field in ("name", "unit_price", "vat_rate_id"):
            if (
                field in update_data
                and update_data[field] is not None
                and getattr(db_obj, field) != update_data[field]
            ):
                updated = True
            else:
                update_data[field] = getattr(db_obj, field)

        if updated:
            # Create a new version
            now = datetime.now()
            update_data["id"] = db_obj.id
            update_data["version"] = db_obj.version + 1
            update_data["from_"] = now
            new_db_obj = self.model(**update_data)
            dbsession.add(new_db_obj)

            # Set the current version as a old one
            db_obj.is_current = False
            db_obj.to_ = now

            try:
                dbsession.commit()
            except SQLAlchemyError as exc:
                dbsession.rollback()
                raise CrudError() from exc
            dbsession.refresh(new_db_obj)
            return new_db_obj

        return db_obj


service = CRUDService(models.Service)
