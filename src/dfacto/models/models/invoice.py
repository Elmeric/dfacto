# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.models import db

if TYPE_CHECKING:  # pragma: no cover
    from .client import Client
    from .item import Item


class InvoiceStatus(enum.Enum):
    DRAFT = 1
    EMITTED = 2
    REMINDED = 3
    PAID = 4
    CANCELLED = 5


class Invoice(db.BaseModel):
    __tablename__ = "invoice"

    id: Mapped[db.intpk] = mapped_column(init=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    raw_amount: Mapped[float] = mapped_column(default=0.0)
    vat: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.DRAFT)
    #    status: Mapped[InvoiceStatus] = mapped_column(Enum(create_constraint=True, validate_strings=True))

    client: Mapped["Client"] = relationship(back_populates="invoices", init=False)
    items: Mapped[list["Item"]] = relationship(
        back_populates="invoice",
        init=False
        # back_populates="invoice", init=False, cascade="all, delete-orphan"
    )
    status_log: Mapped[list["StatusLog"]] = relationship(
        back_populates="invoice", init=False, cascade="all, delete-orphan"
    )

    @hybrid_property
    def net_amount(self) -> float:
        return self.raw_amount + self.vat

    # @hybrid_property
    # def code(self) -> str:
    #     return "FC" + str(self.id).zfill(10)


class StatusLog(db.BaseModel):
    __tablename__ = "status_log"

    id: Mapped[db.intpk] = mapped_column(init=False)
    from_: Mapped[datetime]
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"))
    to: Mapped[Optional[datetime]] = mapped_column(default=None)
    status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.DRAFT)

    invoice: Mapped["Invoice"] = relationship(back_populates="status_log", init=False)
