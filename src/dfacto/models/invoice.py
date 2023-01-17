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

from dfacto.models import basket, db, item, model


@dataclass()
class Invoice:
    id: int
    code: str
    client_id: int
    content: list[item.Item]
    status: model.InvoiceStatus
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


def get(invoice_id: int) -> Invoice:
    invoice: Optional[model._Invoice] = db.Session.get(model._Invoice, invoice_id)
    if invoice is None:
        raise db.FailedCommand(f"INVOICE-GET - Invoice {invoice_id} not found.")

    content = [item.get(it.id) for it in invoice.items]
    return Invoice(
        invoice.id,
        invoice.code,
        invoice.client_id,
        content,
        model.InvoiceStatus[invoice.status],
    )


def list_all() -> list[Invoice]:
    return [
        Invoice(
            invoice.id,
            invoice.code,
            invoice.client_id,
            [item.get(it.id) for it in invoice.items],
            model.InvoiceStatus[invoice.status],
        )
        for invoice in db.Session.scalars(sa.select(model._Invoice)).all()
    ]


def create_from_basket(basket_id: int, clear_basket: bool = True) -> Invoice:
    bskt: Optional[model._Basket] = db.Session.get(model._Basket, basket_id)
    if bskt is None:
        raise db.FailedCommand(f"INVOICE-CREATE - Basket {basket_id} not found.")

    if len(bskt.items) <= 0:
        raise db.RejectedCommand(
            f"INVOICE-CREATE - No items in basket of client {bskt.client.name}."
        )

    created_at = date.today()
    invoice = model._Invoice(
        date=created_at,
        due_date=created_at,
        raw_amount=bskt.raw_amount,
        vat=bskt.vat,
        net_amount=bskt.net_amount,
        status=model.InvoiceStatus.DRAFT,
    )
    invoice.client_id = bskt.client_id
    invoice.items = [it for it in bskt.items]
    db.Session.add(invoice)

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"INVOICE-CREATE - Cannot create invoice from basket"
            f" of client {bskt.client.name}: {exc}"
        )
    else:
        inv = Invoice(
            invoice.id,
            invoice.code,
            invoice.client_id,
            [item.get(it.id) for it in bskt.items],
            invoice.status,
        )
        inv.totalize()
        if clear_basket:
            basket.clear(basket_id)
        return inv


def add_item(invoice_id: int, service_id: int, quantity: int) -> item.Item:
    invoice: Optional[model._Invoice] = db.Session.get(model._Invoice, invoice_id)
    if invoice is None:
        raise db.FailedCommand(f"INVOICE-ADD-ITEM - Invoice {invoice_id} not found.")

    it = item.add(service_id, quantity, invoice_id=invoice_id)
    invoice.raw_amount += it.raw_amount
    invoice.vat += it.vat
    invoice.net_amount += it.net_amount

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"INVOICE-ADD-ITEM - Cannot add service {it.service.name}"
            f" to invoice of client {invoice.client.name}: {exc}"
        )
    else:
        return it


def update_item(
    invoice_id: int,
    item_id: int,
    service_id: Optional[int] = None,
    quantity: Optional[int] = None,
) -> item.Item:
    invoice: Optional[model._Invoice] = db.Session.get(model._Invoice, invoice_id)
    if invoice is None:
        raise db.FailedCommand(f"INVOICE-UPDATE-ITEM - Invoice {invoice_id} not found.")

    it = item.update(item_id, service_id, quantity)
    invoice.raw_amount += it.raw_amount
    invoice.vat += it.vat
    invoice.net_amount += it.net_amount
    return it


def remove_item(item_id: int) -> None:
    it: Optional[model._Item] = db.Session.get(model._Item, item_id)
    if it is None:
        raise db.FailedCommand(f"INVOICE-REMOVE-ITEM - Item {item_id} not found.")

    if it.invoice is None:
        raise db.FailedCommand(
            f"INVOICE-REMOVE-ITEM - Item {item_id} not in an invoice."
        )

    if it.invoice.status != model.InvoiceStatus.DRAFT:
        raise db.RejectedCommand(
            f"INVOICE-REMOVE-ITEM - Only DRAFT invoice can be edited."
        )

    it.invoice.raw_amount -= it.raw_amount
    it.invoice.vat -= it.vat
    it.invoice.net_amount -= it.net_amount
    if it.basket_id is None:
        # Not used by a basket: delete it.
        db.Session.delete(it)
    else:
        # In use by basket, do not delete it, only dereferences the invoice.
        it.invoice_id = None

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"INVOICE-REMOVE-ITEM - Cannot remove item {it.service.name}"
            f" from invoice {it.invoice.code} of client {it.invoice.client.name}: {exc}"
        )


def update_status(invoice_id: int, status: model.InvoiceStatus) -> None:
    invoice: Optional[model._Invoice] = db.Session.get(model._Invoice, invoice_id)
    if invoice is None:
        raise db.FailedCommand(f"INVOICE-STATUS - Invoice {invoice_id} not found.")

    if status != invoice.status:
        if status == model.InvoiceStatus.DRAFT:
            raise db.RejectedCommand(
                f"INVOICE-STATUS - Emitted invoice cannot be reset to DRAFT."
            )
        invoice.status = status

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"INVOICE-STATUS - Cannot change invoice status"
            f" of {invoice_id} to {status}: {exc}"
        )


def delete(invoice_id: int) -> None:
    invoice: Optional[model._Invoice] = db.Session.get(model._Invoice, invoice_id)
    if invoice is None:
        raise db.FailedCommand(f"INVOICE-DELETE - Invoice {invoice_id} not found.")

    if invoice.status != model.InvoiceStatus.DRAFT:
        raise db.RejectedCommand(f"INVOICE-DELETE - Only DRAFT invoice can be deleted.")

    for it in invoice.items:
        invoice.raw_amount -= it.raw_amount
        invoice.vat -= it.vat
        invoice.net_amount -= it.net_amount
        if it.basket_id is None:
            # Not used by a basket: delete it.
            db.Session.delete(it)
        else:
            # In use by basket, do not delete it, only dereferences the invoice.
            it.invoice_id = None

    db.Session.delete(invoice)

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"INVOICE-DELETE - SQL error while deleting draft invoice {invoice_id}"
            f" of client {invoice.client.name}: {exc}"
        )
