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
        profile = self.crud_object.get(name)
        if profile is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET - Company profile {name} not found",
            )
        body = self.schema.from_orm(profile)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_current(self) -> CommandResponse:
        profile = self.crud_object.get_current()
        if profile is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET - No selected company profile",
            )
        body = self.schema.from_orm(profile)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_all(self) -> CommandResponse:
        companies = self.crud_object.get_all()
        body = [self.schema.from_orm(company_) for company_ in companies]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_others(self) -> CommandResponse:
        profile = self.crud_object.get_current()
        if profile is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET_OTHERS - No selected company profile",
            )
        companies = self.crud_object.get_all()
        body = [
            self.schema.from_orm(company_)
            for company_ in companies
            if company_.name != profile.name
        ]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def select(self, name: str, *, is_new: bool) -> CommandResponse:
        try:
            self.crud_object.select(name, is_new=is_new)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"SELECT - Cannot select object: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

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

    def update(self, name: str, *, obj_in: schemas.CompanyUpdate) -> CommandResponse:
        db_obj = self.crud_object.get(name)
        if db_obj is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - Company profile {name} not found.",
            )

        try:
            db_obj = self.crud_object.update(db_obj=db_obj, obj_in=obj_in)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - Cannot update company profile {name}: {exc}",
            )
        else:
            body = self.schema.from_orm(db_obj)
            return CommandResponse(CommandStatus.COMPLETED, body=body)


company = CompanyModel()
