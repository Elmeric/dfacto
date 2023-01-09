# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Optional

from sqlalchemy import ForeignKey, ScalarResult, String, delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.models import db
from dfacto.models.service import _Service
from dfacto.models.vat_rate import _VatRate


class Client(db.BaseModel):
    __tablename__ = "client"

    id: Mapped[db.intpk] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(10))
    address: Mapped[str]
    zip_code: Mapped[str] = mapped_column(String(5))
    city: Mapped[str]
    active: Mapped[bool]

    invoices: Mapped[list["Invoice"]] = relationship(
        default_factory=list, back_populates="client", cascade="all, delete-orphan"
    )
    basket: Mapped["Basket"] = relationship(
        default=None, back_populates="client", cascade="all, delete-orphan"
    )

    def __post_init__(self):
        basket = Basket()
        basket.items = []
        basket.client = self
        self.basket = basket


class Item(db.BaseModel):
    __tablename__ = "item"

    id: Mapped[db.intpk] = mapped_column(init=False)
    raw_amount: Mapped[float]
    vat: Mapped[float]
    net_amount: Mapped[float]
    quantity: Mapped[int] = mapped_column(default=1)
    service_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("service.id"), init=False
    )
    invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoice.id"), init=False
    )
    basket_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("basket.id"), init=False
    )

    service: Mapped["_Service"] = relationship(default=None)
    invoice: Mapped["Invoice"] = relationship(back_populates="items", default=None)
    basket: Mapped["Basket"] = relationship(back_populates="items", default=None)


class InvoiceStatus(enum.Enum):
    DRAFT = 1
    EMITTED = 2
    REMINDED = 3
    PAID = 4
    CANCELLED = 5


class Invoice(db.BaseModel):
    __tablename__ = "invoice"

    id: Mapped[db.intpk] = mapped_column(init=False)
    code: Mapped[str] = mapped_column(String(10))
    date: Mapped[date]
    due_date: Mapped[date]
    status: Mapped[InvoiceStatus]
    #    status: Mapped[InvoiceStatus] = mapped_column(Enum(create_constraint=True, validate_strings=True))
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("client.id"), init=False
    )

    client: Mapped["Client"] = relationship(back_populates="invoices", default=None)
    items: Mapped[list["Item"]] = relationship(
        default_factory=list, back_populates="invoice", cascade="all, delete"
    )


class Basket(db.BaseModel):
    __tablename__ = "basket"

    id: Mapped[db.intpk] = mapped_column(init=False)
    raw_amount: Mapped[float] = mapped_column(default=0.0)
    vat: Mapped[float] = mapped_column(default=0.0)
    net_amount: Mapped[float] = mapped_column(default=0.0)
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("client.id"), init=False
    )

    client: Mapped["Client"] = relationship(back_populates="basket", default=None)
    items: Mapped[list["Item"]] = relationship(
        default_factory=list, back_populates="basket", cascade="all"
    )


class ServiceModel:
    def add_service(
        self, id_: int, name: str, unit_price: float, vat_rate_id: Optional[int] = None
    ) -> None:
        pass
