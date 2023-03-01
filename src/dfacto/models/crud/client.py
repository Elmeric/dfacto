# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Optional, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models import models, schemas
from dfacto.models.util import Period

from .base import CRUDBase, CrudError, CrudIntegrityError


class CRUDClient(CRUDBase[models.Client, schemas.ClientCreate, schemas.ClientUpdate]):
    def get_active(self, dbsession: scoped_session) -> list[models.Client]:
        try:
            clients = cast(
                list[models.Client],
                dbsession.scalars(
                    select(models.Client).where(models.Client.is_active == True)
                ).all(),
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return clients

    def get_basket(
        self, dbsession: scoped_session, obj_id: int
    ) -> Optional[models.Basket]:
        try:
            basket = dbsession.scalars(
                select(models.Basket).where(models.Basket.client_id == obj_id)
            ).first()
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return basket

    def get_invoices(
        self, dbsession: scoped_session, obj_id: int, *, period: Period
    ) -> list[models.Invoice]:
        try:
            invoices = cast(
                list[models.Invoice],
                dbsession.scalars(
                    select(models.Invoice)
                    .join(models.StatusLog)
                    .where(models.Invoice.client_id == obj_id)
                    .where(models.StatusLog.status == models.InvoiceStatus.DRAFT)
                    .where(models.StatusLog.from_ >= period.start_time)
                    .where(models.StatusLog.from_ <= period.end_time)
                ).all(),
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return invoices

    def get_invoices_by_status(
        self,
        dbsession: scoped_session,
        obj_id: int,
        *,
        status: models.InvoiceStatus,
        period: Period,
    ) -> list[models.Invoice]:
        try:
            invoices = cast(
                list[models.Invoice],
                dbsession.scalars(
                    select(models.Invoice)
                    .join(models.StatusLog)
                    .where(models.Invoice.client_id == obj_id)
                    .where(models.StatusLog.status == status)
                    .where(models.StatusLog.from_ >= period.start_time)
                    .where(models.StatusLog.from_ <= period.end_time)
                ).all(),
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return invoices

    def add_to_basket(
        self,
        dbsession: scoped_session,
        *,
        basket: models.Basket,
        service: models.Service,
        quantity: int = 1,
    ) -> models.Item:
        raw_amount = service.unit_price * quantity
        vat = raw_amount * service.vat_rate.rate / 100
        net_amount = raw_amount + vat
        item_ = models.Item(
            raw_amount=raw_amount,
            vat=vat,
            net_amount=net_amount,
            service_id=service.id,
            quantity=quantity,
        )
        item_.basket_id = basket.id
        dbsession.add(item_)
        basket.raw_amount += raw_amount
        basket.vat += vat
        basket.net_amount += net_amount

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
        else:
            dbsession.refresh(item_)
            return item_

    def update_item_quantity(
        self, dbsession: scoped_session, *, item: models.Item, quantity: int
    ) -> None:
        # heck that the quantity is actually changed
        if item.quantity == quantity:
            return

        item.quantity = quantity
        prev_raw_amount = item.raw_amount
        prev_vat = item.vat
        prev_net_amount = item.net_amount
        item.raw_amount = new_raw_amount = item.service.unit_price * quantity
        item.vat = new_vat = item.service.vat_rate.rate * new_raw_amount / 100
        item.net_amount = new_net_amount = new_raw_amount + new_vat

        if item.basket_id is not None:
            item.basket.raw_amount += new_raw_amount - prev_raw_amount
            item.basket.vat += new_vat - prev_vat
            item.basket.net_amount += new_net_amount - prev_net_amount

        if item.invoice_id is not None:
            item.invoice.raw_amount += new_raw_amount - prev_raw_amount
            item.invoice.vat += new_vat - prev_vat

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def remove_item(self, dbsession: scoped_session, *, item: models.Item) -> None:
        # Check that item is in the basket or an invoice but not in both
        basket_id = item.basket_id
        invoice_id = item.invoice_id
        assert basket_id is not None or invoice_id is not None
        assert basket_id is None or invoice_id is None

        if basket_id is None:
            self._remove_item_from_invoice(dbsession, item)
        if invoice_id is None:
            self._remove_item_from_basket(dbsession, item)

    def _remove_item_from_basket(
        self, dbsession: scoped_session, item: models.Item
    ) -> None:
        assert item.invoice_id is None
        item.basket.raw_amount -= item.raw_amount
        item.basket.vat -= item.vat
        item.basket.net_amount -= item.net_amount
        dbsession.delete(item)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def _remove_item_from_invoice(
        self, dbsession: scoped_session, item: models.Item
    ) -> None:
        assert item.basket_id is None
        item.invoice.raw_amount -= item.raw_amount
        item.invoice.vat -= item.vat
        dbsession.delete(item)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def clear_basket(self, dbsession: scoped_session, *, basket: models.Basket) -> None:
        basket.raw_amount = 0.0
        basket.vat = 0.0
        basket.net_amount = 0.0
        for item in basket.items:
            if item.invoice_id is None:
                # Not used by an invoice: delete it.
                dbsession.delete(item)
            else:
                # In use by an invoice, do not delete it, only dereferences the basket.
                item.basket_id = None

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def delete(self, dbsession: scoped_session, *, db_obj: models.Client) -> None:
        assert (
            not db_obj.has_emitted_invoices
        ), "Cannot delete client with non-draft invoices"

        for item in db_obj.basket.items:
            if item.invoice_id is None:
                # Not used by an invoice: delete it.
                dbsession.delete(item)
            else:
                # In use by an invoice, do not delete it, only dereferences the basket.
                item.basket_id = None
        for invoice in db_obj.invoices:
            for item in invoice.items:
                if item.basket_id is None:
                    # Not used by a basket: delete it.
                    dbsession.delete(item)
                else:
                    # In use by a basket, do not delete it, only dereferences the invoice.
                    item.invoice_id = None
            dbsession.delete(invoice)
        dbsession.delete(db_obj.basket)
        dbsession.delete(db_obj)
        try:
            dbsession.commit()
        except IntegrityError as exc:
            dbsession.rollback()
            raise CrudIntegrityError() from exc
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc


client = CRUDClient(models.Client)
