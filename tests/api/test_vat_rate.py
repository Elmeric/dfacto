# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import dataclasses

import pytest

from dfacto.models.api.command import CommandStatus
from dfacto.models import crud, schemas, api
from tests.conftest import FakeORMModel
from tests.api.test_service import FakeORMService

pytestmark = pytest.mark.api


@dataclasses.dataclass
class FakeORMVatRate(FakeORMModel):
    rate: float
    name: str = "Rate"
    is_default: bool = False
    is_preset: bool = False
    services: list["FakeORMService"] = dataclasses.field(default_factory=list)


@pytest.fixture()
def mock_schema_from_orm(monkeypatch):
    def _from_orm(obj):
        return obj

    monkeypatch.setattr(schemas.VatRate, "from_orm", _from_orm)


@pytest.fixture()
def mock_vat_rate_model(mock_dfacto_model, monkeypatch):
    state, methods_called = mock_dfacto_model

    def _get_default(_db):
        methods_called.append("GET_DEFAULT")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _set_default(_db, obj_id: int):
        methods_called.append("SET_DEFAULT")
        exc = state["raises"]["UPDATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return None

    monkeypatch.setattr(crud.vat_rate, "get_default", _get_default)
    monkeypatch.setattr(crud.vat_rate, "set_default", _set_default)

    return state, methods_called


def test_cmd_get(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False}
    state["read_value"] = FakeORMVatRate(id=1, rate=30.0)

    response = api.vat_rate.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.rate == 30.0


def test_cmd_get_unknown(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False}
    state["read_value"] = None

    response = api.vat_rate.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "GET - Object 1 not found."


def test_cmd_get_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": True}

    response = api.vat_rate.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET - SQL or database error")


def test_cmd_get_default_1(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False}
    state["read_value"] = FakeORMVatRate(id=1, name="Rate 1", rate=0.0, is_default=True)

    response = api.vat_rate.get_default()

    assert len(methods_called) == 1
    assert "GET_DEFAULT" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.rate == 0.0
    assert response.body.name == "Rate 1"
    assert response.body.is_default
    assert not response.body.is_preset


def test_cmd_get_default(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False}
    state["read_value"] = FakeORMVatRate(id=1, name="Rate 1", rate=0.0, is_default=True)

    response = api.vat_rate.get_default()

    assert len(methods_called) == 1
    assert "GET_DEFAULT" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.rate == 0.0
    assert response.body.name == "Rate 1"
    assert response.body.is_default
    assert not response.body.is_preset


def test_cmd_set_default(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"UPDATE": False}

    response = api.vat_rate.set_default(6)

    assert len(methods_called) == 1
    assert "SET_DEFAULT" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is None


def test_cmd_set_default_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"UPDATE": True}

    response = api.vat_rate.set_default(6)

    assert len(methods_called) == 1
    assert "SET_DEFAULT" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("SET_DEFAULT - SQL or database error")


def test_cmd_get_multi(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False}
    state["read_value"] = [
            FakeORMVatRate(id=1, name="Rate 1", rate=10.0),
            FakeORMVatRate(id=2, name="Rate 2", rate=20.0),
            FakeORMVatRate(id=3, name="Rate 3", rate=30.0),
            FakeORMVatRate(id=4, name="Rate 4", rate=40.0),
        ]

    response = api.vat_rate.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Rate 2"
    assert response.body[0].rate == 20.0
    assert response.body[1].id == 3
    assert response.body[1].name == "Rate 3"
    assert response.body[1].rate == 30.0


def test_cmd_get_multi_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": True}

    response = api.vat_rate.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-MULTI - SQL or database error")


def test_cmd_get_all(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False}
    state["read_value"] = [
            FakeORMVatRate(id=2, name="Rate 2", rate=20.0),
            FakeORMVatRate(id=3, name="Rate 3", rate=30.0),
        ]

    response = api.vat_rate.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Rate 2"
    assert response.body[0].rate == 20.0
    assert response.body[1].id == 3
    assert response.body[1].name == "Rate 3"
    assert response.body[1].rate == 30.0


def test_cmd_get_all_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": True}

    response = api.vat_rate.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-ALL - SQL or database error")


def test_cmd_add(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"CREATE": False}

    response = api.vat_rate.add(schemas.VatRateCreate(name="A new rate", rate=20.0))

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "A new rate"
    assert response.body.rate == 20.0
    assert not response.body.is_default
    assert not response.body.is_preset


def test_cmd_add_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"CREATE": True}

    response = api.vat_rate.add(schemas.VatRateCreate(name="A new rate", rate=20.0))

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD - Cannot add object")


def test_cmd_update(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMVatRate(
            id=1, name="Rate", rate=100.0, is_default=False, is_preset=False, services=[]
        )

    response = api.vat_rate.update(
        obj_id=1,
        obj_in=schemas.VatRateUpdate(rate=20.0)
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.rate == 20.0


def test_cmd_update_unknown(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = None

    response = api.vat_rate.update(
        obj_id=1,
        obj_in=schemas.VatRateUpdate(rate=20.0)
    )

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Object 1 not found.")


def test_cmd_update_preset(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMVatRate(
            id=1, name="Rate", rate=10.0, is_default=False, is_preset=True, services=[]
        )

    response = api.vat_rate.update(
        obj_id=1,
        obj_in=schemas.VatRateUpdate(rate=20.0)
    )

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason.startswith("UPDATE - Preset VAT rates cannot be changed.")


def test_cmd_update_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": True}
    state["read_value"] = FakeORMVatRate(
        id=1, name="Rate", rate=100.0, is_default=False, is_preset=False, services=[]
    )

    response = api.vat_rate.update(
        obj_id=1,
        obj_in=schemas.VatRateUpdate(rate=200.0)
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Cannot update object 1")


def test_cmd_delete(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = FakeORMVatRate(
        id=4, name="Rate", rate=10.0, is_default=False, is_preset=False, services=[]
    )

    response = api.vat_rate.delete(vat_rate_id=4)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is None


def test_cmd_delete_preset(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = FakeORMVatRate(
        id=4, name="Rate", rate=10.0, is_default=False, is_preset=True, services=[]
    )

    response = api.vat_rate.delete(vat_rate_id=4)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason.startswith("DELETE - Preset VAT rates cannot be deleted.")


def test_cmd_delete_unknown(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = None

    response = api.vat_rate.delete(vat_rate_id=4)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Object 4 not found.")


def test_cmd_delete_in_use(mock_vat_rate_model, mock_schema_from_orm):
    service = FakeORMService(id=1, name="Service 1", unit_price=100.0)
    vat_rate = FakeORMVatRate(
                id=4, name="Rate", rate=10.0, is_default=False, is_preset=False, services=[service]
            )
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = vat_rate

    response = api.vat_rate.delete(vat_rate_id=4)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "DELETE - VAT rate with id 4 is used by at least 'Service 1' service."
    assert response.body is None


def test_cmd_delete_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": crud.CrudError}
    state["read_value"] = FakeORMVatRate(
                id=4, name="Rate", rate=10.0, is_default=False, is_preset=False, services=[]
            )

    response = api.vat_rate.delete(vat_rate_id=4)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Cannot delete object 4")
