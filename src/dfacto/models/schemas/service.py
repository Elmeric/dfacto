# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from dataclasses import dataclass
from typing import Optional

from dfacto.models import models

from .base import BaseSchema
from .vat_rate import VatRate


@dataclass
class _ServiceBase(BaseSchema):
    name: str
    unit_price: float


@dataclass
class _ServiceDefaultsBase:
    name: Optional[str] = None
    unit_price: Optional[float] = None
    vat_rate_id: Optional[int] = None


@dataclass
class ServiceCreate(_ServiceBase):
    vat_rate_id: int


@dataclass
class ServiceUpdate(_ServiceDefaultsBase):
    pass


@dataclass
class _ServiceInDBBase(_ServiceBase):
    id: int


# Additional properties to return from DB
@dataclass
class Service(_ServiceInDBBase):
    vat_rate: VatRate

    @classmethod
    def from_orm(cls, orm_obj: models.Service) -> "Service":
        return cls(
            id=orm_obj.id,
            name=orm_obj.name,
            unit_price=orm_obj.unit_price,
            vat_rate=VatRate.from_orm(orm_obj.vat_rate),
        )


# Additional properties stored in DB
@dataclass
class ServiceInDB(_ServiceInDBBase):
    vat_rate_id: int
