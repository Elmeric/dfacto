# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass

from dfacto.models import crud, schemas

from .base import DFactoModel


@dataclass()
class ServiceModel(DFactoModel[crud.CRUDService, schemas.Service]):
    crud_object: crud.CRUDService = crud.service
    schema: schemas.Service = schemas.Service
