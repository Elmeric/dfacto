# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import sqlite3 as sqlite
from decimal import Decimal
from pathlib import Path
from typing import TypedDict

import sqlalchemy as sa
from sqlalchemy.event import listen
from sqlalchemy.orm import Session

from dfacto.backend import models


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


class PresetGlobals(TypedDict):
    due_delta: int
    penalty_rate: Decimal
    discount_rate: Decimal


PRESET_GLOBALS: list[PresetGlobals] = [
    {"due_delta": 30, "penalty_rate": Decimal("12.0"), "discount_rate": Decimal("1.5")},
]


def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore
    if isinstance(dbapi_connection, sqlite.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _create_tables(engine: sa.Engine) -> None:
    models.BaseModel.metadata.create_all(bind=engine)


def init_db_data(session: Session) -> None:
    if session.scalars(sa.select(models.VatRate)).first() is None:
        # No VAT rates in the database: add the presets and mark "taux zéro" as default.
        session.execute(sa.insert(models.VatRate), PRESET_RATES)
    if session.scalars(sa.select(models.Globals)).first() is None:
        # No invoices'globals in the database: add them.
        session.execute(sa.insert(models.Globals), PRESET_GLOBALS)
    session.commit()


def _init_database(engine: sa.Engine) -> None:
    _create_tables(engine)
    session = session_factory()
    init_db_data(session)
    session.close()


def configure_session(db_path: Path, *, is_new: bool) -> None:
    engine = sa.create_engine(f"sqlite+pysqlite:///{db_path}")
    listen(engine, "connect", _set_sqlite_pragma)
    session_factory.configure(bind=engine)
    if is_new:
        _init_database(engine)


session_factory = sa.orm.sessionmaker()
