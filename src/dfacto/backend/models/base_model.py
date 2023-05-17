# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import decimal
from typing import Annotated, TypeVar

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, mapped_column
from sqlalchemy.types import TypeDecorator, Integer


class SqliteDecimal(TypeDecorator):
    # https://stackoverflow.com/questions/10355767/how-should-i-handle-decimal-in-sqlalchemy-sqlite
    # This TypeDecorator use Sqlalchemy Integer as impl. It converts Decimals
    # from Python to Integers which is later stored in Sqlite database.
    impl = Integer

    def __init__(self, scale):
        # It takes a 'scale' parameter, which specifies the number of digits
        # to the right of the decimal point of the number in the column.
        TypeDecorator.__init__(self)
        self.scale = scale
        self.multiplier_int = 10 ** self.scale

    def process_bind_param(self, value, dialect):
        # e.g. value = Column(SqliteDecimal(2)) means a value such as
        # Decimal('12.34') will be converted to 1234 in Sqlite
        if value is not None:
            value = int(decimal.Decimal(value) * self.multiplier_int)
        return value

    def process_result_value(self, value, dialect):
        # e.g. Integer 1234 in Sqlite will be converted to Decimal('12.34'),
        # when query takes place.
        if value is not None:
            value = decimal.Decimal(value) / self.multiplier_int
        return value


class BaseModel(MappedAsDataclass, DeclarativeBase):
    type_annotation_map = {
        decimal.Decimal: SqliteDecimal(scale=2)
    }


ModelType = TypeVar("ModelType", bound=BaseModel)


intpk = Annotated[int, mapped_column(primary_key=True)]
