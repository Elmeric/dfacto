# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass

from dfacto.backend import models

from .base import Amount, BaseSchema
from .client import Client
from .item import Item


@dataclass
class _BasketBase(BaseSchema[models.Basket]):
    pass


@dataclass
class _BasketDefaultsBase(BaseSchema[models.Basket]):
    pass


@dataclass
class BasketCreate(_BasketBase):
    client_id: int
    is_active: bool = True


@dataclass
class BasketUpdate(_BasketDefaultsBase):
    pass


@dataclass
class _BasketInDBBase(_BasketBase):
    id: int


# Additional properties to return from DB
@dataclass
class Basket(_BasketInDBBase):
    client_id: int
    client: Client
    items: list[Item]

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
    def is_empty(self) -> bool:
        return len(self.items) == 0

    @property
    def is_active(self) -> bool:
        return self.client.is_active

    @classmethod
    def from_orm(cls, orm_obj: models.Basket) -> "Basket":
        return cls(
            id=orm_obj.id,
            client_id=orm_obj.client_id,
            client=Client.from_orm(orm_obj.client),
            items=[Item.from_orm(item) for item in orm_obj.items],
        )


# Additional properties stored in DB
@dataclass
class BasketInDB(_BasketInDBBase):
    pass
