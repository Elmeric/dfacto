# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc

from dfacto.models import basket, db, invoice, model


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

    @property
    def basket(self) -> basket.Basket:
        client: model._Client = db.Session.get(model._Client, self.id)
        return basket.get(client.basket.id)

    @property
    def invoices(self) -> list[invoice.Invoice]:
        return []


def get(client_id: Optional[int] = None) -> Client:
    client: model._Client = db.Session.get(model._Client, client_id)
    if client is None:
        raise db.RejectedCommand(f"CLIENT-GET - Client {client_id} not found.")
    return Client(
        client.id,
        client.name,
        client.code,
        Address(client.address, client.zip_code, client.city),
        client.is_active,
    )


def list_all() -> list[Client]:
    return [
        Client(
            client.id,
            client.name,
            client.code,
            Address(client.address, client.zip_code, client.city),
            client.is_active,
        )
        for client in db.Session.scalars(sa.select(model._Client)).all()
    ]


def add(
    name: str, address: str, zip_code: str, city: str, is_active: bool = True
) -> Client:
    client = model._Client(
        name=name, address=address, zip_code=zip_code, city=city, is_active=is_active
    )
    db.Session.add(client)
    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(f"Cannot add client {name}: {exc}")
    else:
        return Client(
            client.id,
            client.name,
            client.code,
            Address(client.address, client.zip_code, client.city),
            client.is_active,
        )


def on_hold(client_id: int, hold: bool = True) -> None:
    client: model._Client = db.Session.get(model._Client, client_id)
    if client is None:
        raise db.RejectedCommand(f"CLIENT-ON_HOLD - Client {client_id} not found.")

    if hold and client.is_active:
        client.is_active = False
    if not hold and not client.is_active:
        client.is_active = True

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.RejectedCommand(
            f"CLIENT-ON_HOLD - Cannot set {client.name} active status to {hold}: {exc}"
        )


def rename(client_id: int, name: str) -> None:
    client: model._Client = db.Session.get(model._Client, client_id)
    if client is None:
        raise db.RejectedCommand(f"CLIENT-RENAME - Client {client_id} not found.")

    if name != client.name:
        client.name = name

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.RejectedCommand(
            f"CLIENT-RENAME - Cannot rename client {client.name} to {name}: {exc}"
        )


def change_address(client_id: int, address: Address) -> None:
    client: model._Client = db.Session.get(model._Client, client_id)
    if client is None:
        raise db.RejectedCommand(f"CLIENT-ADDRESS - Client {client_id} not found.")
    client.address = address.address
    client.zip_code = address.zip_code
    client.city = address.city

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.RejectedCommand(
            f"CLIENT-ADDRESS - Cannot change address of client {client.name}: {exc}"
        )


def delete(client_id: int) -> None:
    client: model._Client = db.Session.get(model._Client, client_id)

    if client is None:
        raise db.RejectedCommand(f"CLIENT-DELETE - Client {client_id} not found.")

    if client.has_emitted_invoices:
        raise db.RejectedCommand(
            f"CLIENT-DELETE - Client {client.name} has non-DRAFT"
            f" invoices and cannot be deleted."
        )

    if len(client.basket.items) > 0:
        raise db.RejectedCommand(
            f"CLIENT-DELETE - Client {client.name} has a non-empty"
            f" basket and cannot be deleted."
        )

    try:
        db.Session.delete(client)
    except sa.exc.SQLAlchemyError:
        raise db.FailedCommand(
            f"CLIENT-DELETE - SQL error while deleting client {client.name}."
        )
    else:
        db.Session.commit()
