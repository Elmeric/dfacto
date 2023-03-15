# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from typing import Any, Optional

from dfacto import settings as Config
from dfacto.backend.crud import CrudError
from dfacto.backend import models, schemas


class CRUDCompany:
    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        return Config.dfacto_settings.profiles or {}

    def get(self, name: str) -> Optional[models.Company]:
        try:
            company_ = self.profiles[name]
        except KeyError:
            return None
        company_["home"] = Path(company_["home"])
        return models.Company(**company_)

    def get_all(self) -> list[models.Company]:
        companies = []
        for company_ in self.profiles.values():
            company_["home"] = Path(company_["home"])
            companies.append(models.Company(**company_))
        return companies

    def create(self, *, obj_in: schemas.CompanyCreate) -> models.Company:
        name = obj_in.name
        profiles = self.profiles
        if name in profiles:
            raise CrudError(f"{name} already exists.")

        home = obj_in.home
        try:
            home.mkdir(parents=False, exist_ok=True)
        except FileNotFoundError:
            raise CrudError(f"{home} parent folder not found")

        obj_in_data = obj_in.flatten()
        db_obj = models.Company(**obj_in_data)
        profiles[name] = obj_in_data
        Config.dfacto_settings.profiles = profiles
        Config.dfacto_settings.save()

        return db_obj


company = CRUDCompany()
