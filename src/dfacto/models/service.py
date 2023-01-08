# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.exc

from dfacto.models import db
from dfacto.models import vat_rate

if TYPE_CHECKING:
    from dfacto.models.vat_rate import _VatRate


class _Service(db.BaseModel):
    __tablename__ = "service"

    id: sa.orm.Mapped[db.intpk] = sa.orm.mapped_column(init=False)
    name: sa.orm.Mapped[str]
    unit_price: sa.orm.Mapped[float]
    vat_rate_id: sa.orm.Mapped[Optional[int]] = sa.orm.mapped_column(
        sa.ForeignKey("vat_rate.id"), init=False
    )

    vat_rate: sa.orm.Mapped["_VatRate"] = sa.orm.relationship(
        default_factory=vat_rate.get_default
    )


@dataclass()
class Service:
    id: int
    name: str
    unit_prices: float
    vat_rate_id: int
    vat_rate: float


def get(service_id: int = None) -> Optional[Service]:
    service = db.Session.get(_Service, service_id)
    if service is None:
        raise db.RejectedCommand(f"Cannot find a service with {service_id} id!")
    rate = vat_rate.get(service.vat_rate_id)
    if rate is None:
        rate = vat_rate.get_default()
    return Service(
        service.id, service.name, service.unit_price, rate.id, rate.rate
    )


def list_all() -> list[Service]:
    return [
        Service(s.id, s.name, s.unit_price, s.vat_rate_id, s.vat_rate)
        for s in db.Session.scalars(sa.select(_Service)).all()
    ]


def add(rate: float) -> Service:
    v = _Service(rate=rate)
    db.Session.add(v)
    db.Session.commit()
    return Service(v.id, v.rate)


def update(service_id: int, rate: float) -> Service:
    v = db.Session.get(_Service, service_id)
    v.rate = rate
    # db.Session.execute(
    #     sa.update(_Service),
    #     [{"id": service_id, "rate": rate}]
    # )
    db.Session.commit()
    return Service(service_id, rate)


def delete(self, service_id: int) -> None:
    if service_id in self.PRESET_RATE_IDS:
        raise db.RejectedCommand("Default VAT rates cannot be deleted!")

    try:
        db.Session.execute(
            sa.delete(_Service).where(_Service.id == service_id)
        )
    except sa.exc.IntegrityError:
        in_use = db.Session.scalars(
            sa.select(_Service.name)
            .join(_Service.service)
            .where(_Service.service_id == service_id)
        ).first()
        raise db.RejectedCommand(f"VAT rate with id {service_id} is used"
                                 f" by ay least {in_use} service!")
    else:
        db.Session.commit()
