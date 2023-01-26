# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
# from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional, TypedDict

import sqlalchemy as sa
import sqlalchemy.exc
from sqlalchemy.orm import scoped_session

from dfacto.models.model import CommandReport, CommandStatus, _VatRate, _Service
from dfacto.models.schema import VatRate, VatRateCreate, VatRateUpdate
from dfacto.models.crud import crud_vat_rate, CrudError, CrudIntegrityError


class PresetRate(TypedDict):
    id: int
    rate: float


@dataclass()
class VatRateModel:
    Session: scoped_session

    DEFAULT_RATE_ID: ClassVar[int] = 1
    PRESET_RATES: ClassVar[list[PresetRate]] = [
        {"id": DEFAULT_RATE_ID, "rate": 0.0},
        {"id": DEFAULT_RATE_ID + 1, "rate": 5.5},
        {"id": DEFAULT_RATE_ID + 2, "rate": 20.0},
    ]
    PRESET_RATE_IDS: ClassVar[tuple[int, ...]] = tuple(
        [rate["id"] for rate in PRESET_RATES]
    )

    def __post_init__(self) -> None:
        if self.Session.scalars(sa.select(_VatRate)).first() is None:
            # No VAT rates in the database: create them.
            self.Session.execute(sa.insert(_VatRate), VatRateModel.PRESET_RATES)
            self.Session.commit()

    def reset(self) -> CommandReport:
        report = None
        self.Session.execute(sa.update(_VatRate), VatRateModel.PRESET_RATES)
        try:
            # TODO: Limit delete to the non-used VAT rates.
            self.Session.execute(
                sa.delete(_VatRate)
                .where(_VatRate.id.not_in(VatRateModel.PRESET_RATE_IDS))
            )
        except sa.exc.IntegrityError:
            # Some non-preset VAT rates are in use: keep them all!
            report = CommandReport(
                CommandStatus.COMPLETED,
                "VAT_RATE-RESET - Some VAT rate are in-use: all are kept."
            )
        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError:
            self.Session.rollback()
            return CommandReport(
                CommandStatus.FAILED,
                "VAT_RATE-RESET - SQL error while resetting VAT rates.",
            )
        else:
            report = report or CommandReport(CommandStatus.COMPLETED)
            return report

    def get(self, vat_rate_id: Optional[int] = None) -> Optional[VatRate]:
        id_ = vat_rate_id or VatRateModel.DEFAULT_RATE_ID
        vat_rate = crud_vat_rate.get(self.Session, id_)
        if vat_rate is None:
            return None
        return VatRate.from_orm(vat_rate)

    def get_multi(self, skip: int = 0, limit: int = 10) -> list[VatRate]:
        return [
            VatRate.from_orm(vat_rate)
            for vat_rate in crud_vat_rate.get_multi(self.Session, skip, limit)
        ]

    def add(self, vr_in: VatRateCreate) -> CommandReport:
        try:
            _vat_rate = crud_vat_rate.create(self.Session, obj_in=vr_in)
        except CrudError as exc:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-ADD - Cannot add VAT rate {vr_in.rate}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)

    def update(self, vat_rate_id: int, vr_in: VatRateUpdate) -> CommandReport:
        vat_rate = crud_vat_rate.get(self.Session, vat_rate_id)
        if vat_rate is None:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-UPDATE - VAT rate {vat_rate_id} not found.",
            )

        try:
            _vat_rate = crud_vat_rate.update(self.Session, db_obj=vat_rate, obj_in=vr_in)
        except CrudError as exc:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-UPDATE - Cannot update VAT rate {vat_rate_id}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)

    def delete(self, vat_rate_id: int) -> CommandReport:
        if vat_rate_id in VatRateModel.PRESET_RATE_IDS:
            return CommandReport(
                CommandStatus.REJECTED,
                "VAT_RATE-DELETE - Default VAT rates cannot be deleted.",
            )

        vat_rate = crud_vat_rate.get(self.Session, vat_rate_id)
        if vat_rate is None:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-DELETE - VAT rate {vat_rate_id} not found.",
            )

        try:
            _vat_rate = crud_vat_rate.delete(self.Session, db_obj=vat_rate)
        except CrudIntegrityError:
            in_use = self.Session.scalars(
                sa.select(_Service)
                # .join(_Service.vat_rate)
                .where(_Service.vat_rate_id == vat_rate_id)
            ).first()
            return CommandReport(
                CommandStatus.REJECTED,
                f"VAT_RATE-DELETE - VAT rate with id {vat_rate_id} is used"
                f" by at least '{in_use.name}' service.",
            )
        except CrudError as exc:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-DELETE - Cannot delete VAT rate {vat_rate_id}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)
