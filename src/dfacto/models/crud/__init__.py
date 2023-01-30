# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from .base import CRUDBase, CrudError, CrudIntegrityError
from dfacto.models.models import _VatRate
from dfacto.models.schemas.vat_rate import VatRateCreate, VatRateUpdate


vat_rate = CRUDBase[_VatRate, VatRateCreate, VatRateUpdate](_VatRate)
