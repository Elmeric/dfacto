# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import sqlalchemy as sa
from sqlalchemy.orm import scoped_session

from dfacto.models.models import VatRate
from dfacto.models.schemas.vat_rate import VatRateCreate, VatRateUpdate

from .base import CRUDBase


class CRUDVatRate(CRUDBase[VatRate, VatRateCreate, VatRateUpdate]):
    def init_defaults(self, db: scoped_session, preset_rates) -> None:
        if db.scalars(sa.select(self.model)).first() is None:
            # No VAT rates in the database: create them.
            db.execute(sa.insert(self.model), preset_rates)
            db.commit()


vat_rate = CRUDVatRate(VatRate)
