# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from dfacto.models.db import BaseModel, intpk

if TYPE_CHECKING:
    from .client import _Client
    from .item import _Item


class _Basket(BaseModel):
    __tablename__ = "basket"

    id: Mapped[intpk] = mapped_column(init=False)
    raw_amount: Mapped[float] = mapped_column(default=0.0)
    vat: Mapped[float] = mapped_column(default=0.0)
    net_amount: Mapped[float] = mapped_column(default=0.0)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("client.id"), init=False, unique=True
    )

    client: Mapped["_Client"] = relationship(back_populates="basket", init=False)
    items: Mapped[list["_Item"]] = relationship(
        back_populates="basket",
        init=False
        # back_populates="basket", init=False, cascade="all, delete-orphan"
    )
