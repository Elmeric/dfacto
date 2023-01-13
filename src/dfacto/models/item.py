# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc

from dfacto.models import db, model, service


@dataclass()
class Item:
    id: int
    raw_amount: float
    vat: float
    net_amount: float
    service: service.Service
    quantity: int = 1


def get(item_id: Optional[int] = None) -> Item:
    item: Optional[model._Item] = db.Session.get(model._Item, item_id)
    if item is None:
        raise db.FailedCommand(f"ITEM-GET - Item {item_id} not found.")
    return Item(
        item.id,
        item.raw_amount,
        item.vat,
        item.net_amount,
        service.get(item.service.id),
        item.quantity,
    )


def list_all() -> list[Item]:
    return [
        Item(
            item.id,
            item.raw_amount,
            item.vat,
            item.net_amount,
            service.get(item.service.id),
            item.quantity,
        )
        for item in db.Session.scalars(sa.select(model._Item)).all()
    ]


def add(
    service_id: int,
    quantity: int = 1,
    basket_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
) -> Item:
    if basket_id is None and invoice_id is None:
        raise db.RejectedCommand(
            f"ITEM-ADD - An item shall be associated to a basket or an invoice."
        )

    serv = service.get(service_id)
    if serv is None or quantity <= 0:
        raise db.RejectedCommand(
            f"ITEM-ADD - An item shall refer to a strictly positive quantity"
            f" and a service."
        )

    if invoice_id is not None:
        invoice = db.Session.get(model.Invoice, invoice_id)
        if invoice.status != model.InvoiceStatus.DRAFT:
            raise db.RejectedCommand(
                f"ITEM-ADD - Cannot add items to a non-draft invoice."
            )

    item = model._Item(quantity=quantity, service_id=service_id)
    item.basket_id = basket_id
    item.invoice_id = invoice_id
    db.Session.add(item)

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"ITEM-ADD - Cannot add item {serv.name}, {quantity}: {exc}"
        )
    else:
        return Item(
            item.id,
            item.raw_amount,
            item.vat,
            item.net_amount,
            service.get(item.service.id),
            item.quantity,
        )


def update(
    item_id: int,
    service_id: Optional[int] = None,
    quantity: Optional[int] = None,
) -> Item:
    item: model._Item = db.Session.get(model._Item, item_id)
    if item is None:
        raise db.RejectedCommand(f"ITEM-UPDATE - Item {item_id} not found.")

    invoice = item.invoice
    if invoice is not None and invoice.status != model.InvoiceStatus.DRAFT:
        raise db.RejectedCommand(
            f"ITEM-UPDATE - Cannot change items of a non-draft invoice."
        )

    update_needed = True

    if service_id is None and quantity is None:
        update_needed = False

    if service_id is not None:
        if service_id == item.service_id:
            update_needed = False
        item.service_id = service_id

    if quantity is not None:
        if quantity == item.quantity:
            update_needed = False
        item.quantity = quantity

    if update_needed:
        serv = service.get(service_id)
        if serv is None:
            raise db.RejectedCommand(f"ITEM-UPDATE - Service {service_id} not found.")
        raw_amount = item.raw_amount = serv.unit_price * quantity
        vat = item.vat = serv.vat_rate * raw_amount
        item.net_amount = raw_amount + vat

        try:
            db.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            db.Session.rollback()
            raise db.FailedCommand(
                f"ITEM-UPDATE - Cannot update item {serv.name}, {quantity}: {exc}"
            )
        else:
            return Item(
                item.id,
                item.raw_amount,
                item.vat,
                item.net_amount,
                service.get(item.service.id),
                item.quantity,
            )

    return get(item_id)


def delete(item_id: int) -> None:
    try:
        db.Session.execute(sa.delete(model._Item).where(model._Item.id == item_id))
    except sa.exc.SQLAlchemyError:
        raise db.FailedCommand(
            f"ITEM_DELETE - Item with id {item_id} is used"
            f" by at least one client's basket or invoice!"
        )
    else:
        db.Session.commit()
