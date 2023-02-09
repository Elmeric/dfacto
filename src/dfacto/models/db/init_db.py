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
    id: int
    rate: float


DEFAULT_RATE_ID: int = 1
PRESET_RATES: list[PresetRate] = [
    {"id": DEFAULT_RATE_ID, "rate": 0.0},
    {"id": DEFAULT_RATE_ID + 1, "rate": 5.5},
    {"id": DEFAULT_RATE_ID + 2, "rate": 20.0},
]


def create_tables(engine: sa.Engine) -> None:
    base.BaseModel.metadata.create_all(bind=engine)


def init_db_data(session: Union[Session, scoped_session]) -> None:
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
        # No VAT rates in the database: create them.
        session.execute(sa.insert(models.VatRate), PRESET_RATES)
        session.commit()


def init_db(engine: sa.Engine, session: Union[Session, scoped_session]) -> None:
    create_tables(engine)
    init_db_data(session)
