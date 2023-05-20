# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from dfacto.backend import models

from .base import BaseSchema
from .vat_rate import VatRate


@dataclass
class _ServiceBase(BaseSchema[models.Service]):
    name: str
    unit_price: Decimal


@dataclass
class _ServiceDefaultsBase(BaseSchema[models.Service]):
    name: Optional[str] = None
    unit_price: Optional[Decimal] = None
    vat_rate_id: Optional[int] = None


@dataclass
class ServiceCreate(_ServiceBase):
    vat_rate_id: int


@dataclass
class ServiceUpdate(_ServiceDefaultsBase):
    pass


@dataclass
class _ServiceInDBBase(_ServiceBase):
    id: int


# Additional properties to return from DB
@dataclass
class Service(_ServiceInDBBase):
    vat_rate: VatRate

    @classmethod
    def from_orm(cls, orm_obj: models.Service) -> "Service":
        rev_id = orm_obj.rev_id
        revision = orm_obj.revisions[rev_id]
        # revision = None
        # for rev in orm_obj.revisions:
        #     rev: models.ServiceRevision
        #     if rev.id == rev_id:
        #         revision = rev
        #         break
        # assert revision is not None
        return cls(
            id=orm_obj.id,
            name=revision.name,
            unit_price=revision.unit_price.quantize(Decimal('0.01')),
            vat_rate=VatRate.from_orm(revision.vat_rate),
        )

    @classmethod
    def from_revision(cls, orm_obj: models.Service, rev_id: int) -> "Service":
        revision = orm_obj.revisions[rev_id]
        return cls(
            id=orm_obj.id,
            name=revision.name,
            unit_price=revision.unit_price.quantize(Decimal('0.01')),
            vat_rate=VatRate.from_orm(revision.vat_rate),
        )


# Additional properties stored in DB
@dataclass
class ServiceInDB(_ServiceInDBBase):
    vat_rate_id: int
