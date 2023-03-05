# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional, cast

from dfacto.models import db, models

from .base import BaseSchema


@dataclass
class _VatRateBase(BaseSchema):
    name: str
    rate: float
    is_default: bool
    is_preset: bool


@dataclass
class _VatRateDefaultsBase(BaseSchema):
    name: Optional[str] = None
    rate: Optional[float] = None


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
    def from_orm(cls, orm_obj: db.BaseModel) -> "VatRate":
        obj = cast(models.VatRate, orm_obj)
        return cls(
            id=obj.id,
            name=obj.name,
            rate=obj.rate,
            is_default=obj.is_default,
            is_preset=obj.is_preset,
        )


# Additional properties stored in DB
@dataclass
class VatRateInDB(_VatRateInDBBase):
    pass
