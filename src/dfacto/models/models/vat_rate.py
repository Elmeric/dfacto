# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.models.db import BaseModel, intpk

if TYPE_CHECKING:
    from .service import Service


class VatRate(BaseModel):
    __tablename__ = "vat_rate"

    id: Mapped[intpk] = mapped_column(init=False)
    rate: Mapped[float]

    services: Mapped[list["Service"]] = relationship(
        init=False,
        back_populates="vat_rate",
    )
