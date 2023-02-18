# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.models import db

if TYPE_CHECKING:   # pragma: no cover
    from .client import Client
    from .item import Item


class InvoiceStatus(enum.Enum):
    DRAFT = 1
    EMITTED = 2
    REMINDED = 3
    PAID = 4
    CANCELLED = 5


class _Invoice(db.BaseModel):
    __tablename__ = "invoice"

    id: Mapped[db.intpk] = mapped_column(init=False)
    date: Mapped[date]
    due_date: Mapped[date]
    raw_amount: Mapped[float] = mapped_column(default=0.0)
    vat: Mapped[float] = mapped_column(default=0.0)
    net_amount: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.DRAFT)
    #    status: Mapped[InvoiceStatus] = mapped_column(Enum(create_constraint=True, validate_strings=True))
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), init=False)

    client: Mapped["Client"] = relationship(back_populates="invoices", init=False)
    items: Mapped[list["Item"]] = relationship(
        back_populates="invoice",
        init=False
        # back_populates="invoice", init=False, cascade="all, delete-orphan"
    )

    @hybrid_property
    def code(self) -> str:
        return "FC" + str(self.id).zfill(10)
