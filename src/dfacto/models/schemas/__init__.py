# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass

from .base import BaseSchema
from .basket import Basket, BasketCreate, BasketInDB, BasketUpdate
from .client import Client, ClientCreate, ClientInDB, ClientUpdate, Address
from .item import Item, ItemCreate, ItemInDB, ItemUpdate
from .service import Service, ServiceCreate, ServiceInDB, ServiceUpdate
from .vat_rate import VatRate, VatRateCreate, VatRateInDB, VatRateUpdate
