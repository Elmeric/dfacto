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
import sqlalchemy.orm

from dfacto.models.model import CommandReport, CommandStatus, _VatRate


class PresetRate(TypedDict):
    id: int
    rate: float


@dataclass()
class VatRate:
    id: int
    rate: float


@dataclass()
class VatRateModel:
    Session: sa.orm.scoped_session

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
        try:
            self.Session.execute(
                sa.delete(_VatRate).where(
                    _VatRate.id.not_in(VatRateModel.PRESET_RATE_IDS)
                )
            )
        except sa.exc.IntegrityError:
            # Some non-preset VAT rates are in use: keep them all!
            pass
        except sa.exc.SQLAlchemyError:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-RESET - SQL error while resetting VAT rates.",
            )
        else:
            self.Session.execute(sa.update(_VatRate), VatRateModel.PRESET_RATES)
            self.Session.commit()
            return CommandReport(CommandStatus.COMPLETED)

    def get_default(self) -> VatRate:
        return self.get(VatRateModel.DEFAULT_RATE_ID)

    def get(self, vat_rate_id: Optional[int] = None) -> Optional[VatRate]:
        id_ = vat_rate_id or VatRateModel.DEFAULT_RATE_ID
        vat_rate: Optional[_VatRate] = self.Session.get(_VatRate, id_)
        if vat_rate is None:
            return
        return VatRate(vat_rate.id, vat_rate.rate)

    def list_all(self) -> list[VatRate]:
        return [
            VatRate(vat_rate.id, vat_rate.rate)
            for vat_rate in self.Session.scalars(sa.select(_VatRate)).all()
        ]

    def add(self, rate: float) -> CommandReport:
        vat_rate = _VatRate(rate=rate)
        self.Session.add(vat_rate)
        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            self.Session.rollback()
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-ADD - Cannot add VAT rate {rate}: {exc}",
            )
        else:
            return CommandReport(CommandStatus.COMPLETED)

    def update(self, vat_rate_id: int, rate: float) -> CommandReport:
        vat_rate: Optional[_VatRate] = self.Session.get(_VatRate, vat_rate_id)
        if vat_rate is None:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-UPDATE - VAT rate {vat_rate_id} not found.",
            )

        if vat_rate.rate != rate:
            vat_rate.rate = rate
            try:
                self.Session.commit()
            except sa.exc.SQLAlchemyError as exc:
                return CommandReport(
                    CommandStatus.FAILED,
                    f"VAT_RATE-UPDATE - Cannot update VAT rate {vat_rate_id}: {exc}",
                )

        return CommandReport(CommandStatus.COMPLETED)

    def delete(self, vat_rate_id: int) -> CommandReport:
        if vat_rate_id in VatRateModel.PRESET_RATE_IDS:
            return CommandReport(
                CommandStatus.REJECTED,
                "VAT_RATE-DELETE - Default VAT rates cannot be deleted!",
            )

        try:
            self.Session.execute(sa.delete(_VatRate).where(_VatRate.id == vat_rate_id))
        except sa.exc.IntegrityError:
            # in_use = self.Session.scalars(
            #     sa.select(_Service.name)
            #     .join(_Service.vat_rate)
            #     .where(_Service.vat_rate_id == vat_rate_id)
            # ).first()
            return CommandReport(
                CommandStatus.REJECTED,
                f"VAT_RATE-DELETE - VAT rate with id {vat_rate_id} is used"
                f" by at least one service!",
            )
        except sa.exc.SQLAlchemyError:
            return CommandReport(
                CommandStatus.FAILED,
                f"VAT_RATE-DELETE - SQL error while deleting VAT rate {vat_rate_id}",
            )
        else:
            self.Session.commit()
            return CommandReport(CommandStatus.COMPLETED)
