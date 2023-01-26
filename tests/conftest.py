# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Cf. https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2

from sqlite3 import Connection as SQLite3Connection

import pytest
from sqlalchemy import create_engine
from sqlalchemy.event import listen
from sqlalchemy.orm import scoped_session, sessionmaker  # , Session
from sqlalchemy.exc import SQLAlchemyError

from dfacto.models.model import BaseModel
from dfacto.models.vat_rate import VatRateModel


def _set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        # print("Execute: PRAGMA foreign_keys=ON")
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # cursor.execute("PRAGMA journal_mode = OFF")
        cursor.close()


# https://github.com/sqlalchemy/sqlalchemy/issues/7716
# https://docs.sqlalchemy.org/en/14/dialects/sqlite.html#pysqlite-serializable
# @event.listens_for(engine, "connect")
def do_connect(dbapi_connection, connection_record):
    # disable pysqlite's emitting of the BEGIN statement entirely.
    # also stops it from emitting COMMIT before any DDL.
    dbapi_connection.isolation_level = None


# @event.listens_for(engine, "begin")
def do_begin(conn):
    # emit our own BEGIN
    conn.exec_driver_sql("BEGIN")


@pytest.fixture(scope="session")
def engine():
    # engine = create_engine(
    #     r"sqlite+pysqlite:///F:\Users\Documents\Python\dfacto_test.db"
    # )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    listen(engine, "connect", _set_sqlite_pragma)
    listen(engine, "connect", do_connect)
    listen(engine, "begin", do_begin)
    return engine


@pytest.fixture(scope="session")
def tables(engine):
    BaseModel.metadata.create_all(engine)
    yield
    BaseModel.metadata.drop_all(engine)


@pytest.fixture
def dbsession(engine, tables):
    """Returns a sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    # session = Session(bind=connection, join_transaction_mode="create_savepoint")
    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    Session = scoped_session(session_factory)

    # yield session
    yield Session

    # session.close()
    Session.remove()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()


@pytest.fixture
def vat_rate_model(dbsession):
    return VatRateModel(dbsession)
