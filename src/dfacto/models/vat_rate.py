# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import IntegrityError

from dfacto.models import db
from dfacto.models.service import _Service


class _VatRate(db.BaseModel):
    __tablename__ = "vat_rate"

    id: Mapped[db.intpk] = mapped_column(init=False)
    rate: Mapped[float]


@dataclass()
class VatRate:
    id: int
    rate: float


class VatRateModel:
    DEFAULT_RATE_ID: int = 1
    PRESET_RATE_IDS: tuple[int] = (
        DEFAULT_RATE_ID, DEFAULT_RATE_ID + 1, DEFAULT_RATE_ID + 2
    )

    def __init__(self) -> None:
        self._init_vat_rates()

    def _init_vat_rates(self):
        if db.Session.scalars(select(_VatRate)).first() is None:
            # No VAT rates in the database: create them.
            vat_rates = db.Session.scalars(
                insert(_VatRate).returning(_VatRate),
                [
                    {"id": self.DEFAULT_RATE_ID, "rate": 0.0},
                    {"id": self.DEFAULT_RATE_ID + 1, "rate": 5.5},
                    {"id": self.DEFAULT_RATE_ID + 2, "rate": 20.0},
                ],
            )
            db.Session.commit()

    def reset_vat_rates(self) -> None:
        try:
            db.Session.execute(
                delete(_VatRate)
                .where(_VatRate.id.not_in(self.PRESET_RATE_IDS))
            )
        except IntegrityError:
            # Some non-preset VAT rates are in use: keep them all!
            pass
        finally:
            db.Session.execute(
                update(_VatRate),
                [
                    {"id": self.DEFAULT_RATE_ID, "rate": 0.0},
                    {"id": self.DEFAULT_RATE_ID + 1, "rate": 5.5},
                    {"id": self.DEFAULT_RATE_ID + 2, "rate": 20.0},
                ],
            )
            db.Session.commit()

    @classmethod
    def get_default_vat_rate(cls) -> Optional[_VatRate]:
        return db.Session.get(_VatRate, cls.DEFAULT_RATE_ID)

    def get_vat_rate(self, vat_rate_id: int = None) -> Optional[VatRate]:
        id_ = vat_rate_id or self.DEFAULT_RATE_ID
        vat_rate = db.Session.get(_VatRate, id_)
        if vat_rate is None:
            raise db.RejectedCommand(f"Cannot find a VAT rate with {vat_rate_id} id!")
        return VatRate(vat_rate.id, vat_rate.rate)

    @staticmethod
    def list_vat_rates() -> list[VatRate]:
        return [VatRate(v.id, v.rate) for v in db.Session.scalars(select(_VatRate)).all()]

    @staticmethod
    def add_vat_rate(rate: float) -> VatRate:
        v = _VatRate(rate=rate)
        db.Session.add(v)
        db.Session.commit()
        return VatRate(v.id, v.rate)

    @staticmethod
    def update_vat_rate(vat_rate_id: int, rate: float) -> VatRate:
        v = db.Session.get(_VatRate, vat_rate_id)
        v.rate = rate
        # db.Session.execute(
        #     update(_VatRate),
        #     [{"id": vat_rate_id, "rate": rate}]
        # )
        db.Session.commit()
        return VatRate(vat_rate_id, rate)

    def delete_vat_rate(self, vat_rate_id: int) -> None:
        if vat_rate_id in self.PRESET_RATE_IDS:
            raise db.RejectedCommand("Default VAT rates cannot be deleted!")

        try:
            db.Session.execute(
                delete(_VatRate).where(_VatRate.id == vat_rate_id)
            )
        except IntegrityError:
            in_use = db.Session.scalars(
                select(_Service.name)
                .join(_Service.vat_rate)
                .where(_Service.vat_rate_id == vat_rate_id)
            ).first()
            raise db.RejectedCommand(f"VAT rate with id {vat_rate_id} is used"
                                     f" by ay least {in_use} service!")
        else:
            db.Session.commit()
