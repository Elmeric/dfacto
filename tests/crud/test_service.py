# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from decimal import Decimal
from typing import cast

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import crud, models, schemas
from dfacto.backend.db.session import init_db_data

pytestmark = pytest.mark.crud


@pytest.fixture
def init_services(dbsession: Session) -> list[models.Service]:
    init_db_data(dbsession)

    for i in range(5):
        service = models.Service()
        dbsession.add(service)
        dbsession.flush([service])
        service_revision = models.ServiceRevision(
            name=f"Service_{i + 1}",
            unit_price=Decimal(100 + 10 * i),
            vat_rate_id=(i % 3) + 1,
            service_id=service.id
        )
        dbsession.add(service_revision)
        dbsession.flush([service_revision])
        service.rev_id = service_revision.id
        dbsession.commit()

    services = cast(
        list[models.Service], dbsession.scalars(sa.select(models.Service)).all()
    )
    return services


def test_crud_init():
    assert crud.service.model is models.Service


def test_crud_get(dbsession, init_services):
    services = init_services

    service = crud.service.get(dbsession, services[0].id)

    assert service is services[0]


def test_crud_get_unknown(dbsession, init_services):
    services = init_services
    ids = [s.id for s in services]

    service = crud.service.get(dbsession, 10)

    assert 10 not in ids
    assert service is None


def test_crud_get_error(dbsession, init_services, mock_get):
    state, _called = mock_get
    state["failed"] = True

    services = init_services

    with pytest.raises(crud.CrudError):
        _service = crud.service.get(dbsession, services[0].id)


@pytest.mark.parametrize(
    "kwargs, offset, length",
    (
        ({}, 0, 5),
        ({"limit": 2}, 0, 2),
        ({"skip": 2}, 2, 3),
        ({"skip": 2, "limit": 2}, 2, 2),
    ),
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
            name="Wonderful service", unit_price=Decimal('1000.00'), vat_rate_id=2
        ),
    )

    assert service.id is not None
    assert service.rev_id is not None
    assert service.revisions[service.rev_id].name == "Wonderful service"
    assert service.revisions[service.rev_id].unit_price == Decimal('1000.00')
    assert service.revisions[service.rev_id].vat_rate_id == 2
    assert service.revisions[service.rev_id].vat_rate.id == 2
    assert service.revisions[service.rev_id].vat_rate.rate == Decimal('2.1')
    try:
        s = dbsession.get(models.Service, service.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.revisions[s.rev_id].name == "Wonderful service"
    assert s.revisions[s.rev_id].unit_price == Decimal('1000.00')
    assert s.revisions[s.rev_id].vat_rate_id == 2
    assert s.revisions[s.rev_id].vat_rate.id == 2
    assert s.revisions[s.rev_id].vat_rate.rate == Decimal('2.1')


def test_crud_create_error(dbsession, init_services, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _service = crud.service.create(
            dbsession,
            obj_in=schemas.ServiceCreate(
                name="Wonderful service", unit_price=Decimal('1000.00'), vat_rate_id=2
            ),
        )
    assert (
        dbsession.scalars(
            sa.select(models.ServiceRevision)
            .where(models.ServiceRevision.name == "Wonderful service")
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
            name="Wonderful service", unit_price=Decimal('1000.00'), vat_rate_id=2
        ),
    )

    assert updated.id == service.id
    assert updated.revisions[updated.rev_id].name == "Wonderful service"
    assert updated.revisions[updated.rev_id].unit_price == Decimal('1000.00')
    assert updated.revisions[updated.rev_id].vat_rate_id == 2
    assert updated.revisions[updated.rev_id].vat_rate.id == 2
    assert updated.revisions[updated.rev_id].vat_rate.rate == Decimal('2.1')
    try:
        s = dbsession.get(models.Service, updated.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.revisions[s.rev_id].name == "Wonderful service"
    assert s.revisions[s.rev_id].unit_price == Decimal('1000.00')
    assert s.revisions[s.rev_id].vat_rate_id == 2
    assert s.revisions[s.rev_id].vat_rate.id == 2
    assert s.revisions[s.rev_id].vat_rate.rate == Decimal('2.1')


def test_crud_update_partial(dbsession, init_services):
    service = init_services[0]

    updated = crud.service.update(
        dbsession,
        db_obj=service, obj_in=schemas.ServiceUpdate(unit_price=Decimal('1000.00'))
    )

    assert updated.id == service.id
    assert updated.revisions[updated.rev_id].name == service.revisions[service.rev_id].name
    assert updated.revisions[updated.rev_id].unit_price == Decimal('1000.00')
    assert updated.revisions[updated.rev_id].vat_rate_id == service.revisions[service.rev_id].vat_rate_id
    assert updated.revisions[updated.rev_id].vat_rate is service.revisions[service.rev_id].vat_rate
    try:
        s = dbsession.get(models.Service, updated.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.revisions[s.rev_id].name == service.revisions[service.rev_id].name
    assert s.revisions[s.rev_id].unit_price == Decimal('1000.00')
    assert s.revisions[s.rev_id].vat_rate_id == service.revisions[service.rev_id].vat_rate_id
    assert s.revisions[s.rev_id].vat_rate is service.revisions[service.rev_id].vat_rate


def test_crud_update_idem(dbsession, init_services, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    service = init_services[0]

    updated = crud.service.update(
        dbsession,
        db_obj=service,
        obj_in=schemas.ServiceUpdate(unit_price=service.revisions[service.rev_id].unit_price),
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
            obj_in=schemas.ServiceUpdate(name="Wonderful service"),
        )

    assert (
        dbsession.scalars(
            sa.select(models.ServiceRevision)
            .where(models.ServiceRevision.name == "Wonderful service")
        ).first()
        is None
    )


def test_crud_delete(dbsession, init_services):
    service = init_services[0]
    assert dbsession.get(models.Service, service.id) is not None
    assert service.revisions[service.rev_id] in dbsession.get(
        models.VatRate,
        service.revisions[service.rev_id].vat_rate_id
    ).services

    crud.service.delete(dbsession, db_obj=service)

    assert dbsession.get(models.Service, service.id) is None
    for revision in dbsession.get(
        models.VatRate,
        service.revisions[service.rev_id].vat_rate_id
    ).services:
        assert revision.service_id != service.id


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
    assert from_db.name == service.revisions[service.rev_id].name
    assert from_db.unit_price == service.revisions[service.rev_id].unit_price
    assert from_db.vat_rate.id == service.revisions[service.rev_id].vat_rate.id
    assert from_db.vat_rate.rate == service.revisions[service.rev_id].vat_rate.rate


def test_schema_from_revision(dbsession, init_services):
    service = crud.service.update(
        dbsession,
        db_obj=init_services[0],
        obj_in=schemas.ServiceUpdate(
            name="Wonderful service", unit_price=Decimal('1000.00'), vat_rate_id=2
        ),
    )

    from_db = schemas.Service.from_revision(service, service.rev_id)

    assert from_db.id == service.id
    assert from_db.name == service.revisions[service.rev_id].name
    assert from_db.unit_price == service.revisions[service.rev_id].unit_price
    assert from_db.vat_rate.id == service.revisions[service.rev_id].vat_rate.id
    assert from_db.vat_rate.rate == service.revisions[service.rev_id].vat_rate.rate
