# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Type

from dfacto.models import crud, db, schemas

from .base import DFactoModel


@dataclass()
class ServiceModel(DFactoModel[crud.CRUDService, schemas.Service]):
    crud_object: crud.CRUDService = crud.service
    schema: Type[schemas.Service] = schemas.Service


service = ServiceModel(db.Session)
