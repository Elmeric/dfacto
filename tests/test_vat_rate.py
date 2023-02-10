# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for `dfacto` package."""

# Cf. https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2

from typing import cast
from collections import namedtuple

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models.api.command import CommandResponse, CommandStatus
from dfacto.models import db, crud, models, schemas
from dfacto.models.api.api_v1.vat_rate import VatRateModel
from.conftest import FakeCRUDBase


class FakeCRUDVatRate(FakeCRUDBase, crud.CRUDVatRate):
    pass


FakeORMVatRate = namedtuple("VatRate", ["id", "rate", "services"])
FakeORMService = namedtuple("Service", ["id", "name", "unit_price"])


class FakeVatRate(schemas.VatRate):
    @classmethod
    def from_orm(cls, obj):
        return obj


@pytest.fixture
def init_vat_rates(dbsession: sa.orm.scoped_session) -> list[models.VatRate]:
    db.init_db_data(dbsession)

    for i in range(3):
        vat_rate = models.VatRate(
            rate=10 + 2.5*i     # 10, 12.5, 15
        )
        dbsession.add(vat_rate)
        dbsession.commit()

    vat_rates = cast(
        list[models.VatRate],
        dbsession.scalars(sa.select(models.VatRate)).all()
    )
    return vat_rates


@pytest.fixture
def vat_rate_model(dbsession):
    return VatRateModel(dbsession)


def test_crud_init():
    assert crud.vat_rate.model is models.VatRate


def test_crud_get(dbsession, init_vat_rates):
    vat_rates = init_vat_rates

    vat_rate = crud.vat_rate.get(dbsession, id_=vat_rates[0].id)

    assert vat_rate is vat_rates[0]


def test_crud_get_unknown(dbsession, init_vat_rates):
    vat_rates = init_vat_rates
    ids = [vr.id for vr in vat_rates]

    vat_rate = crud.vat_rate.get(dbsession, id_=100)

    assert 100 not in ids
    assert vat_rate is None


def test_crud_get_error(dbsession, init_vat_rates, mock_get):
    state, _called = mock_get
    state["failed"] = True

    vat_rates = init_vat_rates

    with pytest.raises(crud.CrudError):
        _vat_rate = crud.vat_rate.get(dbsession, id_=vat_rates[0].id)


@pytest.mark.parametrize(
    "kwargs, offset, length",
    (
        ({}, 0, 6),
        ({"limit": 2}, 0, 2),
        ({"skip": 2}, 2, 4),
        ({"skip": 2, "limit": 2}, 2, 2)
    )
)
def test_crud_get_multi(kwargs, offset, length, dbsession, init_vat_rates):
    vat_rates = init_vat_rates

    obj_list = crud.vat_rate.get_multi(dbsession, **kwargs)

    assert len(obj_list) == length
    for i, obj in enumerate(obj_list):
        assert obj is vat_rates[i + offset]


