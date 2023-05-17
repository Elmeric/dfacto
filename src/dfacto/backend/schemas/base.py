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
    raw: Decimal
    vat: Decimal
    net: Decimal
