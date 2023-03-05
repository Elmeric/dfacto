# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import cast

from dfacto.models import db, models

from .base import BaseSchema
from .item import Item


@dataclass
class _BasketBase(BaseSchema):
    raw_amount: float
    vat: float


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

    @property
    def net_amount(self) -> float:
        return self.raw_amount + self.vat

    @classmethod
    def from_orm(cls, orm_obj: db.BaseModel) -> "Basket":
        obj = cast(models.Basket, orm_obj)
        return cls(
            id=obj.id,
            raw_amount=obj.raw_amount,
            vat=obj.vat,
            items=[Item.from_orm(item) for item in obj.items],
        )


# Additional properties stored in DB
@dataclass
class BasketInDB(_BasketInDBBase):
    client_id: int
