# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Type

from dfacto.backend import crud, schemas
from dfacto.backend.api.command import CommandResponse, CommandStatus, command

from .base import DFactoModel


@dataclass()
class ServiceModel(DFactoModel[crud.CRUDService, schemas.Service]):
    crud_object: crud.CRUDService = crud.service
    schema: Type[schemas.Service] = schemas.Service

    @command
    def get_all(self, current_only: bool = True) -> CommandResponse:
        try:
            db_objs = self.crud_object.get_all(self.session, current_only=current_only)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-ALL - SQL or database error: {exc}",
            )
        body = [self.schema.from_orm(db_obj) for db_obj in db_objs]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def update(
        self, obj_id: int, *, obj_in: schemas.ServiceUpdate  # type: ignore[override]
    ) -> CommandResponse:
        try:
            db_obj = self.crud_object.get_current(self.session, obj_id)
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


service = ServiceModel()
