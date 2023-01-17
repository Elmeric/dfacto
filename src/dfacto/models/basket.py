# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc

from dfacto.models import db, item, model


@dataclass()
class Basket:
    id: int
    client_id: int
    content: list[item.Item]
    _raw_amount: Optional[float] = None
    _vat: Optional[float] = None
    _net_amount: Optional[float] = None

    @property
    def raw_amount(self) -> float:
        if self._raw_amount is None:
            self.totalize()
        return self._raw_amount

    @property
    def vat(self) -> float:
        if self._vat is None:
            self.totalize()
        return self._vat

    @property
    def net_amount(self) -> float:
        if self._net_amount is None:
            self.totalize()
        return self._net_amount

    def totalize(self):
        raw_amount = vat = 0
        for it in self.content:
            raw_amount += it.raw_amount
            vat += it.vat
        self._raw_amount = raw_amount
        self._vat = vat
        self._net_amount = raw_amount + vat


def get(basket_id: int) -> Basket:
    basket: Optional[model._Basket] = db.Session.get(model._Basket, basket_id)
    if basket is None:
        raise db.FailedCommand(f"BASKET-GET - Basket {basket_id} not found.")

    content = [item.get(it.id) for it in basket.items]
    return Basket(
        basket.id,
        basket.client_id,
        content,
    )


def list_all() -> list[Basket]:
    return [
        Basket(
            basket.id,
            basket.client_id,
            [item.get(it.id) for it in basket.items],
        )
        for basket in db.Session.scalars(sa.select(model._Basket)).all()
    ]


def add_item(basket_id: int, service_id: int, quantity: int) -> item.Item:
    basket: Optional[model._Basket] = db.Session.get(model._Basket, basket_id)
    if basket is None:
        raise db.FailedCommand(f"BASKET-ADD-ITEM - Basket {basket_id} not found.")

    it = item.add(service_id, quantity, basket_id=basket_id)
    basket.raw_amount += it.raw_amount
    basket.vat += it.vat
    basket.net_amount += it.net_amount

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"BASKET-ADD-ITEM - Cannot add service {it.service.name}"
            f" to basket of client {basket.client.name}: {exc}"
        )
    else:
        return it


def update_item(
    basket_id: int,
    item_id: int,
    service_id: Optional[int] = None,
    quantity: Optional[int] = None,
) -> item.Item:
    basket: Optional[model._Basket] = db.Session.get(model._Basket, basket_id)
    if basket is None:
        raise db.FailedCommand(f"BASKET-UPDATE-ITEM - Basket {basket_id} not found.")

    it = item.update(item_id, service_id, quantity)
    basket.raw_amount += it.raw_amount
    basket.vat += it.vat
    basket.net_amount += it.net_amount
    return it


def remove_item(item_id: int) -> None:
    it: Optional[model._Item] = db.Session.get(model._Item, item_id)
    if it is None:
        raise db.FailedCommand(f"BASKET-REMOVE-ITEM - Item {item_id} not found.")

    it.basket.raw_amount -= it.raw_amount
    it.basket.vat -= it.vat
    it.basket.net_amount -= it.net_amount
    if it.invoice_id is None:
        # Not used by an invoice: delete it.
        db.Session.delete(it)
    else:
        # In use by an invoice, do not delete it, only dereferences the basket.
        it.basket_id = None

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"BASKET-REMOVE-ITEM - Cannot remove item {it.service.name}"
            f" from basket of client {it.basket.client.name}: {exc}"
        )


def clear(basket_id: int) -> None:
    basket: Optional[model._Basket] = db.Session.get(model._Basket, basket_id)
    if basket is None:
        raise db.FailedCommand(f"BASKET-CLEAR - Basket {basket_id} not found.")

    for it in basket.items:
        basket.raw_amount -= it.raw_amount
        basket.vat -= it.vat
        basket.net_amount -= it.net_amount
        if it.invoice_id is None:
            # Not used by an invoice: delete it.
            db.Session.delete(it)
        else:
            # In use by an invoice, do not delete it, only dereferences the basket.
            it.basket_id = None

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"BASKET-CLEAR - Cannot clear basket of client {basket.client.name}: {exc}"
        )
