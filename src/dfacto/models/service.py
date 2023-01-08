# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import enum
from datetime import date
from dataclasses import dataclass
from typing import Annotated, Optional

from sqlalchemy import ForeignKey, String, ScalarResult, select, insert, update, delete
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.exc import IntegrityError

from dfacto.models import db
from dfacto.models.vat_rate import _VatRate, VatRateModel


class _Service(db.BaseModel):
    __tablename__ = "service"

    id: Mapped[db.intpk] = mapped_column(init=False)
    name: Mapped[str]
    unit_price: Mapped[float]
    vat_rate_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vat_rate.id"), init=False
    )

    vat_rate: Mapped["_VatRate"] = relationship(
        default_factory=VatRateModel.get_default_vat_rate
    )


@dataclass()
class Service:
    id: int
    name: str
    unit_prices: float
    vat_rate_id: int
    vat_rate: float


class ServiceModel:
    @staticmethod
    def get_service(service_id: int = None) -> Optional[Service]:
        service = db.Session.get(_Service, service_id)
        if service is None:
            raise db.RejectedCommand(f"Cannot find a service with {service_id} id!")
        vat_rate = db.Session.get(_VatRate, service.vat_rate_id)
        if vat_rate is None:
            vat_rate = VatRateModel.get_default_vat_rate()
        return Service(
            service.id, service.name, service.unit_price, vat_rate.id, vat_rate.rate
        )

    @staticmethod
    def list_services() -> list[Service]:
        return [Service(v.id, v.rate) for v in db.Session.scalars(select(_Service)).all()]

    @staticmethod
    def add_service(rate: float) -> Service:
        v = _Service(rate=rate)
        db.Session.add(v)
        db.Session.commit()
        return Service(v.id, v.rate)

    @staticmethod
    def update_service(service_id: int, rate: float) -> Service:
        v = db.Session.get(_Service, service_id)
        v.rate = rate
        # db.Session.execute(
        #     update(_Service),
        #     [{"id": service_id, "rate": rate}]
        # )
        db.Session.commit()
        return Service(service_id, rate)

    def delete_service(self, service_id: int) -> None:
        if service_id in self.PRESET_RATE_IDS:
            raise db.RejectedCommand("Default VAT rates cannot be deleted!")

        try:
            db.Session.execute(
                delete(_Service).where(_Service.id == service_id)
            )
        except IntegrityError:
            in_use = db.Session.scalars(
                select(_Service.name)
                .join(_Service.service)
                .where(_Service.service_id == service_id)
            ).first()
            raise db.RejectedCommand(f"VAT rate with id {service_id} is used"
                                     f" by ay least {in_use} service!")
        else:
            db.Session.commit()
