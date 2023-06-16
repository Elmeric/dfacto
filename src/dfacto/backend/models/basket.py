# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import BaseModel, intpk

if TYPE_CHECKING:  # pragma: no cover
    from .client import Client
    from .item import Item


class Basket(BaseModel):
    # pylint: disable=too-few-public-methods
    __tablename__ = "basket"

    id: Mapped[intpk] = mapped_column(init=False)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("client.id"), init=False, unique=True
    )

    client: Mapped["Client"] = relationship(
        # back_populates="basket",
        init=False
        # back_populates="basket", init=False, cascade="all, delete-orphan"
    )
    items: Mapped[list["Item"]] = relationship(
        back_populates="basket",
        init=False
        # back_populates="basket", init=False, cascade="all, delete-orphan"
    )
