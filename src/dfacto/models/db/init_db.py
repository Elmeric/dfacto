# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TypedDict, Union

import sqlalchemy as sa
from sqlalchemy.orm import Session, scoped_session

from dfacto.models import models
from dfacto.models.db import base


class PresetRate(TypedDict):
    name: str
    rate: float
    is_default: bool
    is_preset: bool


PRESET_RATES: list[PresetRate] = [
    {"name": "taux zéro", "rate": 0.0, "is_default": True, "is_preset": True},
    {"name": "taux particulier", "rate": 2.1, "is_default": False, "is_preset": True},
    {"name": "taux réduit", "rate": 5.5, "is_default": False, "is_preset": True},
    {"name": "taux intermédiaire", "rate": 10, "is_default": False, "is_preset": True},
    {"name": "taux normal", "rate": 20, "is_default": False, "is_preset": True},
]


def create_tables(engine: sa.Engine) -> None:
    base.BaseModel.metadata.create_all(bind=engine)


def init_db_data(session: Union[Session, scoped_session[Session]]) -> None:
    # vr = crud.vat_rate.get(db, DEFAULT_RATE_ID)
    # if vr is None:
    #     # No VAT rates in the database: create them.
    #     for vat_rate in PRESET_RATES:
    #         crud.vat_rate.create(
    #             db,
    #             obj_in=schemas.VatRate(
    #                 id=vat_rate["id"],
    #                 rate=vat_rate["rate"]
    #             )
    #         )
    if session.scalars(sa.select(models.VatRate)).first() is None:
        # No VAT rates in the database: add the presets and mark "taux zéro" as default.
        session.execute(sa.insert(models.VatRate), PRESET_RATES)
        session.commit()


def init_db(
    engine: sa.Engine, session: Union[Session, scoped_session[Session]]
) -> None:
    create_tables(engine)
    init_db_data(session)
