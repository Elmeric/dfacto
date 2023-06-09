# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import BaseModel, intpk

if TYPE_CHECKING:  # pragma: no cover
    from .service import Service


class VatRate(BaseModel):
    # pylint: disable=too-few-public-methods
    __tablename__ = "vat_rate"

    id: Mapped[intpk] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(unique=True)
    rate: Mapped[decimal.Decimal]
    is_default: Mapped[bool] = mapped_column(default=False)
    is_preset: Mapped[bool] = mapped_column(default=False)

    services: Mapped[list["Service"]] = relationship(
        init=False,
        back_populates="vat_rate",
    )
