# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Type

from dfacto.models import db, crud, schemas
from dfacto.models.api.command import CommandResponse, CommandStatus
from .base import DFactoModel


@dataclass()
class ClientModel(DFactoModel[crud.CRUDClient, schemas.Client]):
    crud_object: crud.CRUDClient = crud.client
    schema: Type[schemas.Client] = schemas.Client

    def get_basket(self, client_id: int) -> CommandResponse:
        try:
            db_obj = self.crud_object.get_basket(self.Session, client_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-BASKET - SQL or database error: {exc}",
            )
        else:
            if db_obj is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"GET-BASKET - Basket of client {client_id} not found.",
                )
            else:
                body = schemas.Basket.from_orm(db_obj)
                return CommandResponse(CommandStatus.COMPLETED, body=body)

    def rename(self, client_id: int, name: str) -> CommandResponse:
        return self.update(client_id, schemas.ClientUpdate(name=name))

    def change_address(self, client_id: int, address: schemas.Address) -> CommandResponse:
        return self.update(client_id, schemas.ClientUpdate(address=address))

    def set_active(self, client_id: int) -> CommandResponse:
        return self.update(client_id, schemas.ClientUpdate(is_active=True))

    def set_inactive(self, client_id: int) -> CommandResponse:
        return self.update(client_id, schemas.ClientUpdate(is_active=False))

    def delete(self, obj_id: int) -> CommandResponse:
        client_ = self.crud_object.get(self.Session, obj_id)

        if client_ is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Object {obj_id} not found.",
            )

        if client_.has_emitted_invoices:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"DELETE - Client {client_.name} has non-DRAFT invoices"
                f" and cannot be deleted.",
            )

        if len(client_.basket.items) > 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"DELETE - Client {client_.name} has a non-empty basket"
                f" and cannot be deleted.",
            )

        try:
            self.crud_object.delete(self.Session, db_obj=client_)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Cannot delete object {obj_id}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)


client = ClientModel(db.Session)
