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


@dataclass
class _CompanyDefaultsBase:
    name: Optional[str] = None
    address: Optional[Address] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    rcs: Optional[str] = None
    no_vat: bool = False


@dataclass
class CompanyCreate(_CompanyBase):
    address: Optional[Address] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    rcs: Optional[str] = None
    no_vat: Optional[bool] = None

    def flatten(self) -> dict[str, Any]:
        address: Optional[str]
        zip_code: Optional[str]
        city: Optional[str]
        if self.address is None:
            address = zip_code = city = None
        else:
            address = self.address.address
            zip_code = self.address.zip_code
            city = self.address.city
        return dict(
            name=self.name,
            home=self.home,
            address=address,
            zip_code=zip_code,
            city=city,
            phone_number=self.phone_number,
            email=self.email,
            siret=self.siret,
            rcs=self.rcs,
            no_vat=self.no_vat,
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
            no_vat=self.no_vat,
        )


@dataclass
class _CompanyInDBBase(_CompanyBase):
    address: Address
    phone_number: str
    email: str
    siret: str
    rcs: str
    no_vat: bool


# Additional properties to return from DB
@dataclass
class Company(_CompanyInDBBase):
    @classmethod
    def from_orm(cls, orm_obj: models.Company) -> "Company":
        address = Address(
            address=orm_obj.address, zip_code=orm_obj.zip_code, city=orm_obj.city
        )
        return cls(
            name=orm_obj.name,
            home=orm_obj.home,
            address=address,
            phone_number=orm_obj.phone_number,
            email=orm_obj.email,
            siret=orm_obj.siret,
            rcs=orm_obj.rcs,
            no_vat=orm_obj.no_vat,
        )


# Additional properties stored in DB
@dataclass
class CompanyInDB(_CompanyInDBBase):
    pass
