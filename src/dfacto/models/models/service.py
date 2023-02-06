# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.models.db import BaseModel, intpk

if TYPE_CHECKING:   # pragma: no cover
    from .vat_rate import VatRate


class Service(BaseModel):
    __tablename__ = "service"

    id: Mapped[intpk] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(unique=True)
    unit_price: Mapped[float]
    vat_rate_id: Mapped[int] = mapped_column(ForeignKey("vat_rate.id"))

    vat_rate: Mapped["VatRate"] = relationship(init=False, back_populates="services")
