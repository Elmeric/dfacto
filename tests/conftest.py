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
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker  # , Session

from dfacto.models.db import BaseModel


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
    session_factory = sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    Session = scoped_session(session_factory)

    # yield session
    yield Session

    # session.close()
    Session.remove()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()


@pytest.fixture()
def mock_commit(monkeypatch):
    state = {"failed": False}
    called = []

    def _commit(_):
        called.append(True)
        if state["failed"]:
            raise SQLAlchemyError("Commit failed")

    monkeypatch.setattr("dfacto.models.crud.base.scoped_session.commit", _commit)

    return state, called


@pytest.fixture()
def mock_get(monkeypatch):
    state = {"failed": False}
    called = []

    def _get(_1, _2, _3):
        called.append(True)
        if state["failed"]:
            raise SQLAlchemyError("Get failed")

    monkeypatch.setattr("dfacto.models.crud.base.scoped_session.get", _get)

    return state, called


@pytest.fixture()
def mock_select(monkeypatch):
    state = {"failed": False}
    called = []

    def _select(_):
        called.append(True)
        if state["failed"]:
            raise SQLAlchemyError("Select failed")

    monkeypatch.setattr("dfacto.models.crud.base.select", _select)

    return state, called
