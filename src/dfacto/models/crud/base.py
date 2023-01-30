# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
import dataclasses

import sqlalchemy as sa
from sqlalchemy.orm import Session

from dfacto.models.db import BaseModel
from dfacto.models.schemas import BaseSchema

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseSchema)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseSchema)


class CrudError(Exception):
    pass


class CrudIntegrityError(Exception):
    pass


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        """
        self.model = model

    def get(self, db: Session, id_: Any) -> Optional[ModelType]:
        try:
            obj = db.get(self.model, id_)
        except sa.exc.SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return obj

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        try:
            obj_list = db.scalars(sa.select(self.model).offset(skip).limit(limit)).all()
        except sa.exc.SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return obj_list

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
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

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        updated = False
        obj_data = vars(db_obj)

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            # update_data = obj_in.dict(exclude_unset=True)
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

    def delete(self, db: Session, *, id_: int) -> ModelType:
        db_obj = db.get(self.model, id_)
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
