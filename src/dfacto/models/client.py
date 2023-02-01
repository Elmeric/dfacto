# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass, field
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc
import sqlalchemy.orm

from dfacto.models.basket import Basket, BasketModel
from dfacto.models.command import CommandResponse, CommandStatus
from dfacto.models.invoice import Invoice
from dfacto.models.models import _Client


@dataclass()
class Address:
    address: str
    zip_code: str
    city: str


@dataclass()
class Client:
    id: int
    name: str
    code: str
    address: Address
    is_active: bool
    basket: Basket
    invoices: list[Invoice] = field(default_factory=list)


@dataclass()
class ClientModel:
    Session: sa.orm.scoped_session
    basket_model: BasketModel

    def get(self, client_id: int) -> Optional[Client]:
        client: Optional[_Client] = self.Session.get(_Client, client_id)
        if client is None:
            return
        return Client(
            client.id,
            client.name,
            client.code,
            Address(client.address, client.zip_code, client.city),
            client.is_active,
            self.basket_model.get(client.basket.id),
        )

    def list_all(self) -> list[Client]:
        return [
            Client(
                client.id,
                client.name,
                client.code,
                Address(client.address, client.zip_code, client.city),
                client.is_active,
                self.basket_model.get(client.basket.id),
            )
            for client in self.Session.scalars(sa.select(_Client)).all()
        ]

    def add(
        self, name: str, address: str, zip_code: str, city: str, is_active: bool = True
    ) -> CommandResponse:
        client = _Client(
            name=name,
            address=address,
            zip_code=zip_code,
            city=city,
            is_active=is_active,
        )
        self.Session.add(client)
        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED, f"CLIENT-ADD - Cannot add client {name}: {exc}"
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def on_hold(self, client_id: int, hold: bool = True) -> CommandResponse:
        client: Optional[_Client] = self.Session.get(_Client, client_id)
        if client is None:
            return CommandResponse(
                CommandStatus.FAILED, f"CLIENT-ON_HOLD - Client {client_id} not found."
            )

        if hold and client.is_active:
            client.is_active = False
        if not hold and not client.is_active:
            client.is_active = True

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLIENT-ON_HOLD - Cannot set {client.name} active status to {hold}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def rename(self, client_id: int, name: str) -> CommandResponse:
        client: Optional[_Client] = self.Session.get(_Client, client_id)
        if client is None:
            return CommandResponse(
                CommandStatus.FAILED, f"CLIENT-RENAME - Client {client_id} not found."
            )

        if name != client.name:
            client.name = name

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLIENT-RENAME - Cannot rename client {client.name} to {name}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def change_address(self, client_id: int, address: Address) -> CommandResponse:
        client: Optional[_Client] = self.Session.get(_Client, client_id)
        if client is None:
            return CommandResponse(
                CommandStatus.FAILED, f"CLIENT-ADDRESS - Client {client_id} not found."
            )
        client.address = address.address
        client.zip_code = address.zip_code
        client.city = address.city

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLIENT-ADDRESS - Cannot change address of client {client.name}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def delete(self, client_id: int) -> CommandResponse:
        client: Optional[_Client] = self.Session.get(_Client, client_id)

        if client is None:
            return CommandResponse(
                CommandStatus.FAILED, f"CLIENT-DELETE - Client {client_id} not found."
            )

        if client.has_emitted_invoices:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"CLIENT-DELETE - Client {client.name} has non-DRAFT"
                f" invoices and cannot be deleted.",
            )

        if len(client.basket.items) > 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"CLIENT-DELETE - Client {client.name} has a non-empty"
                f" basket and cannot be deleted.",
            )

        self.Session.delete(client)
        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLIENT-DELETE - SQL error while deleting client {client.name}.",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)
