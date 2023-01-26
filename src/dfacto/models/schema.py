# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from typing import Optional
from dataclasses import dataclass

from dfacto.models.model import _VatRate


@dataclass()
class _VatRateBase:
    pass


@dataclass()
class _VatRateDefaultsBase:
    rate: Optional[float] = 0.0


@dataclass()
class VatRateCreate(_VatRateBase):
    rate: float


@dataclass()
class VatRateUpdate(_VatRateBase, _VatRateDefaultsBase):
    pass


@dataclass()
class _VatRateInDBBase(_VatRateBase):
    id: int
    rate: float


# Additional properties to return from DB
@dataclass()
class VatRate(_VatRateInDBBase):
    pass

    @classmethod
    def from_orm(cls, orm_obj: _VatRate) -> "VatRate":
        return cls(orm_obj.id, orm_obj.rate)


# Additional properties stored in DB
@dataclass()
class VatRateInDB(_VatRateInDBBase):
    pass
