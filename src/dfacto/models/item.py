# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Optional

import sqlalchemy as sa
import sqlalchemy.exc
import sqlalchemy.orm

from dfacto.models.command import CommandResponse, CommandStatus
from dfacto.models.models import _Item
from dfacto.models.schemas import Service
from dfacto.models.service import ServiceModel


@dataclass()
class Item:
    id: int
    raw_amount: float
    vat: float
    net_amount: float
    service: Service
    quantity: int = 1


@dataclass()
class ItemModel:
    Session: sa.orm.scoped_session
    service_model: ServiceModel

    def get(self, item_id: int) -> Optional[Item]:
        item: Optional[_Item] = self.Session.get(_Item, item_id)
        if item is None:
            return
        return Item(
            item.id,
            item.raw_amount,
            item.vat,
            item.net_amount,
            self.service_model.get(item.service.id),
            item.quantity,
        )

    def list_all(self) -> list[Item]:
        return [
            Item(
                item.id,
                item.raw_amount,
                item.vat,
                item.net_amount,
                self.service_model.get(item.service.id),
                item.quantity,
            )
            for item in self.Session.scalars(sa.select(_Item)).all()
        ]

    def delete(self, item_id: int) -> CommandResponse:
        self.Session.execute(sa.delete(_Item).where(_Item.id == item_id))
        try:
            self.Session.commit()
        except sa.exc.SQLAlchemyError:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ITEM_DELETE - Item with id {item_id} is used"
                f" by at least one client's basket or invoice!",
            )
        else:
            return CommandResponse(CommandStatus.COMPLETED)
