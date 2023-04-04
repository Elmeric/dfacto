# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import CheckConstraint

from .base_model import BaseModel, intpk

if TYPE_CHECKING:  # pragma: no cover
    from .basket import Basket
    from .invoice import Invoice
    from .service import Service


class Item(BaseModel):
    __tablename__ = "item"
    __table_args__ = (
        CheckConstraint(
            "not ((basket_id is NULL) and (invoice_id is NULL))",
            # "(basket_id is not NULL) or (invoice_id is not NULL)",
            name="basket_or_invoice_not_null",
        ),
    )

    id: Mapped[intpk] = mapped_column(init=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("service.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoice.id"), init=False
    )
    basket_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("basket.id"), init=False
    )

    service: Mapped["Service"] = relationship(init=False)
    basket: Mapped["Basket"] = relationship(back_populates="items", init=False)
    invoice: Mapped["Invoice"] = relationship(back_populates="items", init=False)
