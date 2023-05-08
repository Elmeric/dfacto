# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, cast

from dfacto.backend import models

from .base import Amount, BaseSchema
from .item import Item
from .client import Client


@dataclass
class _InvoiceBase(BaseSchema[models.Invoice]):
    client_id: int


@dataclass
class _InvoiceDefaultsBase(BaseSchema[models.Invoice]):
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
    status: models.InvoiceStatus


# Additional properties to return from DB
@dataclass
class StatusLog(BaseSchema[models.StatusLog]):
    id: int
    status: models.InvoiceStatus
    from_: datetime
    to: Optional[datetime]
    invoice_id: int

    @classmethod
    def from_orm(cls, orm_obj: models.StatusLog) -> "StatusLog":
        return cls(
            id=orm_obj.id,
            status=orm_obj.status,
            from_=orm_obj.from_,
            to=orm_obj.to,
            invoice_id=orm_obj.invoice.id,
        )


@dataclass
class Invoice(_InvoiceInDBBase):
    items: list[Item]
    status_log: dict[models.InvoiceStatus, StatusLog]
    client: Client

    @property
    def code(self) -> str:
        return "FC" + str(self.id).zfill(5)

    @property
    def amount(self) -> Amount:
        raw_amount = vat_amount = net_amount = 0.0
        for item in self.items:
            amount = item.amount
            raw_amount += amount.raw
            vat_amount += amount.vat
            net_amount += amount.net
        return Amount(raw=raw_amount, vat=vat_amount, net=net_amount)

    @property
    def created_on(self) -> datetime:
        creation_log = self.status_log[models.InvoiceStatus.DRAFT]
        return creation_log.from_

    @property
    def issued_on(self) -> Optional[datetime]:
        try:
            creation_log = self.status_log[models.InvoiceStatus.EMITTED]
        except KeyError:
            return None
        return creation_log.from_

    @property
    def reminded_on(self) -> Optional[datetime]:
        try:
            creation_log = self.status_log[models.InvoiceStatus.REMINDED]
        except KeyError:
            return None
        return creation_log.from_

    @property
    def paid_on(self) -> Optional[datetime]:
        try:
            creation_log = self.status_log[models.InvoiceStatus.PAID]
        except KeyError:
            return None
        return creation_log.from_

    @property
    def cancelled_on(self) -> Optional[datetime]:
        try:
            creation_log = self.status_log[models.InvoiceStatus.CANCELLED]
        except KeyError:
            return None
        return creation_log.from_

    @classmethod
    def from_orm(cls, orm_obj: models.Invoice) -> "Invoice":
        return cls(
            id=orm_obj.id,
            status=orm_obj.status,
            client_id=orm_obj.client_id,
            items=[Item.from_orm(item) for item in orm_obj.items],
            status_log={
                log.status: StatusLog.from_orm(log) for log in orm_obj.status_log
            },
            client=Client.from_orm(orm_obj.client)
        )


# Additional properties stored in DB
@dataclass
class InvoiceInDB(_InvoiceInDBBase):
    pass
