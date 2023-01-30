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

from dfacto.models.command import CommandResponse, CommandStatus
from dfacto.models import crud, models, schemas


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
        if self.Session.scalars(sa.select(models._VatRate)).first() is None:
            # No VAT rates in the database: create them.
            self.Session.execute(sa.insert(models._VatRate), VatRateModel.PRESET_RATES)
            self.Session.commit()

    def reset(self) -> CommandResponse:
        report = None
        self.Session.execute(sa.update(models._VatRate), VatRateModel.PRESET_RATES)
        try:
            # TODO: Limit delete to the non-used VAT rates.
            self.Session.execute(
                sa.delete(models._VatRate)
                .where(models._VatRate.id.not_in(VatRateModel.PRESET_RATE_IDS))
            )
        except sa.exc.IntegrityError:
            # Some non-preset VAT rates are in use: keep them all!
            report = CommandResponse(
                CommandStatus.COMPLETED,
                "VAT_RATE-RESET - Some VAT rate are in-use: all are kept."
            )
        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError:
            self.Session.rollback()
            return CommandResponse(
                CommandStatus.FAILED,
                "VAT_RATE-RESET - SQL error while resetting VAT rates.",
            )
        else:
            report = report or CommandResponse(CommandStatus.COMPLETED)
            return report

    def get(self, vat_rate_id: Optional[int] = None) -> CommandResponse:
        id_ = vat_rate_id or VatRateModel.DEFAULT_RATE_ID
        try:
            vat_rate = crud.vat_rate.get(self.Session, id_)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"VAT_RATE-GET - SQL or database error: {exc}",
            )
        else:
            if vat_rate is None:
                body = None
            else:
                body = schemas.VatRate.from_orm(vat_rate)
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_multi(self, skip: int = 0, limit: int = 10) -> CommandResponse:
        try:
            vat_rates = crud.vat_rate.get_multi(self.Session, skip=skip, limit=limit)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"VAT_RATE-GET-MULTI - SQL or database error: {exc}",
            )
        else:
            body = [schemas.VatRate.from_orm(vat_rate) for vat_rate in vat_rates]
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def add(self, vr_in: schemas.VatRateCreate) -> CommandResponse:
        try:
            vat_rate = crud.vat_rate.create(self.Session, obj_in=vr_in)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"VAT_RATE-ADD - Cannot add VAT rate {vr_in.rate}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED, body=vat_rate)

    def update(self, vat_rate_id: int, vr_in: schemas.VatRateUpdate) -> CommandResponse:
        vat_rate = crud.vat_rate.get(self.Session, vat_rate_id)
        if vat_rate is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"VAT_RATE-UPDATE - VAT rate {vat_rate_id} not found.",
            )

        try:
            vat_rate = crud.vat_rate.update(self.Session, db_obj=vat_rate, obj_in=vr_in)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"VAT_RATE-UPDATE - Cannot update VAT rate {vat_rate_id}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED, body=vat_rate)

    def delete(self, vat_rate_id: int) -> CommandResponse:
        if vat_rate_id in VatRateModel.PRESET_RATE_IDS:
            return CommandResponse(
                CommandStatus.REJECTED,
                "VAT_RATE-DELETE - Default VAT rates cannot be deleted.",
            )

        vat_rate = crud.vat_rate.get(self.Session, vat_rate_id)
        if vat_rate is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"VAT_RATE-DELETE - VAT rate {vat_rate_id} not found.",
            )

        try:
            vat_rate = crud.vat_rate.delete(self.Session, id_=vat_rate_id)
        except crud.CrudIntegrityError:
            in_use = self.Session.scalars(
                sa.select(models._Service)
                # .join(_Service.vat_rate)
                .where(models._Service.vat_rate_id == vat_rate_id)
            ).first()
            return CommandResponse(
                CommandStatus.REJECTED,
                f"VAT_RATE-DELETE - VAT rate with id {vat_rate_id} is used"
                f" by at least '{in_use.name}' service.",
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"VAT_RATE-DELETE - Cannot delete VAT rate {vat_rate_id}: {exc}",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED, body=vat_rate)
