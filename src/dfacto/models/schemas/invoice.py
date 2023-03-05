# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, cast

from dfacto.models import db, models

from .base import BaseSchema
from .item import Item


@dataclass
class _InvoiceBase(BaseSchema):
    client_id: int


@dataclass
class _InvoiceDefaultsBase(BaseSchema):
    pass


@dataclass
class InvoiceCreate(_InvoiceBase):
    pass


@dataclass
class InvoiceUpdate(_InvoiceDefaultsBase):
    pass


@dataclass
class _InvoiceInDBBase(_InvoiceBase):
    id: int
    raw_amount: float
    vat: float
    status: models.InvoiceStatus


# Additional properties to return from DB
@dataclass
class StatusLog(BaseSchema):
    id: int
    status: models.InvoiceStatus
    from_: datetime
    to: Optional[datetime]
    invoice_id: int

    @classmethod
    def from_orm(cls, orm_obj: db.BaseModel) -> "StatusLog":
        obj = cast(models.StatusLog, orm_obj)
        return cls(
            id=obj.id,
            status=obj.status,
            from_=obj.from_,
            to=obj.to,
            invoice_id=obj.invoice.id,
        )


@dataclass
class Invoice(_InvoiceInDBBase):
    items: list[Item]
    status_log: list[StatusLog]

    @property
    def code(self) -> str:
        return "FC" + str(self.id).zfill(10)

    @property
    def net_amount(self) -> float:
        return self.raw_amount + self.vat

    @classmethod
    def from_orm(cls, orm_obj: db.BaseModel) -> "Invoice":
        obj = cast(models.Invoice, orm_obj)
        return cls(
            id=obj.id,
            raw_amount=obj.raw_amount,
            vat=obj.vat,
            status=obj.status,
            client_id=obj.client_id,
            items=[Item.from_orm(item) for item in obj.items],
            status_log=[StatusLog.from_orm(action) for action in obj.status_log],
        )


# Additional properties stored in DB
@dataclass
class InvoiceInDB(_InvoiceInDBBase):
    pass
