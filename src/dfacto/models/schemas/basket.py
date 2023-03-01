# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass

from dfacto.models import models

from .base import BaseSchema
from .item import Item


@dataclass
class _BasketBase(BaseSchema):
    raw_amount: float
    vat: float
    net_amount: float


@dataclass
class _BasketDefaultsBase(BaseSchema):
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
    items: list[Item]

    @classmethod
    def from_orm(cls, orm_obj: models.Basket) -> "Basket":
        return cls(
            id=orm_obj.id,
            raw_amount=orm_obj.raw_amount,
            vat=orm_obj.vat,
            net_amount=orm_obj.net_amount,
            items=[Item.from_orm(item) for item in orm_obj.items],
        )


# Additional properties stored in DB
@dataclass
class BasketInDB(_BasketInDBBase):
    client_id: int
