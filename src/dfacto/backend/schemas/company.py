# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dfacto.backend import models

from dfacto.backend.schemas import Address


@dataclass
class _CompanyBase:
    name: str
    home: Path
    address: Address
    phone_number: str
    email: str
    siret: str
    rcs: str


@dataclass
class _CompanyDefaultsBase:
    name: Optional[str] = None
    address: Optional[Address] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    rcs: Optional[str] = None


@dataclass
class CompanyCreate(_CompanyBase):
    address: Optional[Address] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    rcs: Optional[str] = None

    def flatten(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            home=self.home,
            address=self.address.address,
            zip_code=self.address.zip_code,
            city=self.address.city,
            phone_number=self.phone_number,
            email=self.email,
            siret=self.siret,
            rcs=self.rcs,
        )


@dataclass
class CompanyUpdate(_CompanyDefaultsBase):
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
            phone_number=self.phone_number,
            email=self.email,
            siret=self.siret,
            rcs=self.rcs,
        )


@dataclass
class _CompanyInDBBase(_CompanyBase):
    pass
    # id: int


# Additional properties to return from DB
@dataclass
class Company(_CompanyInDBBase):
    @classmethod
    def from_orm(cls, orm_obj: models.Company) -> "Company":
        address = Address(
            address=orm_obj.address, zip_code=orm_obj.zip_code, city=orm_obj.city
        )
        return cls(
            # id=orm_obj.id,
            name=orm_obj.name,
            home=orm_obj.home,
            address=address,
            phone_number=orm_obj.phone_number,
            email=orm_obj.email,
            siret=orm_obj.siret,
            rcs=orm_obj.rcs,
        )


# Additional properties stored in DB
@dataclass
class CompanyInDB(_CompanyInDBBase):
    pass
