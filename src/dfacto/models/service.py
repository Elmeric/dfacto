# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc
import sqlalchemy.orm

from dfacto.models.model import CommandReport, CommandStatus, _Service
from dfacto.models.vat_rate import VatRate, VatRateModel


@dataclass()
class Service:
    id: int
    name: str
    unit_price: float
    vat_rate: VatRate


@dataclass()
class ServiceModel:
    Session: sa.orm.scoped_session
    vat_rate_model: VatRateModel

    def get(self, service_id: int) -> Optional[Service]:
        service: Optional[_Service] = self.Session.get(_Service, service_id)
        if service is None:
            return
        return Service(
            service.id,
            service.name,
            service.unit_price,
            VatRate(service.vat_rate_id, service.vat_rate.rate),
        )

    def list_all(self) -> list[Service]:
        return [
            Service(
                service.id,
                service.name,
                service.unit_price,
                VatRate(service.vat_rate_id, service.vat_rate.rate),
            )
            for service in self.Session.scalars(sa.select(_Service)).all()
        ]

    def add(
        self,
        name: str,
        unit_price: float,
        vat_rate_id: int = VatRateModel.DEFAULT_RATE_ID,
    ) -> CommandReport:
        service = _Service(name=name, unit_price=unit_price, vat_rate_id=vat_rate_id)
        self.Session.add(service)
        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandReport(
                CommandStatus.FAILED, f"SERVICE-ADD - Cannot add service {name}: {exc}"
            )

        else:
            return CommandReport(CommandStatus.COMPLETED)

    def update(
        self,
        service_id: int,
        name: Optional[str] = None,
        unit_price: Optional[float] = None,
        vat_rate_id: Optional[int] = None,
    ) -> CommandReport:
        service: Optional[_Service] = self.Session.get(_Service, service_id)

        if service is None:
            return CommandReport(
                CommandStatus.FAILED,
                f"SERVICE-UPDATE - Service {service_id} not found.",
            )

        if name is not None and name != service.name:
            service.name = name

        if unit_price is not None and unit_price != service.unit_price:
            service.unit_price = unit_price

        if vat_rate_id is not None and vat_rate_id != service.vat_rate_id:
            service.vat_rate_id = self.vat_rate_model.get(vat_rate_id).id

        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandReport(
                CommandStatus.FAILED,
                f"SERVICE-UPDATE - Cannot update service {service.name}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)

    def delete(self, service_id: int) -> CommandReport:
        self.Session.execute(sa.delete(_Service).where(_Service.id == service_id))
        try:
            self.Session.commit()
        except sa.exc.IntegrityError:
            return CommandReport(
                CommandStatus.REJECTED,
                f"SERVICE-DELETE - Service with id {service_id}"
                f" is used by at least one invoice's item!",
            )
        except sa.exc.SQLAlchemyError:
            return CommandReport(
                CommandStatus.FAILED,
                f"SERVICE-DELETE - SQL error while deleting service {service_id}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)
