# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc

from dfacto.models import db, model, vat_rate


@dataclass()
class Service:
    id: int
    name: str
    unit_price: float
    vat_rate: vat_rate.VatRate


def get(service_id: int) -> Service:
    service: model._Service = db.Session.get(model._Service, service_id)
    if service is None:
        raise db.FailedCommand(f"SERVICE-GET - Service {service_id} not found.")
    return Service(
        service.id,
        service.name,
        service.unit_price,
        vat_rate.VatRate(service.vat_rate_id, service.vat_rate.rate),
    )


def list_all() -> list[Service]:
    return [
        Service(
            service.id,
            service.name,
            service.unit_price,
            vat_rate.VatRate(service.vat_rate_id, service.vat_rate.rate),
        )
        for service in db.Session.scalars(sa.select(model._Service)).all()
    ]


def add(
    name: str, unit_price: float, vat_rate_id: int = vat_rate.DEFAULT_RATE_ID
) -> Service:
    service = model._Service(name=name, unit_price=unit_price, vat_rate_id=vat_rate_id)
    db.Session.add(service)
    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(f"SERVICE-ADD - Cannot add service {name}: {exc}")
    else:
        return Service(
            service.id,
            service.name,
            service.unit_price,
            vat_rate.VatRate(service.vat_rate_id, service.vat_rate.rate),
        )


def update(
    service_id: int,
    name: Optional[str] = None,
    unit_price: Optional[float] = None,
    vat_rate_id: Optional[int] = None,
) -> Service:
    service: model._Service = db.Session.get(model._Service, service_id)

    if service is None:
        raise db.FailedCommand(f"SERVICE-UPDATE - Service {service_id} not found.")

    if name is not None and name != service.name:
        service.name = name

    if unit_price is not None and unit_price != service.unit_price:
        service.unit_price = unit_price

    if vat_rate_id is not None and vat_rate_id != service.vat_rate_id:
        service.vat_rate_id = vat_rate.get(vat_rate_id).id

    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(
            f"SERVICE-UPDATE - Cannot update service {service.name}: {exc}"
        )
    else:
        return Service(
            service.id,
            service.name,
            service.unit_price,
            vat_rate.VatRate(service.vat_rate_id, service.vat_rate.rate),
        )


def delete(service_id: int) -> None:
    db.Session.execute(sa.delete(model._Service).where(model._Service.id == service_id))
    try:
        db.Session.commit()
    except sa.exc.IntegrityError:
        raise db.RejectedCommand(
            f"SERVICE-DELETE - Service with id {service_id} is used by at least one invoice's item!"
        )
    except sa.exc.SQLAlchemyError:
        raise db.FailedCommand(
            f"SERVICE-DELETE - SQL error while deleting service {service_id}"
        )
