# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Optional, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import models, schemas
from dfacto.backend.util import Period

from .base import CRUDBase, CrudError, CrudIntegrityError


class CRUDClient(CRUDBase[models.Client, schemas.ClientCreate, schemas.ClientUpdate]):
    def get_active(self, dbsession: Session) -> list[models.Client]:
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

    def get_basket(self, dbsession: Session, obj_id: int) -> Optional[models.Basket]:
        try:
            basket = dbsession.scalars(
                select(models.Basket).where(models.Basket.client_id == obj_id)
            ).first()
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return basket

    def get_item_from_service(
        self, dbsession: Session, obj_id: int, *, service_id: int
    ) -> Optional[models.Item]:
        try:
            item = dbsession.scalars(
                select(models.Item)
                .join(models.Basket)
                .where(models.Item.service_id == service_id)
                .where(models.Basket.client_id == obj_id)
            ).first()
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return item

    def get_invoices(
        self, dbsession: Session, obj_id: int, *, period: Period
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
        dbsession: Session,
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
        dbsession: Session,
        *,
        basket: models.Basket,
        service: models.Service,
        quantity: int = 1,  # may be negative to decrease service quantity in basket
    ) -> models.Item:
        raw_amount = service.unit_price * quantity
        vat = raw_amount * service.vat_rate.rate / 100
        # Check if an item already exist in basket for this service
        try:
            item_ = cast(
                models.Item,
                dbsession.scalars(
                    select(models.Item)
                    .where(models.Item.basket_id == basket.id)
                    .where(models.Item.service_id == service.id)
                ).first(),
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            if item_ is None:
                # No item found: create it
                item_ = models.Item(
                    service_id=service.id,
                    quantity=quantity,
                )
                item_.basket_id = basket.id
                dbsession.add(item_)
            else:
                # Item found: update it
                item_.quantity += quantity

            try:
                dbsession.commit()
            except SQLAlchemyError as exc:
                dbsession.rollback()
                raise CrudError() from exc
            else:
                dbsession.refresh(item_)
                return item_

    def remove_from_basket(
        self,
        dbsession: Session,
        *,
        basket: models.Basket,
        service: models.Service,
    ) -> None:
        try:
            item_ = cast(
                models.Item,
                dbsession.scalars(
                    select(models.Item)
                    .where(models.Item.basket_id == basket.id)
                    .where(models.Item.service_id == service.id)
                ).first(),
            )
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            if item_ is None:
                return

            dbsession.delete(item_)

            try:
                dbsession.commit()
            except SQLAlchemyError as exc:
                dbsession.rollback()
                raise CrudError() from exc
            else:
                return

    def update_item_quantity(
        self, dbsession: Session, *, item: models.Item, quantity: int
    ) -> None:
        # Check that the quantity is actually changed
        if item.quantity == quantity:
            return

        if item.quantity == 0:
            self.remove_item(dbsession, item=item)
            return

        item.quantity = quantity

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def remove_item(self, dbsession: Session, *, item: models.Item) -> None:
        # Check that item is in the basket or an invoice but not in both
        basket_id = item.basket_id
        invoice_id = item.invoice_id
        assert basket_id is not None or invoice_id is not None
        assert basket_id is None or invoice_id is None

        if basket_id is None:
            self._remove_item_from_invoice(dbsession, item)
        if invoice_id is None:
            self._remove_item_from_basket(dbsession, item)

    def _remove_item_from_basket(self, dbsession: Session, item: models.Item) -> None:
        assert item.invoice_id is None
        dbsession.delete(item)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def _remove_item_from_invoice(self, dbsession: Session, item: models.Item) -> None:
        assert item.basket_id is None
        dbsession.delete(item)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def clear_basket(self, dbsession: Session, *, basket: models.Basket) -> None:
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

    def delete(self, dbsession: Session, *, db_obj: models.Client) -> None:
        assert (
            not db_obj.has_emitted_invoices
        ), "Cannot delete client with non-draft invoices"
        assert db_obj.basket is not None

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
