# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Generic, NamedTuple

from dfacto.backend.models import ModelType


@dataclass
class BaseSchema(Generic[ModelType]):
    def flatten(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_orm(cls, orm_obj: ModelType) -> "BaseSchema[ModelType]":
        return BaseSchema()


class Amount(NamedTuple):
    raw: Decimal = Decimal(0)
    vat: Decimal = Decimal(0)
    net: Decimal = Decimal(0)

    def __add__(self, other: "Amount") -> "Amount":
        if not isinstance(other, Amount):
            raise ValueError(f"{other} shall be an Amount instance!")
        return Amount(
            raw=self.raw + other.raw,
            vat=self.vat + other.vat,
            net=self.net + other.net
        )

    def __iadd__(self, other: "Amount") -> "Amount":
        return self.__add__(other)

    def __neg__(self) -> "Amount":
        return Amount(
            raw=-self.raw,
            vat=-self.vat,
            net=-self.net
        )
