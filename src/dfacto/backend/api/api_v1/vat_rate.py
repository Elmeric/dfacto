# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Type, TypedDict

from dfacto.backend import crud, schemas
from dfacto.backend.api.command import CommandResponse, CommandStatus, command

from .base import DFactoModel


class PresetRate(TypedDict):
    id: int
    rate: float


@dataclass()
class VatRateModel(DFactoModel[crud.CRUDVatRate, schemas.VatRate]):
    crud_object: crud.CRUDVatRate = crud.vat_rate
    schema: Type[schemas.VatRate] = schemas.VatRate

    @command
    def get_default(self) -> CommandResponse:
        try:
            vat_rate_ = self.crud_object.get_default(self.session)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET_DEFAULT - SQL or database error: {exc}",
            )
        else:
            if vat_rate_ is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    "GET_DEFAULT - Default VAT rate not found.",
                )
            else:
                body = self.schema.from_orm(vat_rate_)
                return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def set_default(self, obj_id: int) -> CommandResponse:
        try:
            old = self.crud_object.get_default(self.session)
            new = self.crud_object.get(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - SQL or database error: {exc}",
            )
        else:
            if new is old:
                return CommandResponse(CommandStatus.COMPLETED)
            if old is None or new is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    "Previous or new default VAT rate not found.",
                )

            try:
                self.crud_object.set_default(
                    self.session, old_default=old, new_default=new
                )
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED, f"SET_DEFAULT - SQL or database error: {exc}"
                )
            else:
                return CommandResponse(CommandStatus.COMPLETED)

    @command
    def update(self, obj_id: int, *, obj_in: schemas.VatRateUpdate) -> CommandResponse:
        try:
            vat_rate_ = self.crud_object.get(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE - SQL or database error: {exc}",
            )
        else:
            if vat_rate_ is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"UPDATE - Object {obj_id} not found.",
                )

            if vat_rate_.is_preset:
                return CommandResponse(
                    CommandStatus.REJECTED,
                    "UPDATE - Preset VAT rates cannot be changed.",
                )

            try:
                vat_rate_ = self.crud_object.update(
                    self.session, db_obj=vat_rate_, obj_in=obj_in
                )
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"UPDATE - Cannot update object {obj_id}: {exc}",
                )
            else:
                body = self.schema.from_orm(vat_rate_)
                return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def delete(self, obj_id: int) -> CommandResponse:
        try:
            vat_rate_ = self.crud_object.get(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - SQL or database error: {exc}",
            )
        else:
            if vat_rate_ is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"DELETE - Object {obj_id} not found.",
                )

            if vat_rate_.is_preset:
                return CommandResponse(
                    CommandStatus.REJECTED,
                    "DELETE - Preset VAT rates cannot be deleted.",
                )

            in_use = vat_rate_.services
            if len(in_use) > 0:
                return CommandResponse(
                    CommandStatus.REJECTED,
                    f"DELETE - VAT rate with id {obj_id} is used"
                    f" by at least '{in_use[0].name}' service.",
                )

            try:
                self.crud_object.delete(self.session, db_obj=vat_rate_)
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"DELETE - Cannot delete object {obj_id}: {exc}",
                )
            else:
                return CommandResponse(CommandStatus.COMPLETED)


vat_rate = VatRateModel()
