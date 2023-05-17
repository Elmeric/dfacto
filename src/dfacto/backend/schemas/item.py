# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from decimal import Decimal

from dfacto.backend import models

from .base import Amount, BaseSchema
from .service import Service


@dataclass
class _ItemBase(BaseSchema[models.Item]):
    service_id: int
    quantity: int


@dataclass
class _ItemDefaultsBase(BaseSchema[models.Item]):
    pass


@dataclass
class ItemCreate(_ItemBase):
    quantity: int = 1


@dataclass
class ItemUpdate(_ItemDefaultsBase):
    pass


@dataclass
class _ItemInDBBase(_ItemBase):
    id: int


# Additional properties to return from DB
@dataclass
class Item(_ItemInDBBase):
    service: Service

    @property
    def amount(self) -> Amount:
        service = self.service
        raw_amount = service.unit_price * self.quantity
        vat_amount = (raw_amount * service.vat_rate.rate / 100).quantize(Decimal('0.01'))
        net_amount = raw_amount + vat_amount
        return Amount(raw=raw_amount, vat=vat_amount, net=net_amount)

    @classmethod
    def from_orm(cls, orm_obj: models.Item) -> "Item":
        return cls(
            id=orm_obj.id,
            service_id=orm_obj.service.id,
            quantity=orm_obj.quantity,
            service=Service.from_orm(orm_obj.service),
        )


# Additional properties stored in DB
@dataclass
class ItemInDB(_ItemInDBBase):
    pass
