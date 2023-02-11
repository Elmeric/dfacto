# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import ClassVar, Type, TypedDict

from dfacto.models import db, crud, schemas
from dfacto.models.api.command import CommandResponse, CommandStatus
from .base import DFactoModel


class PresetRate(TypedDict):
    id: int
    rate: float


@dataclass()
class VatRateModel(DFactoModel[crud.CRUDVatRate, schemas.VatRate]):
    crud_object: crud.CRUDVatRate = crud.vat_rate
    schema: Type[schemas.VatRate] = schemas.VatRate

    def get_default(self) -> CommandResponse:
        db_obj = self.crud_object.get_default(self.Session)
        return CommandResponse(
            CommandStatus.COMPLETED,
            body=self.schema.from_orm(db_obj)
        )

    def set_default(self, vat_rate_id: int) -> CommandResponse:
        try:
            self.crud_object.set_default(self.Session, vat_rate_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"SET_DEFAULT - SQL or database error: {exc}"
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def update(self, obj_id: int, obj_in: schemas.VatRateUpdate) -> CommandResponse:
        db_obj = self.crud_object.get(self.Session, obj_id)
        if db_obj is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - Object {obj_id} not found.",
            )

        if db_obj.is_preset:
            return CommandResponse(
                CommandStatus.REJECTED,
                "UPDATE - Preset VAT rates cannot be changed.",
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

    def delete(self, vat_rate_id: int) -> CommandResponse:
        vat_rate = self.crud_object.get(self.Session, vat_rate_id)

        if vat_rate is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Object {vat_rate_id} not found.",
            )

        if vat_rate.is_preset:
            return CommandResponse(
                CommandStatus.REJECTED,
                "DELETE - Preset VAT rates cannot be deleted.",
            )

        in_use = vat_rate.services
        if len(in_use) > 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"DELETE - VAT rate with id {vat_rate_id} is used"
                f" by at least '{in_use[0].name}' service.",
            )

        try:
            self.crud_object.delete(self.Session, db_obj=vat_rate)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Cannot delete object {vat_rate_id}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)


vat_rate = VatRateModel(db.Session)
