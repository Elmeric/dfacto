# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import datetime

from sqlalchemy.orm import scoped_session
from sqlalchemy.exc import SQLAlchemyError

from dfacto.models import models
from dfacto.models import schemas

from .base import CRUDBase, CrudError


class CRUDInvoice(
    CRUDBase[models.Invoice, schemas.InvoiceCreate, schemas.InvoiceUpdate]
):
    def create(
        self, dbsession: scoped_session, *, obj_in: schemas.InvoiceCreate
    ) -> models.Invoice:
        obj_in_data = obj_in.flatten()
        db_obj = self.model(**obj_in_data)
        dbsession.add(db_obj)
        dbsession.flush([db_obj])
        now = datetime.now()
        # dbsession.execute(
        #     update(models.StatusLog)
        #         .where(models.StatusLog.to == None)
        #         .values(to=now)
        # )
        log = models.StatusLog(
            invoice_id=db_obj.id,
            from_=now,
            to=None,
            status=models.InvoiceStatus.DRAFT
        )
        dbsession.add(log)
        try:
            dbsession.commit()
        except SQLAlchemyError as exc:
            dbsession.rollback()
            raise CrudError() from exc
        else:
            dbsession.refresh(db_obj)
            return db_obj


invoice = CRUDInvoice(models.Invoice)
