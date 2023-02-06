# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.orm import scoped_session

from dfacto.models import crud, schemas
from dfacto.models.command import CommandResponse, CommandStatus

CRUDObjectType = TypeVar("CRUDObjectType", bound=crud.CRUDBase)
SchemaType = TypeVar("SchemaType", bound=schemas.BaseSchema)


@dataclass()
class DFactoModel(Generic[CRUDObjectType, SchemaType]):
    Session: scoped_session
    crud_object: Optional[CRUDObjectType] = None
    schema: Optional[Type[SchemaType]] = None

    def get(self, obj_id: int) -> CommandResponse:
        try:
            db_obj = self.crud_object.get(self.Session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET - SQL or database error: {exc}",
            )
        else:
            if db_obj is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"GET - Object {obj_id} not found.",
                )
            else:
                body = self.schema.from_orm(db_obj)
                return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_multi(self, skip: int = 0, limit: int = 10) -> CommandResponse:
        try:
            db_objs = self.crud_object.get_multi(self.Session, skip=skip, limit=limit)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-MULTI - SQL or database error: {exc}",
            )
        else:
            body = [self.schema.from_orm(db_obj) for db_obj in db_objs]
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_all(self) -> CommandResponse:
        try:
            db_objs = self.crud_object.get_all(self.Session)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-ALL - SQL or database error: {exc}",
            )
        else:
            body = [self.schema.from_orm(db_obj) for db_obj in db_objs]
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def add(self, obj_in: crud.CreateSchemaType) -> CommandResponse:
        try:
            db_obj = self.crud_object.create(self.Session, obj_in=obj_in)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD - Cannot add object: {exc}",
            )
        else:
            body = self.schema.from_orm(db_obj)
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def update(self, obj_id: int, obj_in: crud.UpdateSchemaType) -> CommandResponse:
        db_obj = self.crud_object.get(self.Session, obj_id)
        if db_obj is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - Object {obj_id} not found.",
            )

        try:
            db_obj = self.crud_object.update(
                self.Session, db_obj=db_obj, obj_in=obj_in
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - Cannot update object {obj_id}: {exc}",
            )
        else:
            body = self.schema.from_orm(db_obj)
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def delete(self, obj_id: int) -> CommandResponse:
        db_obj = self.crud_object.get(self.Session, obj_id)
        if db_obj is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Object {obj_id} not found.",
            )

        try:
            self.crud_object.delete(self.Session, db_obj=db_obj)
        except crud.CrudIntegrityError:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"DELETE - Object {obj_id}"
                f" is used by at least one other object.",
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Cannot delete object {obj_id}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)
