# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from datetime import date
from typing import Optional

from sqlalchemy import ForeignKey, String, and_, case, exists, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import CheckConstraint

from dfacto.models import db


class _VatRate(db.BaseModel):
    __tablename__ = "vat_rate"

    id: Mapped[db.intpk] = mapped_column(init=False)
    rate: Mapped[float]


class _Service(db.BaseModel):
    __tablename__ = "service"

    id: Mapped[db.intpk] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(unique=True)
    unit_price: Mapped[float]
    vat_rate_id: Mapped[int] = mapped_column(ForeignKey("vat_rate.id"))

    vat_rate: Mapped["_VatRate"] = relationship(init=False)


class _Client(db.BaseModel):
    __tablename__ = "client"

    id: Mapped[db.intpk] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    address: Mapped[str]
    zip_code: Mapped[str] = mapped_column(String(5))
    city: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)

    basket: Mapped["_Basket"] = relationship(
        init=False, back_populates="client", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["_Invoice"]] = relationship(
        init=False,
        back_populates="client",
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def code(self) -> str:
        return "CL" + str(self.id).zfill(5)

    @hybrid_property
    def has_emitted_invoices(self) -> bool:
        return any(invoice.status != InvoiceStatus.DRAFT for invoice in self.invoices)

    @has_emitted_invoices.expression
    def has_emitted_invoices(cls):
        return select(
            case(
                (
                    exists()
                    .where(
                        and_(
                            _Invoice.client_id == cls.id,
                            _Invoice.status != "DRAFT",
                        )
                    )
                    .correlate(cls),
                    True,
                ),
                else_=False,
            ).label("has_emitted_invoices")
        ).scalar_subquery()

    def __post_init__(self) -> None:
        self.basket = _Basket()


class _Item(db.BaseModel):
    __tablename__ = "item"
    __table_args__ = (
        CheckConstraint(
            "not ((basket_id is NULL) and (invoice_id is NULL))",
            # "(basket_id is not NULL) or (invoice_id is not NULL)",
            name="basket_or_invoice_not_null",
        ),
    )

    id: Mapped[db.intpk] = mapped_column(init=False)
    raw_amount: Mapped[float] = mapped_column(init=False)
    vat: Mapped[float] = mapped_column(init=False)
    net_amount: Mapped[float] = mapped_column(init=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoice.id"), init=False
    )
    basket_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("basket.id"), init=False
    )

    service: Mapped["_Service"] = relationship(init=False)
    basket: Mapped["_Basket"] = relationship(back_populates="items", init=False)
    invoice: Mapped["_Invoice"] = relationship(back_populates="items", init=False)

    def __post_init__(self) -> None:
        serv = db.Session.get(_Service, self.service_id)
        self.raw_amount = raw_amount = serv.unit_price * self.quantity
        self.vat = vat = raw_amount * serv.vat_rate.rate / 100
        self.net_amount = raw_amount + vat


class _Basket(db.BaseModel):
    __tablename__ = "basket"

    id: Mapped[db.intpk] = mapped_column(init=False)
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

    client: Mapped["_Client"] = relationship(back_populates="invoices", init=False)
    items: Mapped[list["_Item"]] = relationship(
        back_populates="invoice",
        init=False
        # back_populates="invoice", init=False, cascade="all, delete-orphan"
    )

    @hybrid_property
    def code(self) -> str:
        return "FC" + str(self.id).zfill(10)
