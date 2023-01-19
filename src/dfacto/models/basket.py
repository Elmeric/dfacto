# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc
import sqlalchemy.orm

from dfacto.models.item import Item, ItemModel
from dfacto.models.model import (
    CommandReport,
    CommandStatus,
    InvoiceStatus,
    _Basket,
    _Item,
)
from dfacto.models.service import ServiceModel


@dataclass()
class Basket:
    id: int
    client_id: int
    content: list[Item]
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


@dataclass()
class BasketModel:
    Session: sa.orm.scoped_session
    service_model: ServiceModel
    item_model: ItemModel

    def get(self, basket_id: int) -> Optional[Basket]:
        basket: Optional[_Basket] = self.Session.get(_Basket, basket_id)
        if basket is None:
            return

        content = [self.item_model.get(it.id) for it in basket.items]
        return Basket(
            basket.id,
            basket.client_id,
            content,
        )

    def list_all(self) -> list[Basket]:
        return [
            Basket(
                basket.id,
                basket.client_id,
                [self.item_model.get(it.id) for it in basket.items],
            )
            for basket in self.Session.scalars(sa.select(_Basket)).all()
        ]

    def add_item(self, basket_id: int, service_id: int, quantity: int) -> CommandReport:
        basket: Optional[_Basket] = self.Session.get(_Basket, basket_id)
        if basket is None:
            return CommandReport(
                CommandStatus.FAILED, f"BASKET-ADD-ITEM - Basket {basket_id} not found."
            )

        serv = self.service_model.get(service_id)
        if serv is None or quantity <= 0:
            return CommandReport(
                CommandStatus.REJECTED,
                f"BASKET-ADD-ITEM - An item shall refer to a strictly positive quantity"
                f" and a service.",
            )

        item = _Item(quantity=quantity, service_id=service_id)
        item.raw_amount = raw_amount = serv.unit_price * quantity
        item.vat = vat = raw_amount * serv.vat_rate.rate / 100
        item.net_amount = raw_amount + vat
        item.basket_id = basket_id
        self.Session.add(item)

        basket.raw_amount += item.raw_amount
        basket.vat += item.vat
        basket.net_amount += item.net_amount

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandReport(
                CommandStatus.FAILED,
                f"BASKET-ADD-ITEM - Cannot add service {item.service.name}"
                f" to basket of client {basket.client.name}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)

    def update_item(
        self,
        basket_id: int,
        item_id: int,
        service_id: Optional[int] = None,
        quantity: Optional[int] = None,
    ) -> CommandReport:
        basket: Optional[_Basket] = self.Session.get(_Basket, basket_id)
        if basket is None:
            return CommandReport(
                CommandStatus.FAILED,
                f"BASKET-UPDATE-ITEM - Basket {basket_id} not found.",
            )

        item: Optional[_Item] = self.Session.get(_Item, item_id)
        if item is None:
            return CommandReport(
                CommandStatus.FAILED, f"BASKET-UPDATE-ITEM - Item {item_id} not found."
            )

        invoice = item.invoice
        if invoice is not None and invoice.status != InvoiceStatus.DRAFT:
            return CommandReport(
                CommandStatus.REJECTED,
                f"BASKET-UPDATE-ITEM - Cannot change items of a non-draft invoice.",
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
            serv = self.service_model.get(service_id)
            if serv is None:
                return CommandReport(
                    CommandStatus.REJECTED,
                    f"BASKET-UPDATE-ITEM - Service {service_id} not found.",
                )
            raw_amount = item.raw_amount = serv.unit_price * quantity
            vat = item.vat = serv.vat_rate.rate * raw_amount
            item.net_amount = raw_amount + vat

        basket.raw_amount += item.raw_amount
        basket.vat += item.vat
        basket.net_amount += item.net_amount

        return CommandReport(CommandStatus.COMPLETED)

    def remove_item(self, item_id: int) -> CommandReport:
        it: Optional[_Item] = self.Session.get(_Item, item_id)
        if it is None:
            return CommandReport(
                CommandStatus.FAILED, f"BASKET-REMOVE-ITEM - Item {item_id} not found."
            )

        it.basket.raw_amount -= it.raw_amount
        it.basket.vat -= it.vat
        it.basket.net_amount -= it.net_amount
        if it.invoice_id is None:
            # Not used by an invoice: delete it.
            self.Session.delete(it)
        else:
            # In use by an invoice, do not delete it, only dereferences the basket.
            it.basket_id = None

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandReport(
                CommandStatus.FAILED,
                f"BASKET-REMOVE-ITEM - Cannot remove item {it.service.name}"
                f" from basket of client {it.basket.client.name}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)

    def clear(self, basket_id: int) -> CommandReport:
        basket: Optional[_Basket] = self.Session.get(_Basket, basket_id)
        if basket is None:
            return CommandReport(
                CommandStatus.FAILED, f"BASKET-CLEAR - Basket {basket_id} not found."
            )

        for it in basket.items:
            basket.raw_amount -= it.raw_amount
            basket.vat -= it.vat
            basket.net_amount -= it.net_amount
            if it.invoice_id is None:
                # Not used by an invoice: delete it.
                self.Session.delete(it)
            else:
                # In use by an invoice, do not delete it, only dereferences the basket.
                it.basket_id = None

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandReport(
                CommandStatus.FAILED,
                f"BASKET-CLEAR - Cannot clear basket of client {basket.client.name}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)
