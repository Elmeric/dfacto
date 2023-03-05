# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import datetime

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, scoped_session

from dfacto.models import models, schemas

from .base import CRUDBase, CrudError


class CRUDInvoice(
    CRUDBase[models.Invoice, schemas.InvoiceCreate, schemas.InvoiceUpdate]
):
    def create(
        self, dbsession: scoped_session[Session], *, obj_in: schemas.InvoiceCreate
    ) -> models.Invoice:
        obj_in_data = obj_in.flatten()
        db_obj = self.model(**obj_in_data)
        dbsession.add(db_obj)
        dbsession.flush([db_obj])

        now = datetime.now()
        # dbsession.execute(
        #     update(models.StatusLog)
        #         .where(models.StatusLog.to == None)
        #         .values(to=now)
        # )
        log = models.StatusLog(
            invoice_id=db_obj.id, from_=now, to=None, status=models.InvoiceStatus.DRAFT
        )
        dbsession.add(log)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
        else:
            dbsession.refresh(db_obj)
            return db_obj

    def invoice_from_basket(
        self,
        dbsession: scoped_session[Session],
        basket: models.Basket,
        *,
        clear_basket: bool = True,
    ) -> models.Invoice:
        db_obj = models.Invoice(
            client_id=basket.client_id,
            raw_amount=basket.raw_amount,
            vat=basket.vat,
            status=models.InvoiceStatus.DRAFT,
        )
        for item in basket.items:
            db_obj.items.append(item)
            if clear_basket:
                basket.raw_amount -= item.raw_amount
                basket.vat -= item.vat
                item.basket_id = None
        dbsession.add(db_obj)
        dbsession.flush([db_obj])

        now = datetime.now()
        log = models.StatusLog(
            invoice_id=db_obj.id, from_=now, to=None, status=models.InvoiceStatus.DRAFT
        )
        dbsession.add(log)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
        else:
            dbsession.refresh(db_obj)
            return db_obj

    def add_item(
        self,
        dbsession: scoped_session[Session],
        *,
        invoice_: models.Invoice,
        service: models.Service,
        quantity: int = 1,
    ) -> models.Item:
        assert (
            invoice_.status is models.InvoiceStatus.DRAFT
        ), "Cannot add items to a non-draft invoice."

        raw_amount = service.unit_price * quantity
        vat = raw_amount * service.vat_rate.rate / 100
        item_ = models.Item(
            raw_amount=raw_amount,
            vat=vat,
            service_id=service.id,
            quantity=quantity,
        )
        item_.invoice_id = invoice_.id
        dbsession.add(item_)
        invoice_.raw_amount += raw_amount
        invoice_.vat += vat

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
        else:
            dbsession.refresh(item_)
            return item_

    def clear_invoice(
        self, dbsession: scoped_session[Session], *, invoice_: models.Invoice
    ) -> None:
        assert (
            invoice_.status is models.InvoiceStatus.DRAFT
        ), "Cannot clear a non-draft invoice."
        self._clear_or_delete(dbsession, invoice_, clear_only=True)

    def delete_invoice(
        self,
        dbsession: scoped_session[Session],
        *,
        invoice_: models.Invoice,
    ) -> None:
        assert (
            invoice_.status is models.InvoiceStatus.DRAFT
        ), "Cannot delete a non-draft invoice."
        self._clear_or_delete(dbsession, invoice_, clear_only=False)

    def _clear_or_delete(
        self,
        dbsession: scoped_session[Session],
        invoice_: models.Invoice,
        clear_only: bool = False,
    ) -> None:
        # In both cases, invoice shall be emptied
        for item in invoice_.items:
            if item.basket_id is None:
                # Not used by a basket: delete it.
                dbsession.delete(item)
            else:
                # In use by a basket, do not delete it, only dereferences the invoice.
                item.invoice_id = None
        if clear_only:
            invoice_.raw_amount = 0.0
            invoice_.vat = 0.0
        else:
            dbsession.delete(invoice_)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def cancel_invoice(
        self, dbsession: scoped_session[Session], *, invoice_: models.Invoice
    ) -> None:
        assert invoice_.status in (
            models.InvoiceStatus.EMITTED,
            models.InvoiceStatus.REMINDED,
        ), "Only emitted invoices may be cancelled."

        now = datetime.now()
        invoice_.status = models.InvoiceStatus.CANCELLED
        dbsession.execute(
            update(models.StatusLog)
            .where(models.StatusLog.invoice_id == invoice_.id)
            .where(models.StatusLog.to == None)
            .values(to=now)
        )
        log = models.StatusLog(
            invoice_id=invoice_.id,
            from_=now,
            to=None,
            status=models.InvoiceStatus.CANCELLED,
        )
        dbsession.add(log)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def mark_as(
        self,
        dbsession: scoped_session[Session],
        *,
        invoice_: models.Invoice,
        status: models.InvoiceStatus,
    ) -> None:
        assert status in (
            models.InvoiceStatus.EMITTED,
            models.InvoiceStatus.REMINDED,
            models.InvoiceStatus.PAID,
            models.InvoiceStatus.CANCELLED,
        )

        now = datetime.now()
        invoice_.status = status
        dbsession.execute(
            update(models.StatusLog)
            .where(models.StatusLog.invoice_id == invoice_.id)
            .where(models.StatusLog.to == None)
            .values(to=now)
        )
        log = models.StatusLog(
            invoice_id=invoice_.id, from_=now, to=None, status=status
        )
        dbsession.add(log)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc


invoice = CRUDInvoice(models.Invoice)
