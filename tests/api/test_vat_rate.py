# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from decimal import Decimal

import pytest

from dfacto.backend import api, crud, schemas
from dfacto.backend.api.command import CommandStatus
from tests.api.test_service import FakeORMService
from tests.conftest import FakeORMServiceRevision, FakeORMVatRate

pytestmark = pytest.mark.api


@pytest.fixture()
def mock_vat_rate_model(mock_dfacto_model, monkeypatch):
    state, methods_called = mock_dfacto_model

    def _get_default(_db):
        methods_called.append("GET_DEFAULT")
        exc = state["raises"]["GET_DEFAULT"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["default_value"]

    def _set_default(_db, old_default, new_default):
        methods_called.append("SET_DEFAULT")
        exc = state["raises"]["SET_DEFAULT"]
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
    state["read_value"] = FakeORMVatRate(id=1, rate=Decimal("30.00"))

    response = api.vat_rate.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.rate == Decimal("30.00")


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


def test_cmd_get_default(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"GET_DEFAULT": False}
    state["default_value"] = FakeORMVatRate(
        id=1, name="Rate 1", rate=Decimal("0.00"), is_default=True
    )

    response = api.vat_rate.get_default()

    assert len(methods_called) == 1
    assert "GET_DEFAULT" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is not None


def test_cmd_set_default(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"GET_DEFAULT": False, "READ": False, "SET_DEFAULT": False}
    state["default_value"] = FakeORMVatRate(
        id=1, name="Rate 1", rate=Decimal("0.00"), is_default=True
    )
    state["read_value"] = FakeORMVatRate(
        id=6, name="Rate 1", rate=Decimal("0.00"), is_default=False
    )

    response = api.vat_rate.set_default(6)

    assert len(methods_called) == 3
    assert "GET_DEFAULT" in methods_called
    assert "GET" in methods_called
    assert "SET_DEFAULT" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is None


def test_cmd_set_default_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"GET_DEFAULT": False, "READ": False, "SET_DEFAULT": True}
    state["default_value"] = FakeORMVatRate(
        id=1, name="Rate 1", rate=Decimal("0.00"), is_default=True
    )
    state["read_value"] = FakeORMVatRate(
        id=6, name="Rate 1", rate=Decimal("0.00"), is_default=False
    )

    response = api.vat_rate.set_default(6)

    assert len(methods_called) == 3
    assert "GET_DEFAULT" in methods_called
    assert "GET" in methods_called
    assert "SET_DEFAULT" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("SET_DEFAULT - SQL or database error")
    assert response.body is None


def test_cmd_get_multi(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False}
    state["read_value"] = [
        FakeORMVatRate(id=1, name="Rate 1", rate=Decimal("10.00")),
        FakeORMVatRate(id=2, name="Rate 2", rate=Decimal("20.00")),
        FakeORMVatRate(id=3, name="Rate 3", rate=Decimal("30.00")),
        FakeORMVatRate(id=4, name="Rate 4", rate=Decimal("40.00")),
    ]

    response = api.vat_rate.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Rate 2"
    assert response.body[0].rate == Decimal("20.00")
    assert response.body[1].id == 3
    assert response.body[1].name == "Rate 3"
    assert response.body[1].rate == Decimal("30.00")


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
        FakeORMVatRate(id=2, name="Rate 2", rate=Decimal("20.00")),
        FakeORMVatRate(id=3, name="Rate 3", rate=Decimal("30.00")),
    ]

    response = api.vat_rate.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Rate 2"
    assert response.body[0].rate == Decimal("20.00")
    assert response.body[1].id == 3
    assert response.body[1].name == "Rate 3"
    assert response.body[1].rate == Decimal("30.00")


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

    response = api.vat_rate.add(
        schemas.VatRateCreate(name="A new rate", rate=Decimal("20.00"))
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "A new rate"
    assert response.body.rate == Decimal("20.00")
    assert not response.body.is_default
    assert not response.body.is_preset


def test_cmd_add_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"CREATE": True}

    response = api.vat_rate.add(
        schemas.VatRateCreate(name="A new rate", rate=Decimal("20.00"))
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD - Cannot add object")


def test_cmd_update(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMVatRate(
        id=1,
        name="Rate",
        rate=Decimal("100.00"),
        is_default=False,
        is_preset=False,
        services=[],
    )

    response = api.vat_rate.update(
        obj_id=1, obj_in=schemas.VatRateUpdate(rate=Decimal("20.00"))
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.rate == Decimal("20.00")


def test_cmd_update_unknown(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = None

    response = api.vat_rate.update(
        obj_id=1, obj_in=schemas.VatRateUpdate(rate=Decimal("20.00"))
    )

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Object 1 not found.")


def test_cmd_update_preset(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMVatRate(
        id=1,
        name="Rate",
        rate=Decimal("10.00"),
        is_default=False,
        is_preset=True,
        services=[],
    )

    response = api.vat_rate.update(
        obj_id=1, obj_in=schemas.VatRateUpdate(rate=Decimal("20.00"))
    )

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason.startswith("UPDATE - Preset VAT rates cannot be changed.")


def test_cmd_update_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "UPDATE": True}
    state["read_value"] = FakeORMVatRate(
        id=1,
        name="Rate",
        rate=Decimal("100.00"),
        is_default=False,
        is_preset=False,
        services=[],
    )

    response = api.vat_rate.update(
        obj_id=1, obj_in=schemas.VatRateUpdate(rate=Decimal("200.00"))
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
        id=4,
        name="Rate",
        rate=Decimal("10.00"),
        is_default=False,
        is_preset=False,
        services=[],
    )

    response = api.vat_rate.delete(obj_id=4)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is None


def test_cmd_delete_preset(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = FakeORMVatRate(
        id=4,
        name="Rate",
        rate=Decimal("10.00"),
        is_default=False,
        is_preset=True,
        services=[],
    )

    response = api.vat_rate.delete(obj_id=4)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason.startswith("DELETE - Preset VAT rates cannot be deleted.")


def test_cmd_delete_unknown(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = None

    response = api.vat_rate.delete(obj_id=4)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Object 4 not found.")


def test_cmd_delete_in_use(mock_vat_rate_model, mock_schema_from_orm):
    service_revision = FakeORMServiceRevision(
        id=1, name="Service 1", unit_price=Decimal("100.00")
    )
    service = FakeORMService(id=1, rev_id=1, revisions={1: service_revision})
    vat_rate = FakeORMVatRate(
        id=4,
        name="Rate",
        rate=Decimal("10.00"),
        is_default=False,
        is_preset=False,
        services=[service_revision],
    )
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = vat_rate

    response = api.vat_rate.delete(obj_id=4)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason
        == "DELETE - VAT rate with id 4 is used by at least 'Service 1' service."
    )
    assert response.body is None


def test_cmd_delete_error(mock_vat_rate_model, mock_schema_from_orm):
    state, methods_called = mock_vat_rate_model
    state["raises"] = {"READ": False, "DELETE": crud.CrudError}
    state["read_value"] = FakeORMVatRate(
        id=4,
        name="Rate",
        rate=Decimal("10.00"),
        is_default=False,
        is_preset=False,
        services=[],
    )

    response = api.vat_rate.delete(obj_id=4)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Cannot delete object 4")
