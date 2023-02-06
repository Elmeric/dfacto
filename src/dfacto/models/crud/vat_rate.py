# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import scoped_session

from dfacto.models import models
from dfacto.models import schemas

from .base import CRUDBase

if TYPE_CHECKING:   # pragma: no cover
    from dfacto.models.vat_rate import PresetRate


class CRUDVatRate(CRUDBase[models.VatRate, schemas.VatRateCreate, schemas.VatRateUpdate]):
    def init_defaults(self, db: scoped_session, preset_rates: "PresetRate") -> None:
        if db.scalars(sa.select(self.model)).first() is None:
            # No VAT rates in the database: create them.
            db.execute(sa.insert(self.model), preset_rates)
            db.commit()


vat_rate = CRUDVatRate(models.VatRate)
