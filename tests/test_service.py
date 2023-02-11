# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import cast
import dataclasses

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models.api.command import CommandStatus
from dfacto.models import db, crud, models, schemas
from dfacto.models.api.api_v1.service import ServiceModel
from .conftest import FakeORMModel, FakeSchema, FakeCRUDBase


@dataclasses.dataclass
class FakeORMService(FakeORMModel):
    unit_price: float
    name: str = "Service"
    vat_rate_id: int = 1


class FakeCRUDService(FakeCRUDBase, crud.CRUDService):
    pass


class FakeService(FakeSchema, schemas.Service):
    pass


@pytest.fixture
def init_services(dbsession: sa.orm.scoped_session) -> list[models.Service]:
    db.init_db_data(dbsession)

    for i in range(5):
        service = models.Service(
            name=f"Service_{i + 1}",
            unit_price=100 + 10*i,
            vat_rate_id=(i % 3) + 1
        )
        dbsession.add(service)
        dbsession.commit()

    services = cast(
        list[models.Service],
        dbsession.scalars(sa.select(models.Service)).all()
    )
    return services


@pytest.fixture
def service_model(dbsession):
    return ServiceModel(dbsession)


def test_crud_init():
    assert crud.service.model is models.Service


def test_crud_get(dbsession, init_services):
    services = init_services

    service = crud.service.get(dbsession, id_=services[0].id)

    assert service is services[0]


def test_crud_get_unknown(dbsession, init_services):
    services = init_services
    ids = [s.id for s in services]

    service = crud.service.get(dbsession, id_=10)

    assert 10 not in ids
    assert service is None


def test_crud_get_error(dbsession, init_services, mock_get):
    state, _called = mock_get
    state["failed"] = True

    services = init_services

    with pytest.raises(crud.CrudError):
        _service = crud.service.get(dbsession, id_=services[0].id)


@pytest.mark.parametrize(
    "kwargs, offset, length",
    (
        ({}, 0, 5),
        ({"limit": 2}, 0, 2),
        ({"skip": 2}, 2, 3),
        ({"skip": 2, "limit": 2}, 2, 2)
    )
)
def test_crud_get_multi(kwargs, offset, length, dbsession, init_services):
    services = init_services

    obj_list = crud.service.get_multi(dbsession, **kwargs)

    assert len(obj_list) == length
    for i, obj in enumerate(obj_list):
        assert obj is services[i + offset]


