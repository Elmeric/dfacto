# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from dfacto import settings as Config
from dfacto.backend import db, models, schemas
from dfacto.backend.crud import CrudError
from dfacto.util.settings import SettingsError


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

    def get_current(self) -> Optional[models.Company]:
        return self.get(Config.dfacto_settings.last_profile)

    def get_all(self) -> list[models.Company]:
        companies = []
        for company_ in self.profiles.values():
            company_["home"] = Path(company_["home"])
            companies.append(models.Company(**company_))
        return companies

    def select(self, name: str, *, is_new: bool) -> None:
        profiles = self.profiles

        if name not in profiles:
            raise CrudError(f"{name} does not exist")
        Config.dfacto_settings.last_profile = name

        try:
            Config.dfacto_settings.save()
        except SettingsError as exc:
            raise CrudError(f"Cannot persist company profiles: {exc}") from exc

        db_path = profiles[name]["home"] / "dfacto.db"
        db.configure_session(db_path, is_new=is_new)

    def create(self, *, obj_in: schemas.CompanyCreate) -> models.Company:
        name = obj_in.name
        profiles = self.profiles
        if name in profiles:
            raise CrudError(f"{name} already exists")

        home = obj_in.home
        try:
            home.mkdir(parents=False, exist_ok=True)
        except FileNotFoundError as exc:
            raise CrudError(f"{home} parent folder not found") from exc

        obj_in_data = obj_in.flatten()
        db_obj = models.Company(**obj_in_data)
        profiles[name] = obj_in_data
        Config.dfacto_settings.profiles = profiles
        try:
            Config.dfacto_settings.save()
        except SettingsError as exc:
            raise CrudError(f"Cannot persist company profiles: {exc}") from exc

        return db_obj

    def update(
        self, *, db_obj: models.Company, obj_in: schemas.CompanyUpdate
    ) -> models.Company:
        updated = False
        renamed = obj_in.name is not None and db_obj.name != obj_in.name
        old_name = db_obj.name
        update_data = obj_in.flatten()

        for field in update_data:
            if (
                update_data[field] is not None
                and getattr(db_obj, field) != update_data[field]
            ):
                setattr(db_obj, field, update_data[field])
                updated = True

        if updated:
            profiles = self.profiles
            profiles[db_obj.name] = asdict(db_obj)
            if renamed:
                del profiles[old_name]
                Config.dfacto_settings.last_profile = db_obj.name
            Config.dfacto_settings.profiles = profiles
            try:
                Config.dfacto_settings.save()
            except SettingsError as exc:
                raise CrudError(f"Cannot persist company profiles: {exc}") from exc

        return db_obj


company = CRUDCompany()
