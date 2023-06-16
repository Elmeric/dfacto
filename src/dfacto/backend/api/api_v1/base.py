# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field
from typing import Generic, Type, TypeVar

from sqlalchemy.orm import Session

from dfacto.backend import crud, schemas
from dfacto.backend.api.command import CommandResponse, CommandStatus, command

CRUDObjectType = TypeVar(  # pylint: disable=invalid-name
    "CRUDObjectType", bound=crud.CRUDBase  # type: ignore[type-arg]
)
SchemaType = TypeVar(  # pylint: disable=invalid-name
    "SchemaType", bound=schemas.BaseSchema  # type: ignore[type-arg]
)


@dataclass()
class DFactoModel(Generic[CRUDObjectType, SchemaType]):
    crud_object: CRUDObjectType
    schema: Type[SchemaType]
    session: Session = field(init=False)

    @command
    def get(self, obj_id: int) -> CommandResponse:
        try:
            db_obj = self.crud_object.get(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET - SQL or database error: {exc}",
            )
        if db_obj is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET - Object {obj_id} not found.",
            )
        body = self.schema.from_orm(db_obj)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_multi(self, *, skip: int = 0, limit: int = 10) -> CommandResponse:
        try:
            db_objs = self.crud_object.get_multi(self.session, skip=skip, limit=limit)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-MULTI - SQL or database error: {exc}",
            )
        body = [self.schema.from_orm(db_obj) for db_obj in db_objs]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_all(self) -> CommandResponse:
        try:
            db_objs = self.crud_object.get_all(self.session)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-ALL - SQL or database error: {exc}",
            )
        body = [self.schema.from_orm(db_obj) for db_obj in db_objs]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def add(self, obj_in: crud.CreateSchemaType) -> CommandResponse:
        try:
            db_obj = self.crud_object.create(self.session, obj_in=obj_in)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD - Cannot add object: {exc}",
            )
        body = self.schema.from_orm(db_obj)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def update(self, obj_id: int, *, obj_in: crud.UpdateSchemaType) -> CommandResponse:
        try:
            db_obj = self.crud_object.get(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - SQL or database error: {exc}",
            )

        if db_obj is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - Object {obj_id} not found.",
            )

        try:
            db_obj = self.crud_object.update(self.session, db_obj=db_obj, obj_in=obj_in)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - Cannot update object {obj_id}: {exc}",
            )
        body = self.schema.from_orm(db_obj)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def delete(self, obj_id: int) -> CommandResponse:
        try:
            db_obj = self.crud_object.get(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - SQL or database error: {exc}",
            )

        if db_obj is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Object {obj_id} not found.",
            )

        try:
            self.crud_object.delete(self.session, db_obj=db_obj)
        except crud.CrudIntegrityError:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"DELETE - Object {obj_id}" f" is used by at least one other object.",
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Cannot delete object {obj_id}: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED)