def test_crud_get_multi_error(dbsession, init_vat_rates, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _vat_rates = crud.vat_rate.get_multi(dbsession)


def test_crud_create(dbsession, init_vat_rates):
    vat_rate = crud.vat_rate.create(
        dbsession,
        obj_in=schemas.VatRateCreate(rate=30.0)
    )

    assert vat_rate.id is not None
    assert vat_rate.rate == 30.0
    try:
        s = dbsession.get(models.VatRate, vat_rate.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.rate == 30.0


def test_crud_create_error(dbsession, init_vat_rates, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _vat_rate = crud.vat_rate.create(
            dbsession,
            obj_in=schemas.VatRateCreate(rate=30.0)
        )
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
        ).first()
        is None
    )


@pytest.mark.parametrize("obj_in_factory", (schemas.VatRateUpdate, dict))
def test_crud_update(obj_in_factory, dbsession, init_vat_rates):
    vat_rate = init_vat_rates[0]

    updated = crud.vat_rate.update(
        dbsession,
        db_obj=vat_rate,
        obj_in=obj_in_factory(rate=30.0)
    )

    assert updated.id == vat_rate.id
    assert updated.rate == 30.0
    try:
        s = dbsession.get(models.VatRate, updated.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.rate == 30.0


def test_crud_update_idem(dbsession, init_vat_rates, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    vat_rate = init_vat_rates[0]

    updated = crud.vat_rate.update(
        dbsession,
        db_obj=vat_rate,
        obj_in=schemas.VatRateUpdate(rate=vat_rate.rate)
    )

    assert updated is vat_rate
    assert len(called) == 0


def test_crud_update_error(dbsession, init_vat_rates, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    vat_rate = init_vat_rates[0]

    with pytest.raises(crud.CrudError):
        _updated = crud.vat_rate.update(
            dbsession,
            db_obj=vat_rate,
            obj_in=schemas.VatRateUpdate(rate=30.0)
        )

    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
        ).first()
        is None
    )


def test_crud_delete(dbsession, init_vat_rates):
    vat_rate = init_vat_rates[0]
    assert dbsession.get(models.VatRate, vat_rate.id) is not None

    crud.vat_rate.delete(dbsession, db_obj=vat_rate)

    assert dbsession.get(models.VatRate, vat_rate.id) is None


def test_crud_delete_error(dbsession, init_vat_rates, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    vat_rate = init_vat_rates[0]
    assert dbsession.get(models.VatRate, vat_rate.id) is not None

    with pytest.raises(crud.CrudError):
        crud.vat_rate.delete(dbsession, db_obj=vat_rate)

    assert dbsession.get(models.VatRate, vat_rate.id) is not None


def test_schema_from_orm(dbsession, init_vat_rates):
    vat_rate = init_vat_rates[0]

    from_db = schemas.VatRate.from_orm(vat_rate)

    assert from_db.id == vat_rate.id
    assert from_db.rate == vat_rate.rate


def test_cmd_get(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False},
            read_value=dict(id=1, rate=30.0)
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.get(obj_id=1)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body["id"] == 1
    assert response.body["rate"] == 30.0


def test_cmd_get_unknown(dbsession):
    crud_object = FakeCRUDVatRate(raises={"READ": False}, read_value=None)
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.get(obj_id=1)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "GET - Object 1 not found."


def test_cmd_get_error(dbsession):
    crud_object = FakeCRUDVatRate(raises={"READ": True})
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.get(obj_id=1)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET - SQL or database error")


def test_cmd_get_default(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False},
            read_value=dict(id=db.DEFAULT_RATE_ID, rate=0.0)
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.get_default()

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body["id"] == db.DEFAULT_RATE_ID
    assert response.body["rate"] == 0.0


def test_cmd_get_multi(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False},
            read_value=[
                dict(id=1,rate=10.0),
                dict(id=2, rate=20.0),
                dict(id=3, rate=30.0),
                dict(id=4, rate=40.0),
            ]
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.get_multi(skip=1, limit=2)

    assert len(crud_object.methods_called) == 1
    assert "GET_MULTI" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0]["id"] == 2
    assert response.body[0]["rate"] == 20.0
    assert response.body[1]["id"] == 3
    assert response.body[1]["rate"] == 30.0


def test_cmd_get_multi_error(dbsession):
    crud_object = FakeCRUDVatRate(raises={"READ": True})
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.get_multi(skip=1, limit=2)

    assert len(crud_object.methods_called) == 1
    assert "GET_MULTI" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-MULTI - SQL or database error")


def test_cmd_get_all(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False},
            read_value=[
                dict(id=2, rate=20.0),
                dict(id=3, rate=30.0),
            ]
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.get_all()

    assert len(crud_object.methods_called) == 1
    assert "GET_ALL" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0]["id"] == 2
    assert response.body[0]["rate"] == 20.0
    assert response.body[1]["id"] == 3
    assert response.body[1]["rate"] == 30.0


def test_cmd_get_all_error(dbsession):
    crud_object = FakeCRUDVatRate(raises={"READ": True})
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.get_all()

    assert len(crud_object.methods_called) == 1
    assert "GET_ALL" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-ALL - SQL or database error")


def test_cmd_add(dbsession):
    crud_object = FakeCRUDVatRate(raises={"CREATE": False})
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.add(
        schemas.VatRateCreate(rate=20.0)
    )

    assert len(crud_object.methods_called) == 1
    assert "CREATE" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.rate == 20.0


def test_cmd_add_error(dbsession):
    crud_object = FakeCRUDVatRate(raises={"CREATE": True})
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.add(
        schemas.VatRateCreate(rate=20.0)
    )

    assert len(crud_object.methods_called) == 1
    assert "CREATE" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD - Cannot add object")


def test_cmd_update(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False, "UPDATE": False},
            read_value=dict(id=1, rate=100.0)
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.update(
        obj_id=1,
        obj_in=schemas.VatRateUpdate(rate=20.0)
    )

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "UPDATE" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body["id"] == 1
    assert response.body["rate"] == 20.0


def test_cmd_update_unknown(dbsession):
    crud_object = FakeCRUDVatRate(raises={"READ": False, "UPDATE": False}, read_value=None)
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.update(
        obj_id=1,
        obj_in=schemas.VatRateUpdate(rate=20.0)
    )

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Object 1 not found.")


def test_cmd_update_error(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False, "UPDATE": True},
            read_value=dict(id=1, rate=10.0)
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.update(
        obj_id=1,
        obj_in=schemas.VatRateUpdate(rate=200.0)
    )

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "UPDATE" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Cannot update object 1")


def test_cmd_delete(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False, "DELETE": False},
            read_value=FakeORMVatRate(id=4, rate=10.0, services=[])
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.delete(vat_rate_id=4)

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "DELETE" in crud_object.methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is None


def test_cmd_delete_default(dbsession):
    crud_object = FakeCRUDVatRate(
        raises={"READ": False, "DELETE": False},
        read_value=None
    )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.delete(vat_rate_id=1)

    assert len(crud_object.methods_called) == 0
    assert response.status is CommandStatus.REJECTED
    assert response.reason.startswith("DELETE - Default VAT rates cannot be deleted.")


def test_cmd_delete_unknown(dbsession):
    crud_object = FakeCRUDVatRate(
        raises={"READ": False, "DELETE": False},
        read_value=None
    )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.delete(vat_rate_id=4)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Object 4 not found.")


def test_cmd_delete_in_use(dbsession):
    service = FakeORMService(id=1, name="Service 1", unit_price=100.0)
    vat_rate = FakeORMVatRate(id=4, rate=10.0, services=[service])
    crud_object = FakeCRUDVatRate(
            raises={"READ": False, "DELETE": False},
            read_value=vat_rate
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    response = vat_rate_model.delete(vat_rate_id=4)

    assert len(crud_object.methods_called) == 1
    assert "GET" in crud_object.methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "DELETE - VAT rate with id 4 is used by at least 'Service 1' service."
    assert response.body is None


def test_cmd_delete_error(dbsession):
    crud_object = FakeCRUDVatRate(
            raises={"READ": False, "DELETE": crud.CrudError},
            read_value=FakeORMVatRate(id=4, rate=10.0, services=[])
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema = FakeVatRate
    )

    response = vat_rate_model.delete(vat_rate_id=4)

    assert len(crud_object.methods_called) == 2
    assert "GET" in crud_object.methods_called
    assert "DELETE" in crud_object.methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Cannot delete object 4")


@pytest.mark.parametrize(
    "in_use, expected",
    (
        (
            True,
            CommandResponse(
                CommandStatus.FAILED,
                "VAT_RATE-RESET - Reset failed: some VAT rates may be in use."
            )
        ),
        (False, CommandResponse(CommandStatus.COMPLETED))
    )
)
def test_cmd_reset(in_use, expected, dbsession):
    service = FakeORMService(id=1, name="Service 1", unit_price=100.0)
    vat_rate_not_used = FakeORMVatRate(id=4, rate=10.0, services=[])
    vat_rate_in_use = FakeORMVatRate(id=5, rate=10.0, services=[service])
    crud_object = FakeCRUDVatRate(
            raises={"READ": False, "UPDATE": False, "DELETE": False},
            read_value=None
        )
    vat_rate_model = VatRateModel(
        dbsession,
        crud_object=crud_object,
        schema=FakeVatRate
    )

    call_count = {"UPDATE": 0, "GET_ALL":0, "DELETE": 0}

    def _update(_obj_id, _obj_in):
        call_count["UPDATE"] += 1
        return CommandResponse(CommandStatus.COMPLETED)

    def _get_all():
        call_count["GET_ALL"] += 1
        if in_use:
            return CommandResponse(CommandStatus.COMPLETED, body=[vat_rate_in_use])
        return CommandResponse(CommandStatus.COMPLETED, body=[vat_rate_not_used])

    def _delete(_obj_id):
        call_count["DELETE"] += 1
        if in_use:
            return CommandResponse(CommandStatus.REJECTED)
        return CommandResponse(CommandStatus.COMPLETED)

    vat_rate_model.update = _update
    vat_rate_model.get_all = _get_all
    vat_rate_model.delete = _delete

    response = vat_rate_model.reset()

    assert response.status is expected.status
    assert response.reason == expected.reason
    assert response.body is None
    assert call_count["UPDATE"] == 3
    assert call_count["GET_ALL"] == 1
    assert call_count["DELETE"] == 1
