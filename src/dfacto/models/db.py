# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from sqlite3 import Connection as SQLite3Connection
from typing import Annotated

from sqlalchemy import create_engine
from sqlalchemy.event import listen
from sqlalchemy.orm import (
    DeclarativeBase,
    MappedAsDataclass,
    mapped_column,
    scoped_session,
    sessionmaker,
)


class BaseModel(MappedAsDataclass, DeclarativeBase):
    pass


intpk = Annotated[int, mapped_column(primary_key=True)]


def _set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        print("Execute: PRAGMA foreign_keys=ON")
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # dbapi_connection.execute('PRAGMA foreign_keys = ON')


print(f"**************** CREATING ENGINE ****************")
# engine = create_engine("sqlite+pysqlite:///:memory:", echo=True)
# try:
#     os.remove('dcfs_data/dcfs.db')
# except OSError:
#     pass
engine = create_engine("sqlite+pysqlite:///dfacto.db")
# engine = create_engine('sqlite+pysqlite:///dfacto.db', echo=True)
listen(engine, "connect", _set_sqlite_pragma)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
print(f"Importing db.py: {engine} {id(engine)}", Session)
