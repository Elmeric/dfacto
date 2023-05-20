# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Annotated, TypeVar

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, mapped_column

from .base_model import BaseModel, ModelType
from .basket import Basket
from .client import Client
from .company import Company
from .invoice import Invoice, InvoiceStatus, StatusLog
from .item import Item
from .service import Service, ServiceRevision
from .vat_rate import VatRate

__all__ = [
    "ModelType",
    "BaseModel",
    "VatRate",
    "Service",
    "ServiceRevision",
    "Client",
    "Basket",
    "Item",
    "Invoice",
    "StatusLog",
    "InvoiceStatus",
    "Company",
]
