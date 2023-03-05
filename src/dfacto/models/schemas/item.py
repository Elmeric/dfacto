# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from dataclasses import dataclass
from typing import cast

from dfacto.models import db, models

from .base import BaseSchema
from .service import Service


@dataclass
class _ItemBase(BaseSchema):
    raw_amount: float
    vat: float
    service_id: int
    quantity: int


@dataclass
class _ItemDefaultsBase(BaseSchema):
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
    def net_amount(self) -> float:
        return self.raw_amount + self.vat

    @classmethod
    def from_orm(cls, orm_obj: db.BaseModel) -> "Item":
        obj = cast(models.Item, orm_obj)
        return cls(
            id=obj.id,
            raw_amount=obj.raw_amount,
            vat=obj.vat,
            service_id=obj.service.id,
            quantity=obj.quantity,
            service=Service.from_orm(obj.service),
        )


# Additional properties stored in DB
@dataclass
class ItemInDB(_ItemInDBBase):
    pass
