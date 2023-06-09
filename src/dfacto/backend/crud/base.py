# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Any, Generic, Optional, Type, TypeVar, Union, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import schemas
from dfacto.backend.models import ModelType

CreateSchemaType = TypeVar(  # pylint: disable=invalid-name
    "CreateSchemaType", bound=schemas.BaseSchema  # type: ignore[type-arg]
)
UpdateSchemaType = TypeVar(  # pylint: disable=invalid-name
    "UpdateSchemaType", bound=schemas.BaseSchema  # type: ignore[type-arg]
)


class CrudError(Exception):
    pass


class CrudIntegrityError(CrudError):
    pass


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """CRUD object with default methods to Create, Read, Update, Delete (CRUD)."""
        self.model = model

    def get(self, dbsession: Session, obj_id: int) -> Optional[ModelType]:
        try:
            obj = dbsession.get(self.model, obj_id)
        except SQLAlchemyError as exc:
            raise CrudError from exc
        return obj

    def get_multi(
        self, dbsession: Session, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        try:
            obj_list = cast(
                list[ModelType],
                dbsession.scalars(select(self.model).offset(skip).limit(limit)).all(),
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        return obj_list

    def get_all(self, dbsession: Session) -> list[ModelType]:
        try:
            obj_list = cast(
                list[ModelType], dbsession.scalars(select(self.model)).all()
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        return obj_list

    def create(self, dbsession: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.flatten()
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
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, dict[str, Any]],
    ) -> ModelType:
        updated = False
        obj_data = vars(db_obj)

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            # update_data = obj_in.dict(exclude_unset=True)
            update_data = obj_in.flatten()

        for field in obj_data:
            if (
                field in update_data
                and update_data[field] is not None
                and getattr(db_obj, field) != update_data[field]
            ):
                setattr(db_obj, field, update_data[field])
                updated = True

        if updated:
            try:
                dbsession.commit()
            except SQLAlchemyError as exc:
                dbsession.rollback()
                raise CrudError() from exc
            dbsession.refresh(db_obj)
            return db_obj
        return db_obj

    def delete(self, dbsession: Session, *, db_obj: ModelType) -> None:
        dbsession.delete(db_obj)
        try:
            dbsession.commit()
        except IntegrityError as exc:
            dbsession.rollback()
            raise CrudIntegrityError() from exc
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
