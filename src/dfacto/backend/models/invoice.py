# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import BaseModel, intpk

if TYPE_CHECKING:  # pragma: no cover
    from .client import Client
    from .item import Item

    def _(_text: str) -> str:
        ...


class InvoiceStatus(enum.Enum):
    DRAFT = 1
    EMITTED = 2
    REMINDED = 3
    PAID = 4
    CANCELLED = 5

    def as_string(self) -> str:
        return {
            InvoiceStatus.DRAFT: _("Draft"),
            InvoiceStatus.EMITTED: _("Emitted"),
            InvoiceStatus.REMINDED: _("Reminded"),
            InvoiceStatus.PAID: _("Paid"),
            InvoiceStatus.CANCELLED: _("Cancelled"),
        }.get(self, "")


class Invoice(BaseModel):
    # pylint: disable=too-few-public-methods
    __tablename__ = "invoice"

    id: Mapped[intpk] = mapped_column(init=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    globals_id: Mapped[int] = mapped_column(ForeignKey("globals.id"))
    status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.DRAFT)

    globals: Mapped["Globals"] = relationship(init=False)
    client: Mapped["Client"] = relationship(back_populates="invoices", init=False)
    items: Mapped[list["Item"]] = relationship(
        back_populates="invoice",
        init=False
        # back_populates="invoice", init=False, cascade="all, delete-orphan"
    )
    status_log: Mapped[list["StatusLog"]] = relationship(
        back_populates="invoice", init=False, cascade="all, delete-orphan"
    )


class StatusLog(BaseModel):
    # pylint: disable=too-few-public-methods
    __tablename__ = "status_log"

    id: Mapped[intpk] = mapped_column(init=False)
    from_: Mapped[datetime]
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"))
    to: Mapped[Optional[datetime]] = mapped_column(default=None)
    status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.DRAFT)

    invoice: Mapped["Invoice"] = relationship(back_populates="status_log", init=False)


class Globals(BaseModel):
    # pylint: disable=too-few-public-methods
    __tablename__ = "globals"

    id: Mapped[intpk] = mapped_column(init=False)
    due_delta: Mapped[int]
    penalty_rate: Mapped[Decimal]
    discount_rate: Mapped[Decimal]
    is_current: Mapped[bool] = mapped_column(default=True)
