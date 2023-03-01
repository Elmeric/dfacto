# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Any, Optional

from dfacto.models import models

from .base import BaseSchema


@dataclass()
class Address:
    address: str
    zip_code: str
    city: str


@dataclass
class _ClientBase(BaseSchema):
    name: str
    address: Address
    is_active: bool


@dataclass
class _ClientDefaultsBase(BaseSchema):
    name: Optional[str] = None
    address: Optional[Address] = None
    is_active: Optional[int] = None


@dataclass
class ClientCreate(_ClientBase):
    is_active: bool = True

    def flatten(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            address=self.address.address,
            zip_code=self.address.zip_code,
            city=self.address.city,
            is_active=self.is_active,
        )


@dataclass
class ClientUpdate(_ClientDefaultsBase):
    def flatten(self) -> dict[str, Any]:
        if self.address is None:
            address = zip_code = city = None
        else:
            address = self.address.address
            zip_code = self.address.zip_code
            city = self.address.city
        return dict(
            name=self.name,
            address=address,
            zip_code=zip_code,
            city=city,
            is_active=self.is_active,
        )


@dataclass
class _ClientInDBBase(_ClientBase):
    id: int


# Additional properties to return from DB
@dataclass
class Client(_ClientInDBBase):
    @property
    def code(self) -> str:
        return "CL" + str(self.id).zfill(5)
        # print(f"Code of client {self.name} is {self.code}")

    @classmethod
    def from_orm(cls, orm_obj: models.Client) -> "Client":
        address = Address(
            address=orm_obj.address, zip_code=orm_obj.zip_code, city=orm_obj.city
        )
        return cls(
            id=orm_obj.id,
            name=orm_obj.name,
            address=address,
            is_active=orm_obj.is_active,
        )


# Additional properties stored in DB
@dataclass
class ClientInDB(_ClientInDBBase):
    pass
