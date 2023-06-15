# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from dfacto.backend import models

from .base import BaseSchema


@dataclass
class _VatRateBase(BaseSchema[models.VatRate]):
    name: str
    rate: Decimal
    is_default: bool
    is_preset: bool


@dataclass
class _VatRateDefaultsBase(BaseSchema[models.VatRate]):
    name: Optional[str] = None
    rate: Optional[Decimal] = None


@dataclass
class VatRateCreate(_VatRateBase):
    is_default: bool = False
    is_preset: bool = False


@dataclass
class VatRateUpdate(_VatRateDefaultsBase):
    pass


@dataclass
class _VatRateInDBBase(_VatRateBase):
    id: int


# Additional properties to return from DB
@dataclass
class VatRate(_VatRateInDBBase):
    @classmethod
    def from_orm(cls, orm_obj: models.VatRate) -> "VatRate":
        return cls(
            id=orm_obj.id,
            name=orm_obj.name,
            rate=orm_obj.rate.quantize(Decimal("0.1")),
            is_default=orm_obj.is_default,
            is_preset=orm_obj.is_preset,
        )


# Additional properties stored in DB
@dataclass
class VatRateInDB(_VatRateInDBBase):
    pass
