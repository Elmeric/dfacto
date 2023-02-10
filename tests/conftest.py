# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Cf. https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2

from typing import Union, Any, Type
import dataclasses

from sqlite3 import Connection as SQLite3Connection

import pytest
from sqlalchemy import create_engine
from sqlalchemy.event import listen
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker  # , Session

from dfacto.models import db, crud, schemas


def _set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
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
    db.BaseModel.metadata.create_all(engine)
    yield
    db.BaseModel.metadata.drop_all(engine)


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


class FakeCRUDBase(crud.CRUDBase):
    def __init__(
        self,
        *,
        raises: dict[
            str,
            Union[bool, Union[Type[crud.CrudError], Type[crud.CrudIntegrityError]]]
        ],
        read_value: Any = None
    ):
        self.raises = raises
        self.read_value = read_value
        self.methods_called = []

    def get(self, _db, _id):
        self.methods_called.append("GET")
        exc = self.raises["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return self.read_value

    def get_multi(self, _db, *, skip: int = 0, limit: int = 100):
        self.methods_called.append("GET_MULTI")
        exc = self.raises["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return self.read_value[skip: skip + limit]

    def get_all(self, _db):
        self.methods_called.append("GET_ALL")
        exc = self.raises["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return self.read_value

    def create(self, _db, *, obj_in: schemas.ServiceCreate):
        self.methods_called.append("CREATE")
        exc = self.raises["CREATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            obj_in.id = 1
            return obj_in

    def update(
        self,
        _db,
        *,
        db_obj: dict[str, Any],
        obj_in: Union[schemas.ServiceUpdate, dict[str, Any]]
    ):
        self.methods_called.append("UPDATE")
        exc = self.raises["UPDATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = dataclasses.asdict(obj_in)
            for field in db_obj:
                if (
                    field in update_data
                    and update_data[field] is not None
                    and db_obj[field] != update_data[field]
                ):
                    db_obj[field] = update_data[field]
            return db_obj

    def delete(self, db: scoped_session, *, db_obj: dict[str, Any]) -> None:
        self.methods_called.append("DELETE")
        exc = self.raises["DELETE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return
