# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
import sqlalchemy.exc
import sqlalchemy.orm

from dfacto.models import db, vat_rate

if TYPE_CHECKING:
    from dfacto.models.vat_rate import _VatRate


class _Service(db.BaseModel):
    __tablename__ = "service"

    id: sa.orm.Mapped[db.intpk] = sa.orm.mapped_column(init=False)
    name: sa.orm.Mapped[str] = sa.orm.mapped_column(unique=True)
    unit_price: sa.orm.Mapped[float]
    vat_rate_id: sa.orm.Mapped[int] = sa.orm.mapped_column(
        sa.ForeignKey("vat_rate.id"), nullable=False
    )

    vat_rate: sa.orm.Mapped["_VatRate"] = sa.orm.relationship(init=False)


@dataclass()
class Service:
    id: int
    name: str
    unit_price: float
    vat_rate_id: int
    vat_rate: float


def get(service_id: Optional[int] = None) -> Service:
    service = db.Session.get(_Service, service_id)
    if service is None:
        raise db.RejectedCommand(f"Cannot find a service with {service_id} id!")
    return Service(
        service.id,
        service.name,
        service.unit_price,
        service.vat_rate.id,
        service.vat_rate.rate,
    )


def list_all() -> list[Service]:
    return [
        Service(
            service.id,
            service.name,
            service.unit_price,
            service.vat_rate_id,
            service.vat_rate.rate,
        )
        for service in db.Session.scalars(sa.select(_Service)).all()
    ]


def add(
    name: str, unit_price: float, vat_rate_id: int = vat_rate.DEFAULT_RATE_ID
) -> Service:
    service = _Service(name=name, unit_price=unit_price, vat_rate_id=vat_rate_id)
    db.Session.add(service)
    try:
        db.Session.commit()
    except sa.exc.IntegrityError as exc:
        db.Session.rollback()
        raise db.RejectedCommand(f"Cannot add service {name}: {exc}")
    else:
        return Service(
            service.id,
            service.name,
            service.unit_price,
            service.vat_rate_id,
            service.vat_rate.rate,
        )


def update(
    service_id: int,
    name: Optional[str] = None,
    unit_price: Optional[float] = None,
    vat_rate_id: Optional[int] = None,
) -> Service:
    service = db.Session.get(_Service, service_id)
    if service is None:
        raise db.RejectedCommand(f"Cannot find a service with {service_id} id!")

    if name is not None and name != service.name:
        service.name = name

    if unit_price is not None and unit_price != service.unit_price:
        service.unit_price = unit_price

    if vat_rate_id is not None and vat_rate_id != service.vat_rate_id:
        service.vat_rate_id = vat_rate.get(vat_rate_id).id

    try:
        db.Session.commit()
    except sa.exc.IntegrityError as exc:
        db.Session.rollback()
        raise db.RejectedCommand(f"Cannot update service {service.name}: {exc}")
    else:
        return Service(
            service.id,
            service.name,
            service.unit_price,
            service.vat_rate_id,
            service.vat_rate.rate,
        )


def delete(service_id: int) -> None:
    try:
        db.Session.execute(sa.delete(_Service).where(_Service.id == service_id))
    except sa.exc.IntegrityError:
        # in_use = db.Session.scalars(
        #     sa.select(Item.id)
        #     .join(Item.service)
        #     .where(Item.service_id == service_id)
        # ).first()
        raise db.RejectedCommand(
            f"Service with id {service_id} is used" f" by at least one invoice's item!"
        )
    else:
        db.Session.commit()
