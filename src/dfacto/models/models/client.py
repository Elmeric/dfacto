# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING, cast

from sqlalchemy import String, and_, case, exists, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dfacto.models import db

from .basket import Basket
from .invoice import Invoice, InvoiceStatus

# Refer to: https://github.com/dropbox/sqlalchemy-stubs/issues/98#issuecomment-762884766
if TYPE_CHECKING:
    hybrid_property = property
else:
    from sqlalchemy.ext.hybrid import hybrid_property


class Client(db.BaseModel):
    __tablename__ = "client"

    id: Mapped[db.intpk] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    address: Mapped[str]
    zip_code: Mapped[str] = mapped_column(String(5))
    city: Mapped[str]
    email: Mapped[str] = mapped_column(String(254))
    is_active: Mapped[bool] = mapped_column(default=True)

    basket: Mapped["Basket"] = relationship(
        init=False,
        # cascade="all, delete-orphan"
        # init=False, back_populates="client", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        init=False,
        back_populates="client",
        # cascade="all, delete-orphan",
    )

    @hybrid_property
    def has_emitted_invoices(self) -> bool:
        return any(invoice.status != InvoiceStatus.DRAFT for invoice in self.invoices)

    @has_emitted_invoices.expression
    def has_emitted_invoices(cls):  # type: ignore
        return select(
            case(
                (
                    exists()
                    .where(
                        and_(
                            Invoice.client_id == cls.id,
                            Invoice.status != "DRAFT",
                        )
                    )
                    .correlate(cls),  # type: ignore
                    True,
                ),
                else_=False,
            ).label("has_emitted_invoices")
        ).scalar_subquery()

    def __post_init__(self) -> None:
        self.basket = cast(Mapped[Basket], Basket())
