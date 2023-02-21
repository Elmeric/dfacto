# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from datetime import date, timedelta

from dfacto.models import models

from .base import BaseSchema
from .item import Item


@dataclass
class _InvoiceBase(BaseSchema):
    client_id: int
    raw_amount: float
    vat: float
    # net_amount: float
    date: date
    due_date: date
    status: models.InvoiceStatus


@dataclass
class _InvoiceDefaultsBase(BaseSchema):
    pass


@dataclass
class InvoiceCreate(_InvoiceBase):
    raw_amount: float = 0.0
    vat: float = 0.0
    # net_amount: float = 0.0
    date: date = date.today()
    due_date: date = date.today() + timedelta(30)
    status: models.InvoiceStatus = models.InvoiceStatus.DRAFT


@dataclass
class InvoiceUpdate(_InvoiceDefaultsBase):
    pass


@dataclass
class _InvoiceInDBBase(_InvoiceBase):
    id: int


# Additional properties to return from DB
@dataclass
class Invoice(_InvoiceInDBBase):
    items: list[Item]

    @property
    def code(self) -> str:
        return "FC" + str(self.id).zfill(10)

    @classmethod
    def from_orm(cls, orm_obj: models.Invoice) -> "Invoice":
        return cls(
            id=orm_obj.id,
            date=orm_obj.date,
            due_date=orm_obj.due_date,
            raw_amount=orm_obj.raw_amount,
            vat=orm_obj.vat,
            # net_amount=orm_obj.net_amount,
            status=orm_obj.status,
            items=[Item.from_orm(item) for item in orm_obj.items]
        )


# Additional properties stored in DB
@dataclass
class InvoiceInDB(_InvoiceInDBBase):
    client_id: int
