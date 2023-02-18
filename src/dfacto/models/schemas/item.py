# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from dataclasses import dataclass

from dfacto.models import models

from .base import BaseSchema
from .service import Service


@dataclass
class _ItemBase(BaseSchema):
    raw_amount: float
    vat: float
    net_amount: float
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

    @classmethod
    def from_orm(cls, orm_obj: models.Item) -> "Item":
        return cls(
            id=orm_obj.id,
            raw_amount=orm_obj.raw_amount,
            vat=orm_obj.vat,
            net_amount=orm_obj.net_amount,
            service_id=orm_obj.service.id,
            quantity=orm_obj.quantity,
            service=Service.from_orm(orm_obj.service),
        )


# Additional properties stored in DB
@dataclass
class ItemInDB(_ItemInDBBase):
    pass
