# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import scoped_session
from sqlalchemy.exc import SQLAlchemyError

from dfacto.models import models
from dfacto.models import schemas

from .base import CRUDBase, CrudError


class CRUDClient(
    CRUDBase[models.Client, schemas.ClientCreate, schemas.ClientUpdate]
):
    def get_basket(self, dbsession: scoped_session, obj_id: int) -> Optional[models.Basket]:
        try:
            basket = dbsession.scalars(
                select(models.Basket).where(models.Basket.client_id == obj_id)
            ).first()
        except SQLAlchemyError as exc:
            raise CrudError from exc
        else:
            return basket

    def add_to_basket(
        self,
        dbsession: scoped_session,
        *,
        basket: models.Basket,
        service: models.Service,
        quantity: int = 1
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

    def remove_from_basket(
        self, dbsession: scoped_session, *, db_obj: models.Item
    ) -> None:
        db_obj.basket.raw_amount -= db_obj.raw_amount
        db_obj.basket.vat -= db_obj.vat
        db_obj.basket.net_amount -= db_obj.net_amount
        if db_obj.invoice_id is None:
            # Not used by an invoice: delete it.
            dbsession.delete(db_obj)
        else:
            # In use by an invoice, do not delete it, only dereferences the basket.
            db_obj.basket_id = None

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def update_item_quantity(
        self, dbsession: scoped_session, *, db_obj: models.Item, quantity: int
    ) -> None:
        db_obj.quantity = quantity
        prev_raw_amount = db_obj.raw_amount
        prev_vat = db_obj.vat
        prev_net_amount = db_obj.net_amount
        db_obj.raw_amount = raw_amount = db_obj.service.unit_price * quantity
        db_obj.vat = vat = db_obj.service.vat_rate.rate * raw_amount
        db_obj.net_amount = raw_amount + vat

        db_obj.basket.raw_amount += (db_obj.raw_amount - prev_raw_amount)
        db_obj.basket.vat += (db_obj.vat - prev_vat)
        db_obj.basket.net_amount += (db_obj.net_amount - prev_net_amount)

        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc

    def clear_basket(self, dbsession: scoped_session, *, db_obj: models.Basket) -> None:
        for item in db_obj.items:
            db_obj.raw_amount -= item.raw_amount
            db_obj.vat -= item.vat
            db_obj.net_amount -= item.net_amount
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


client = CRUDClient(models.Client)
