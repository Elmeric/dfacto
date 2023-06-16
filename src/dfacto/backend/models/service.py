# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import decimal
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import BaseModel

if TYPE_CHECKING:  # pragma: no cover
    from .vat_rate import VatRate


# https://hub.packtpub.com/slowly-changing-dimension-scd-type-6/
class Service(BaseModel):
    # pylint: disable=too-few-public-methods
    __tablename__ = "service"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    unit_price: Mapped[decimal.Decimal]
    vat_rate_id: Mapped[int] = mapped_column(ForeignKey("vat_rate.id"))
    from_: Mapped[datetime] = mapped_column(default=datetime(1900, 1, 1, 0, 0, 0))
    to_: Mapped[datetime] = mapped_column(default=datetime(9999, 12, 31, 23, 59, 59))
    is_current: Mapped[bool] = mapped_column(default=True)

    vat_rate: Mapped["VatRate"] = relationship(init=False, back_populates="services")
