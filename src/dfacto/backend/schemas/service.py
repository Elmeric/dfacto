# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from dfacto.backend import models

from .base import BaseSchema
from .vat_rate import VatRate

ServiceKey = tuple[int, int]  # (id, version)


@dataclass
class _ServiceBase(BaseSchema[models.Service]):
    name: str
    unit_price: Decimal


@dataclass
class _ServiceDefaultsBase(BaseSchema[models.Service]):
    name: Optional[str] = None
    unit_price: Optional[Decimal] = None
    vat_rate_id: Optional[int] = None


@dataclass
class ServiceCreate(_ServiceBase):
    vat_rate_id: int


@dataclass
class ServiceUpdate(_ServiceDefaultsBase):
    pass


@dataclass
class _ServiceInDBBase(_ServiceBase):
    pass


# Additional properties to return from DB
@dataclass
class Service(_ServiceInDBBase):
    key: ServiceKey
    vat_rate: VatRate

    @property
    def id(self) -> int:
        return self.key[0]

    @classmethod
    def from_orm(cls, orm_obj: models.Service) -> "Service":
        return cls(
            key=(orm_obj.id, orm_obj.version),
            name=orm_obj.name,
            unit_price=orm_obj.unit_price.quantize(Decimal("0.01")),
            vat_rate=VatRate.from_orm(orm_obj.vat_rate),
        )


# Additional properties stored in DB
@dataclass
class ServiceInDB(_ServiceInDBBase):
    id: int
    version: int
    vat_rate_id: int
    from_: datetime
    to_: datetime
    is_current: bool
