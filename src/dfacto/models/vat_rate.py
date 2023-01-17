# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
# from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TypedDict

import sqlalchemy as sa
import sqlalchemy.exc

from dfacto.models import db, model


class PresetRate(TypedDict):
    id: int
    rate: float


DEFAULT_RATE_ID: int = 1
PRESET_RATES: list[PresetRate] = [
    {"id": DEFAULT_RATE_ID, "rate": 0.0},
    {"id": DEFAULT_RATE_ID + 1, "rate": 5.5},
    {"id": DEFAULT_RATE_ID + 2, "rate": 20.0},
]
PRESET_RATE_IDS: tuple[int, ...] = tuple([rate["id"] for rate in PRESET_RATES])
print(PRESET_RATE_IDS)


@dataclass()
class VatRate:
    id: int
    rate: float


def init() -> None:
    if db.Session.scalars(sa.select(model._VatRate)).first() is None:
        # No VAT rates in the database: create them.
        db.Session.execute(sa.insert(model._VatRate), PRESET_RATES)
        db.Session.commit()


def reset() -> None:
    try:
        db.Session.execute(
            sa.delete(model._VatRate).where(model._VatRate.id.not_in(PRESET_RATE_IDS))
        )
    except sa.exc.IntegrityError:
        # Some non-preset VAT rates are in use: keep them all!
        pass
    except sa.exc.SQLAlchemyError:
        raise db.FailedCommand(f"VAT_RATE-RESET - SQL error while resetting VAT rates.")
    finally:
        db.Session.execute(sa.update(model._VatRate), PRESET_RATES)
        db.Session.commit()


def get_default() -> VatRate:
    return get(DEFAULT_RATE_ID)


def get(vat_rate_id: Optional[int] = None) -> VatRate:
    id_ = vat_rate_id or DEFAULT_RATE_ID
    vat_rate: model._VatRate = db.Session.get(model._VatRate, id_)
    if vat_rate is None:
        raise db.FailedCommand(f"VAT_RATE-GET - VAT rate {vat_rate_id} not found.")
    return VatRate(vat_rate.id, vat_rate.rate)


def list_all() -> list[VatRate]:
    return [
        VatRate(vat_rate.id, vat_rate.rate)
        for vat_rate in db.Session.scalars(sa.select(model._VatRate)).all()
    ]


def add(rate: float) -> VatRate:
    vat_rate = model._VatRate(rate=rate)
    db.Session.add(vat_rate)
    try:
        db.Session.commit()
    except sa.exc.SQLAlchemyError as exc:
        db.Session.rollback()
        raise db.FailedCommand(f"VAT_RATE-ADD - Cannot add VAT rate {rate}: {exc}")
    else:
        return VatRate(vat_rate.id, vat_rate.rate)


def update(vat_rate_id: int, rate: float) -> VatRate:
    vat_rate: model._VatRate = db.Session.get(model._VatRate, vat_rate_id)
    if vat_rate is None:
        raise db.FailedCommand(f"VAT_RATE-UPDATE - VAT rate {vat_rate_id} not found.")

    if vat_rate.rate != rate:
        vat_rate.rate = rate
        try:
            db.Session.commit()
        except sa.exc.SQLAlchemyError as exc:
            raise db.FailedCommand(
                f"VAT_RATE-UPDATE - Cannot update VAT rate {vat_rate_id}: {exc}"
            )

    return VatRate(vat_rate.id, vat_rate.rate)


def delete(vat_rate_id: int) -> None:
    if vat_rate_id in PRESET_RATE_IDS:
        raise db.RejectedCommand(
            "VAT_RATE-DELETE - Default VAT rates cannot be deleted!"
        )

    try:
        db.Session.execute(
            sa.delete(model._VatRate).where(model._VatRate.id == vat_rate_id)
        )
    except sa.exc.IntegrityError:
        # in_use = db.Session.scalars(
        #     sa.select(_Service.name)
        #     .join(_Service.vat_rate)
        #     .where(_Service.vat_rate_id == vat_rate_id)
        # ).first()
        raise db.RejectedCommand(
            f"VAT_RATE-DELETE - VAT rate with id {vat_rate_id} is used"
            f" by at least one service!"
        )
    except sa.exc.SQLAlchemyError:
        raise db.FailedCommand(
            f"VAT_RATE-DELETE - SQL error while deleting VAT rate {vat_rate_id}"
        )
    else:
        db.Session.commit()
