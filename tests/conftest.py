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


#
# Mock some methods of the sqlalchemy 'scoped_session'
#
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


#
# Mock some methods of the CRUDBase class used by all DFactoModel command API
#
@pytest.fixture()
def mock_dfacto_model(monkeypatch):
    state = {"raises": {}, "read_value": None}
    methods_called = []

    def _get(_, _db, _id):
        methods_called.append("GET")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _get_multi(_, _db, *, skip: int = 0, limit: int = 100):
        methods_called.append("GET_MULTI")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"][skip: skip + limit]

    def _get_all(_, _db):
        methods_called.append("GET_ALL")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _create(_, _db, *, obj_in: schemas.ServiceCreate):
        methods_called.append("CREATE")
        exc = state["raises"]["CREATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            obj_in.id = 1
            return obj_in

    def _update(
        _,
        _db,
        *,
        db_obj,
        obj_in: Union[schemas.ServiceUpdate, dict[str, Any]]
    ):
        methods_called.append("UPDATE")
        exc = state["raises"]["UPDATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            obj_data = dataclasses.asdict(db_obj)
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.flatten()
                # update_data = dataclasses.asdict(obj_in)
            for field in obj_data:
                if (
                    field in update_data
                    and update_data[field] is not None
                    and getattr(db_obj, field) != update_data[field]
                ):
                    setattr(db_obj, field, update_data[field])
            return db_obj

    def _delete(_, db: scoped_session, *, db_obj: dict[str, Any]) -> None:
        methods_called.append("DELETE")
        exc = state["raises"]["DELETE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return

    monkeypatch.setattr(crud.base.CRUDBase, "get", _get)
    monkeypatch.setattr(crud.base.CRUDBase, "get_multi", _get_multi)
    monkeypatch.setattr(crud.base.CRUDBase, "get_all", _get_all)
    monkeypatch.setattr(crud.base.CRUDBase, "create", _create)
    monkeypatch.setattr(crud.base.CRUDBase, "update", _update)
    monkeypatch.setattr(crud.base.CRUDBase, "delete", _delete)

    return state, methods_called


@dataclasses.dataclass
class FakeORMModel:
    id: int
