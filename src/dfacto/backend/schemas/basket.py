# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass

from dfacto.backend import models

from .base import BaseSchema
from .item import Item


@dataclass
class _BasketBase(BaseSchema[models.Basket]):
    raw_amount: float
    vat: float


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
    items: list[Item]

    @property
    def net_amount(self) -> float:
        return self.raw_amount + self.vat

    @classmethod
    def from_orm(cls, orm_obj: models.Basket) -> "Basket":
        return cls(
            id=orm_obj.id,
            raw_amount=orm_obj.raw_amount,
            vat=orm_obj.vat,
            client_id=orm_obj.client_id,
            items=[Item.from_orm(item) for item in orm_obj.items],
        )


# Additional properties stored in DB
@dataclass
class BasketInDB(_BasketInDBBase):
    pass
