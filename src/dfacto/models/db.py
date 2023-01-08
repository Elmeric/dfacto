# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from contextlib import contextmanager
from sqlite3 import Connection as SQLite3Connection
from typing import Annotated

import sqlalchemy as sa
import sqlalchemy.event as sa_evt
import sqlalchemy.orm as sa_orm
import sqlalchemy.exc as sa_exc

intpk = Annotated[int, sa_orm.mapped_column(primary_key=True)]


class CommandException(Exception):
    """Base command exception."""


class RejectedCommand(CommandException):
    """Indicates that the command is rejected."""


class FailedCommand(CommandException):
    """Indicates that the command has failed."""


def _set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        print("Execute: PRAGMA foreign_keys=ON")
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # dbapi_connection.execute('PRAGMA foreign_keys = ON')


print(f"**************** CREATING ENGINE ****************")
# engine = sa.create_engine("sqlite+pysqlite:///:memory:", echo=True)
# try:
#     os.remove('dcfs_data/dcfs.db')
# except OSError:
#     pass
engine = sa.create_engine("sqlite+pysqlite:///dfacto.db")
# engine = sa.create_engine('sqlite+pysqlite:///dfacto.db', echo=True)
sa_evt.listen(engine, "connect", _set_sqlite_pragma)
session_factory = sa_orm.sessionmaker(bind=engine)
Session = sa_orm.scoped_session(session_factory)
print(f"Importing db.py: {engine} {id(engine)}", Session)


class BaseModel(sa_orm.MappedAsDataclass, sa_orm.DeclarativeBase):
    pass


def create_schema():
    print(f"Creating db schema: {engine} {id(engine)}", Session)
    BaseModel.metadata.create_all(engine)


@contextmanager
def command_context():
    try:
        print(f'Creating cmdCtxt: {engine}, {id(engine)}, {Session}')
        yield Session
        Session.commit()
    except sa_exc.SQLAlchemyError as e:
        Session.rollback()
        raise FailedCommand(str(e.args[0]))
