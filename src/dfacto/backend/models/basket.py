# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.backend import db

if TYPE_CHECKING:  # pragma: no cover
    from .item import Item


class Basket(db.BaseModel):
    __tablename__ = "basket"

    id: Mapped[db.intpk] = mapped_column(init=False)
    raw_amount: Mapped[float] = mapped_column(default=0.0)
    vat: Mapped[float] = mapped_column(default=0.0)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("client.id"), init=False, unique=True
    )

    items: Mapped[list["Item"]] = relationship(
        back_populates="basket",
        init=False
        # back_populates="basket", init=False, cascade="all, delete-orphan"
    )