def test_crud_get_multi_error(dbsession, init_services, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _services = crud.service.get_multi(dbsession)


def test_crud_create(dbsession, init_services):
    service = crud.service.create(
        dbsession,
        obj_in=schemas.ServiceCreate(
            name="Wonderful service",
            unit_price=1000.0,
            vat_rate_id=2
        )
    )

    assert service.id is not None
    assert service.name == "Wonderful service"
    assert service.unit_price == 1000.0
    assert service.vat_rate_id == 2
    assert service.vat_rate.id == 2
    assert service.vat_rate.rate == 2.1
    try:
        s = dbsession.get(models.Service, service.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name == "Wonderful service"
    assert s.unit_price == 1000.0
    assert s.vat_rate_id == 2
    assert s.vat_rate.id == 2
    assert s.vat_rate.rate == 2.1


def test_crud_create_duplicate(dbsession, init_services):
    with pytest.raises(crud.CrudError):
        _service = crud.service.create(
            dbsession,
            obj_in=schemas.ServiceCreate(
                name="Service_1",
                unit_price=10.0,
                vat_rate_id=2
            )
        )
    assert len(
        dbsession.scalars(
            sa.select(models.Service).where(models.Service.name == "Service_1")
        ).all()
    ) == 1


def test_crud_create_error(dbsession, init_services, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _service = crud.service.create(
            dbsession,
            obj_in=schemas.ServiceCreate(
                name="Wonderful service",
                unit_price=1000.0,
                vat_rate_id=2
            )
        )
    assert (
        dbsession.scalars(
            sa.select(models.Service).where(models.Service.name == "Wonderful service")
        ).first()
        is None
    )


@pytest.mark.parametrize("obj_in_factory", (schemas.ServiceUpdate, dict))
def test_crud_update(obj_in_factory, dbsession, init_services):
    service = init_services[0]

    updated = crud.service.update(
        dbsession,
        db_obj=service,
        obj_in=obj_in_factory(
            name="Wonderful service",
            unit_price=1000.0,
            vat_rate_id=2
        )
    )

    assert updated.id == service.id
    assert updated.name == "Wonderful service"
    assert updated.unit_price == 1000.0
    assert updated.vat_rate_id == 2
    assert updated.vat_rate.id == 2
    assert updated.vat_rate.rate == 2.1
    try:
        s = dbsession.get(models.Service, updated.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name == "Wonderful service"
    assert s.unit_price == 1000.0
    assert s.vat_rate_id == 2
    assert s.vat_rate.id == 2
    assert s.vat_rate.rate == 2.1


def test_crud_update_partial(dbsession, init_services):
    service = init_services[0]

    updated = crud.service.update(
        dbsession,
        db_obj=service,
        obj_in=schemas.ServiceUpdate(unit_price=1000.0)
    )

    assert updated.id == service.id
    assert updated.name == service.name
    assert updated.unit_price == 1000.0
    assert updated.vat_rate_id == service.vat_rate_id
    assert updated.vat_rate is service.vat_rate
    try:
        s = dbsession.get(models.Service, updated.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name == service.name
    assert s.unit_price == 1000.0
    assert s.vat_rate_id == s.vat_rate_id
    assert s.vat_rate is service.vat_rate


def test_crud_update_idem(dbsession, init_services, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    service = init_services[0]

    updated = crud.service.update(
        dbsession,
        db_obj=service,
        obj_in=schemas.ServiceUpdate(unit_price=service.unit_price)
    )

    assert updated is service
    assert len(called) == 0


def test_crud_update_error(dbsession, init_services, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    service = init_services[0]

    with pytest.raises(crud.CrudError):
        _updated = crud.service.update(
            dbsession,
            db_obj=service,
            obj_in=schemas.ServiceUpdate(name="Wonderful service")
        )

    assert (
        dbsession.scalars(
            sa.select(models.Service).where(models.Service.name == "Wonderful service")
        ).first()
        is None
    )


def test_crud_delete(dbsession, init_services):
    service = init_services[0]
    assert dbsession.get(models.Service, service.id) is not None
    assert service in dbsession.get(models.VatRate, service.vat_rate_id).services

    crud.service.delete(dbsession, db_obj=service)

    assert dbsession.get(models.Service, service.id) is None
    for s in dbsession.get(models.VatRate, service.vat_rate_id).services:
        assert s.id != service.id


def test_crud_delete_error(dbsession, init_services, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    service = init_services[0]
    assert dbsession.get(models.Service, service.id) is not None

    with pytest.raises(crud.CrudError):
        crud.service.delete(dbsession, db_obj=service)

    assert dbsession.get(models.Service, service.id) is not None


def test_schema_from_orm(dbsession, init_services):
    service = init_services[0]

    from_db = schemas.Service.from_orm(service)

    assert from_db.id == service.id
    assert from_db.name == service.name
    assert from_db.unit_price == service.unit_price
    assert from_db.vat_rate.id == service.vat_rate.id
    assert from_db.vat_rate.rate == service.vat_rate.rate


def test_cmd_get(dbsession):
    crud_object = FakeCRUDService(
            raises={"READ": False},
            read_value=FakeORMService(id=1, name="Service 1", unit_price=100.0)
        )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeService
    )

    response = service_model.get(obj_id=1)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Service 1"
    assert response.body.unit_price == 100.0


def test_cmd_get_unknown(dbsession):
    crud_object = FakeCRUDService(raises={"READ": False}, read_value=None)
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeService
    )

    response = service_model.get(obj_id=1)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "GET - Object 1 not found."


def test_cmd_get_error(dbsession):
    crud_object = FakeCRUDService(raises={"READ": True})
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.get(obj_id=1)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET - SQL or database error")


def test_cmd_get_multi(dbsession):
    crud_object = FakeCRUDService(
            raises={"READ": False},
            read_value=[
                FakeORMService(id=1, name="Service 1", unit_price=100.0),
                FakeORMService(id=2, name="Service 2", unit_price=200.0),
                FakeORMService(id=3, name="Service 3", unit_price=300.0),
                FakeORMService(id=4, name="Service 4", unit_price=400.0),
            ]
        )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeService
    )

    response = service_model.get_multi(skip=1, limit=2)

    assert len(crud_object.methods_called) == 1
    assert "GET_MULTI" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Service 2"
    assert response.body[0].unit_price == 200.0
    assert response.body[1].id == 3
    assert response.body[1].name == "Service 3"
    assert response.body[1].unit_price == 300.0


def test_cmd_get_multi_error(dbsession):
    crud_object = FakeCRUDService(raises={"READ": True})
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.get_multi(skip=1, limit=2)

    assert len(crud_object.methods_called) == 1
    assert "GET_MULTI" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-MULTI - SQL or database error")


def test_cmd_get_all(dbsession):
    crud_object = FakeCRUDService(
            raises={"READ": False},
            read_value=[
                FakeORMService(id=2, name="Service 2", unit_price=200.0),
                FakeORMService(id=3, name="Service 3", unit_price=300.0),
            ]
        )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeService
    )

    response = service_model.get_all()

    assert len(crud_object.methods_called) == 1
    assert "GET_ALL" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Service 2"
    assert response.body[0].unit_price == 200.0
    assert response.body[1].id == 3
    assert response.body[1].name == "Service 3"
    assert response.body[1].unit_price == 300.0


def test_cmd_get_all_error(dbsession):
    crud_object = FakeCRUDService(raises={"READ": True})
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.get_all()

    assert len(crud_object.methods_called) == 1
    assert "GET_ALL" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-ALL - SQL or database error")


def test_cmd_add(dbsession):
    crud_object = FakeCRUDService(raises={"CREATE": False})
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeService
    )

    response = service_model.add(
        schemas.ServiceCreate(name="Service 2", unit_price=200.0, vat_rate_id=3)
    )

    assert len(crud_object.methods_called) == 1
    assert "CREATE" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Service 2"
    assert response.body.unit_price == 200.0
    assert response.body.vat_rate_id == 3


def test_cmd_add_error(dbsession):
    crud_object = FakeCRUDService(raises={"CREATE": True})
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.add(
        schemas.ServiceCreate(name="Service 2", unit_price=200.0, vat_rate_id=3)
    )

    assert len(crud_object.methods_called) == 1
    assert "CREATE" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD - Cannot add object")


def test_cmd_update(dbsession):
    crud_object = FakeCRUDService(
            raises={"READ": False, "UPDATE": False},
            read_value=FakeORMService(id=1, name="Service 1", unit_price=100.0, vat_rate_id=1)
        )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeService
    )

    response = service_model.update(
        obj_id=1,
        obj_in=schemas.ServiceUpdate(name="Service 2", unit_price=200.0, vat_rate_id=3)
    )

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "UPDATE" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Service 2"
    assert response.body.unit_price == 200.0
    assert response.body.vat_rate_id == 3


def test_cmd_update_unknown(dbsession):
    crud_object = FakeCRUDService(raises={"READ": False, "UPDATE": False}, read_value=None)
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.update(
        obj_id=1,
        obj_in=schemas.ServiceUpdate(name="Service 2", unit_price=200.0, vat_rate_id=3)
    )

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Object 1 not found.")


def test_cmd_update_error(dbsession):
    crud_object = FakeCRUDService(
            raises={"READ": False, "UPDATE": True},
            read_value=FakeORMService(id=1, name="Service 1", unit_price=100.0, vat_rate_id=1)
        )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.update(
        obj_id=1,
        obj_in=schemas.ServiceUpdate(name="Service 2", unit_price=200.0, vat_rate_id=3)
    )

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "UPDATE" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Cannot update object 1")


def test_cmd_delete(dbsession):
    crud_object = FakeCRUDService(
            raises={"READ": False, "DELETE": False},
            read_value=FakeORMService(id=1, name="Service 1", unit_price=100.0, vat_rate_id=1)
        )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeService
    )

    response = service_model.delete(obj_id=1)

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "DELETE" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is None


def test_cmd_delete_unknown(dbsession):
    crud_object = FakeCRUDService(
        raises={"READ": False, "DELETE": False},
        read_value=None
    )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.delete(obj_id=1)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Object 1 not found.")


@pytest.mark.parametrize("error", (crud.CrudError, crud.CrudIntegrityError))
def test_cmd_delete_error(error, dbsession):
    crud_object = FakeCRUDService(
            raises={"READ": False, "DELETE": error},
            read_value=FakeORMService(id=1, name="Service 1", unit_price=100.0, vat_rate_id=1)
        )
    service_model = ServiceModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeService
    )

    response = service_model.delete(obj_id=1)

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "DELETE" in crud_object.methods_called
    if error is crud.CrudError:
        assert response.status is CommandStatus.FAILED
        assert response.reason.startswith("DELETE - Cannot delete object 1")
    else:
        assert response.status is CommandStatus.REJECTED
        assert response.reason.startswith(
            "DELETE - Object 1 is used by at least one other object."
        )
