# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from dfacto.backend import crud, schemas
from dfacto.backend.api.command import CommandResponse, CommandStatus


@dataclass
class CompanyModel:
    crud_object: crud.CRUDCompany = crud.company
    schema: Type[schemas.Company] = schemas.Company

    def get(self, name: str) -> CommandResponse:
        prev = self.crud_object.get(name)
        if prev is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET - Company profile {name} not found",
            )
        body = self.schema.from_orm(prev)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_all(self) -> CommandResponse:
        companies = self.crud_object.get_all()
        body = [self.schema.from_orm(company_) for company_ in companies]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def add(self, obj_in: schemas.CompanyCreate) -> CommandResponse:
        try:
            db_obj = self.crud_object.create(obj_in=obj_in)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD - Cannot add object: {exc}",
            )
        else:
            body = self.schema.from_orm(db_obj)
            return CommandResponse(CommandStatus.COMPLETED, body=body)


company = CompanyModel()
