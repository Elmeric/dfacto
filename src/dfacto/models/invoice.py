# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from datetime import date
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc
import sqlalchemy.orm

from dfacto.models.basket import BasketModel
from dfacto.models.api.command import CommandResponse, CommandStatus
from dfacto.models.item import Item, ItemModel
from dfacto.models.models import InvoiceStatus, Basket, _Invoice, _Item
# from dfacto.models.api.api_v1.service import ServiceModel
from dfacto.models import api


@dataclass()
class Invoice:
    id: int
    code: str
    client_id: int
    content: list[Item]
    status: InvoiceStatus
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
class InvoiceModel:
    Session: sa.orm.scoped_session
    # service_model: ServiceModel
    item_model: ItemModel
    basket_model: BasketModel

    def get(self, invoice_id: int) -> Optional[Invoice]:
        invoice: Optional[_Invoice] = self.Session.get(_Invoice, invoice_id)
        if invoice is None:
            return

        content = [self.item_model.get(it.id) for it in invoice.items]
        return Invoice(
            invoice.id,
            invoice.code,
            invoice.client_id,
            content,
            invoice.status,
        )

    def list_all(self) -> list[Invoice]:
        return [
            Invoice(
                invoice.id,
                invoice.code,
                invoice.client_id,
                [self.item_model.get(it.id) for it in invoice.items],
                invoice.status,
            )
            for invoice in self.Session.scalars(sa.select(_Invoice)).all()
        ]

    def create_from_basket(
        self, basket_id: int, clear_basket: bool = True
    ) -> CommandResponse:
        bskt: Optional[Basket] = self.Session.get(Basket, basket_id)
        if bskt is None:
            return CommandResponse(
                CommandStatus.FAILED, f"INVOICE-CREATE - Basket {basket_id} not found."
            )

        if len(bskt.items) <= 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"INVOICE-CREATE - No items in basket of client {bskt.client.name}.",
            )

        created_at = date.today()
        invoice = _Invoice(
            date=created_at,
            due_date=created_at,
            raw_amount=bskt.raw_amount,
            vat=bskt.vat,
            net_amount=bskt.net_amount,
            status=InvoiceStatus.DRAFT,
        )
        invoice.client_id = bskt.client_id
        invoice.items = [it for it in bskt.items]
        self.Session.add(invoice)

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-CREATE - Cannot create invoice from basket"
                f" of client {bskt.client.name}: {exc}",
            )
        else:
            inv = Invoice(
                invoice.id,
                invoice.code,
                invoice.client_id,
                [self.item_model.get(it.id) for it in bskt.items],
                invoice.status,
            )
            inv.totalize()
            if clear_basket:
                self.basket_model.clear(basket_id)
            return CommandResponse(CommandStatus.COMPLETED)

    def add_item(
        self, invoice_id: int, service_id: int, quantity: int
    ) -> CommandResponse:
        invoice: Optional[_Invoice] = self.Session.get(_Invoice, invoice_id)
        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-ADD-ITEM - Invoice {invoice_id} not found.",
            )

        serv = api.service.get(service_id)
        # serv = self.service_model.get(service_id)
        if serv is None or quantity <= 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"INVOICE-ADD-ITEM - An item shall refer to a strictly"
                f" positive quantity and a service.",
            )

        if invoice.status != InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"INVOICE-ADD-ITEM - Cannot add items to a non-draft invoice.",
            )

        item = _Item(quantity=quantity, service_id=service_id)
        item.raw_amount = raw_amount = serv.unit_price * quantity
        item.vat = vat = raw_amount * serv.vat_rate.rate / 100
        item.net_amount = raw_amount + vat
        item.invoice_id = invoice_id
        self.Session.add(item)

        invoice.raw_amount += item.raw_amount
        invoice.vat += item.vat
        invoice.net_amount += item.net_amount

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-ADD-ITEM - Cannot add service {item.service.name}"
                f" to invoice of client {invoice.client.name}: {exc}",
            )

        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def update_item(
        self,
        invoice_id: int,
        item_id: int,
        service_id: Optional[int] = None,
        quantity: Optional[int] = None,
    ) -> CommandResponse:
        invoice: Optional[_Invoice] = self.Session.get(_Invoice, invoice_id)
        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-UPDATE-ITEM - Invoice {invoice_id} not found.",
            )

        if invoice.status != InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"INVOICE-UPDATE-ITEM - Cannot change items of a non-draft invoice.",
            )

        item: Optional[_Item] = self.Session.get(_Item, item_id)
        if item is None:
            return CommandResponse(
                CommandStatus.FAILED, f"INVOICE-UPDATE-ITEM - Item {item_id} not found."
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
            serv = api.service.get(service_id)
            # serv = self.service_model.get(service_id)
            if serv is None:
                return CommandResponse(
                    CommandStatus.REJECTED,
                    f"INVOICE-UPDATE-ITEM - Service {service_id} not found.",
                )
            raw_amount = item.raw_amount = serv.unit_price * quantity
            vat = item.vat = serv.vat_rate.rate * raw_amount
            item.net_amount = raw_amount + vat

        invoice.raw_amount += item.raw_amount
        invoice.vat += item.vat
        invoice.net_amount += item.net_amount
        return CommandResponse(CommandStatus.COMPLETED)

    def remove_item(self, item_id: int) -> CommandResponse:
        it: Optional[_Item] = self.Session.get(_Item, item_id)
        if it is None:
            return CommandResponse(
                CommandStatus.FAILED, f"INVOICE-REMOVE-ITEM - Item {item_id} not found."
            )

        if it.invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-REMOVE-ITEM - Item {item_id} not in an invoice.",
            )

        if it.invoice.status != InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"INVOICE-REMOVE-ITEM - Only DRAFT invoice can be edited.",
            )

        it.invoice.raw_amount -= it.raw_amount
        it.invoice.vat -= it.vat
        it.invoice.net_amount -= it.net_amount
        if it.basket_id is None:
            # Not used by a basket: delete it.
            self.Session.delete(it)
        else:
            # In use by basket, do not delete it, only dereferences the invoice.
            it.invoice_id = None

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-REMOVE-ITEM - Cannot remove item {it.service.name}"
                f" from invoice {it.invoice.code} of client {it.invoice.client.name}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def update_status(self, invoice_id: int, status: InvoiceStatus) -> CommandResponse:
        invoice: Optional[_Invoice] = self.Session.get(_Invoice, invoice_id)
        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-STATUS - Invoice {invoice_id} not found.",
            )

        if status != invoice.status:
            if status == InvoiceStatus.DRAFT:
                return CommandResponse(
                    CommandStatus.REJECTED,
                    f"INVOICE-STATUS - Emitted invoice cannot be reset to DRAFT.",
                )
            invoice.status = status

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-STATUS - Cannot change invoice status"
                f" of {invoice_id} to {status}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)

    def delete(self, invoice_id: int) -> CommandResponse:
        invoice: Optional[_Invoice] = self.Session.get(_Invoice, invoice_id)
        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-DELETE - Invoice {invoice_id} not found.",
            )

        if invoice.status != InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"INVOICE-DELETE - Only DRAFT invoice can be deleted.",
            )

        for it in invoice.items:
            invoice.raw_amount -= it.raw_amount
            invoice.vat -= it.vat
            invoice.net_amount -= it.net_amount
            if it.basket_id is None:
                # Not used by a basket: delete it.
                self.Session.delete(it)
            else:
                # In use by basket, do not delete it, only dereferences the invoice.
                it.invoice_id = None

        self.Session.delete(invoice)

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-DELETE - SQL error while deleting draft invoice {invoice_id}"
                f" of client {invoice.client.name}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)
