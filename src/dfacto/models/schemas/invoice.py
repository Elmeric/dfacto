# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from datetime import datetime

from dfacto.models import models

from .base import BaseSchema
from .item import Item


@dataclass
class _InvoiceBase(BaseSchema):
    client_id: int
    raw_amount: float
    vat: float
    status: models.InvoiceStatus


@dataclass
class _InvoiceDefaultsBase(BaseSchema):
    pass


@dataclass
class InvoiceCreate(_InvoiceBase):
    raw_amount: float = 0.0
    vat: float = 0.0
    status: models.InvoiceStatus = models.InvoiceStatus.DRAFT


@dataclass
class InvoiceUpdate(_InvoiceDefaultsBase):
    pass


@dataclass
class _InvoiceInDBBase(_InvoiceBase):
    id: int


# Additional properties to return from DB
@dataclass
class StatusLog(BaseSchema):
    id: int
    status: models.InvoiceStatus
    from_: datetime
    to: datetime
    invoice: "Invoice"

    @classmethod
    def from_orm(cls, orm_obj: models.StatusLog) -> "StatusLog":
        return cls(
            id=orm_obj.id,
            status=orm_obj.status,
            from_=orm_obj.from_,
            to=orm_obj.to,
            invoice=Invoice.from_orm(orm_obj.invoice),
        )


@dataclass
class Invoice(_InvoiceInDBBase):
    items: list[Item]
    actions: list[StatusLog]

    @property
    def code(self) -> str:
        return "FC" + str(self.id).zfill(10)

    @classmethod
    def from_orm(cls, orm_obj: models.Invoice) -> "Invoice":
        return cls(
            id=orm_obj.id,
            raw_amount=orm_obj.raw_amount,
            vat=orm_obj.vat,
            status=orm_obj.status,
            client_id=orm_obj.client_id,
            items=[Item.from_orm(item) for item in orm_obj.items],
            actions=[StatusLog.from_orm(action) for action in orm_obj.status_log],
        )


# Additional properties stored in DB
@dataclass
class InvoiceInDB(_InvoiceInDBBase):
    pass
