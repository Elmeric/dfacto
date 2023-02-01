# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from sqlalchemy import String, and_, case, exists, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.models.db import BaseModel, intpk

from .basket import _Basket
from .invoice import InvoiceStatus, _Invoice


class _Client(BaseModel):
    __tablename__ = "client"

    id: Mapped[intpk] = mapped_column(init=False)
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
