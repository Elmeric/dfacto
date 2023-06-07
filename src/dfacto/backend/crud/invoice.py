# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import update, select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import models, schemas

from .base import CRUDBase, CrudError

if TYPE_CHECKING:
    from dfacto.backend.util import DatetimeRange


class CRUDInvoice(
    CRUDBase[models.Invoice, schemas.InvoiceCreate, schemas.InvoiceUpdate]
):
    def create(
        self, dbsession: Session, *, obj_in: schemas.InvoiceCreate
    ) -> models.Invoice:
        obj_in_data = obj_in.flatten()
        db_obj = self.model(**obj_in_data)
        dbsession.add(db_obj)
        dbsession.flush([db_obj])

        now = datetime.now().date()
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
        dbsession: Session,
        basket: models.Basket,
        *,
        clear_basket: bool = True,
    ) -> models.Invoice:
        db_obj = self.model(
            client_id=basket.client_id,
            status=models.InvoiceStatus.DRAFT,
        )
        item: models.Item
        with dbsession.no_autoflush:
            for item in basket.items:
                current_service: models.Service = item.current_service
                item.service_version = current_service.version
                db_obj.items.append(item)
                if clear_basket:
                    item.basket_id = None
        dbsession.add(db_obj)
        dbsession.flush([db_obj])

        now = datetime.now().date()
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

    def copy_in_basket(
        self,
        dbsession: Session,
        invoice_: models.Invoice,
        *,
        clear_basket: bool = True,
    ) -> None:
        client: models.Client = invoice_.client
        basket: models.Basket = client.basket

        if clear_basket:
            for item in basket.items:
                if item.invoice_id is None:
                    # Not used by an invoice: delete it.
                    dbsession.delete(item)
                else:
                    # In use by an invoice, do not delete it, only dereferences the basket.
                    item.basket_id = None

        item: models.Item
        for item in invoice_.items:
            item_copy = models.Item(
                service_id=item.service_id,
                service_version=item.current_service.version,
                quantity=item.quantity,
            )
            item_copy.basket_id = basket.id
            dbsession.add(item_copy)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def move_in_basket(
        self,
        dbsession: Session,
        invoice_: models.Invoice,
        *,
        clear_basket: bool = True,
    ) -> None:
        client: models.Client = invoice_.client
        basket: models.Basket = client.basket

        if clear_basket:
            for item in basket.items:
                if item.invoice_id is None:
                    # Not used by an invoice: delete it.
                    dbsession.delete(item)
                else:
                    # In use by an invoice, do not delete it, only dereferences the basket.
                    item.basket_id = None

        for item in invoice_.items:
            item.invoice_id = None
            item.basket_id = basket.id

        dbsession.delete(invoice_)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def add_item(
        self,
        dbsession: Session,
        *,
        invoice_: models.Invoice,
        service: models.Service,
        quantity: int = 1,
    ) -> models.Item:
        assert (
            invoice_.status is models.InvoiceStatus.DRAFT
        ), "Cannot add items to a non-draft invoice."

        item_ = models.Item(
            service_id=service.id,
            service_version=service.version,
            quantity=quantity,
        )
        item_.invoice_id = invoice_.id
        dbsession.add(item_)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
        else:
            dbsession.refresh(item_)
            return item_

    def clear_invoice(self, dbsession: Session, *, invoice_: models.Invoice) -> None:
        assert (
            invoice_.status is models.InvoiceStatus.DRAFT
        ), "Cannot clear a non-draft invoice."
        self._clear_or_delete(dbsession, invoice_, clear_only=True)

    def delete_invoice(
        self,
        dbsession: Session,
        *,
        invoice_: models.Invoice,
    ) -> None:
        assert (
            invoice_.status is models.InvoiceStatus.DRAFT
        ), "Cannot delete a non-draft invoice."
        self._clear_or_delete(dbsession, invoice_, clear_only=False)

    def _clear_or_delete(
        self,
        dbsession: Session,
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
            pass
        else:
            dbsession.delete(invoice_)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def cancel_invoice(self, dbsession: Session, *, invoice_: models.Invoice) -> None:
        assert invoice_.status in (
            models.InvoiceStatus.EMITTED,
            models.InvoiceStatus.REMINDED,
        ), "Only emitted invoices may be cancelled."

        now = datetime.now().date()
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
        dbsession: Session,
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

        now = datetime.now().date()
        current_status = invoice_.status
        if status is models.InvoiceStatus.REMINDED and current_status == status:
            # It is a new reminder, only changes from_ date of the last status log
            dbsession.execute(
                update(models.StatusLog)
                .where(models.StatusLog.invoice_id == invoice_.id)
                .where(models.StatusLog.to == None)
                .values(from_=now)
            )
        else:
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

    def get_status_history(
        self, dbsession: Session, *, invoice_id: int
    ) -> list[models.StatusLog]:
        try:
            status_log = cast(
                list[models.StatusLog],
                dbsession.scalars(
                    select(models.StatusLog)
                    .where(models.StatusLog.invoice_id == invoice_id)
                    .order_by(models.StatusLog.from_)
                ).all()
            )
        except SQLAlchemyError as exc:
            raise CrudError() from exc
        else:
            return status_log

    def set_status_history(
        self,
        dbsession: Session,
        *,
        invoice_: models.Invoice,
        log: dict[models.InvoiceStatus, "DatetimeRange"]
    ) -> None:
        for status, from_to in log.items():
            dbsession.execute(
                update(models.StatusLog)
                .where(models.StatusLog.invoice_id == invoice_.id)
                .where(models.StatusLog.status == status)
                .values(from_=from_to.from_, to=from_to.to)
            )
        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            raise CrudError() from exc

    def revert_status(
        self,
        dbsession: Session,
        *,
        invoice_: models.Invoice,
        status: models.InvoiceStatus,
    ) -> None:
        current_status = invoice_.status
        invoice_.status = status
        dbsession.execute(
            delete(models.StatusLog)
            .where(models.StatusLog.invoice_id == invoice_.id)
            .where(models.StatusLog.status == current_status)
        )
        dbsession.execute(
            update(models.StatusLog)
            .where(models.StatusLog.invoice_id == invoice_.id)
            .where(models.StatusLog.status == status)
            .values(to=None)
        )

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc


invoice = CRUDInvoice(models.Invoice)
