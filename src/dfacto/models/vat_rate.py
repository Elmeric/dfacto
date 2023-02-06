# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import ClassVar, Type, TypedDict

from dfacto.models import crud, schemas
from dfacto.models.command import CommandResponse, CommandStatus

from .base import DFactoModel


class PresetRate(TypedDict):
    id: int
    rate: float


@dataclass()
class VatRateModel(DFactoModel[crud.CRUDVatRate, schemas.VatRate]):
    crud_object: crud.CRUDVatRate = crud.vat_rate
    schema: Type[schemas.VatRate] = schemas.VatRate

    DEFAULT_RATE_ID: ClassVar[int] = 1
    PRESET_RATES: ClassVar[list[PresetRate]] = [
        {"id": DEFAULT_RATE_ID, "rate": 0.0},
        {"id": DEFAULT_RATE_ID + 1, "rate": 5.5},
        {"id": DEFAULT_RATE_ID + 2, "rate": 20.0},
    ]
    PRESET_RATE_IDS: ClassVar[tuple[int, ...]] = tuple(
        [rate["id"] for rate in PRESET_RATES]
    )

    def __post_init__(self) -> None:
        self.crud_object.init_defaults(self.Session, VatRateModel.PRESET_RATES)

    def reset(self) -> CommandResponse:
        for vat_rate in VatRateModel.PRESET_RATES:
            self.update(vat_rate["id"], schemas.VatRateUpdate(vat_rate["rate"]))

        vat_rates = self.get_all().body
        success = True
        if vat_rates is not None:
            for vat_rate in vat_rates:
                if vat_rate.id not in VatRateModel.PRESET_RATE_IDS:
                    response = self.delete(vat_rate.id)
                    success = success and response.status is CommandStatus.COMPLETED
        if success:
            return CommandResponse(CommandStatus.COMPLETED)
        else:
            return CommandResponse(
                CommandStatus.FAILED,
                "VAT_RATE-RESET - Reset failed: some VAT rates may be in use.",
            )

    def get_default(self) -> CommandResponse:
        return self.get(VatRateModel.DEFAULT_RATE_ID)

    def delete(self, vat_rate_id: int) -> CommandResponse:
        if vat_rate_id in VatRateModel.PRESET_RATE_IDS:
            return CommandResponse(
                CommandStatus.REJECTED,
                "DELETE - Default VAT rates cannot be deleted.",
            )

        vat_rate = self.crud_object.get(self.Session, vat_rate_id)
        if vat_rate is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Object {vat_rate_id} not found.",
            )

        in_use = vat_rate.services
        if len(in_use) > 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"DELETE - VAT rate with id {vat_rate_id} is used"
                f" by at least '{in_use[0].name}' service.",
            )

        return super().delete(vat_rate_id)
