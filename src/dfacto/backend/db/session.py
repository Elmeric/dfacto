# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import sqlite3 as sqlite
from pathlib import Path

import sqlalchemy as sa
import sqlalchemy.event
import sqlalchemy.orm


def _set_sqlite_pragma(dbapi_connection, _connection_record):  # type: ignore
    if isinstance(dbapi_connection, sqlite.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def configure_session(db_path: Path) -> sa.Engine:
    engine = sa.create_engine(f"sqlite+pysqlite:///{db_path}")
    sa.event.listen(engine, "connect", _set_sqlite_pragma)
    session_factory.configure(bind=engine)
    return engine


session_factory = sa.orm.sessionmaker()
