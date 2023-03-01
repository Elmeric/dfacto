# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import pytest

from dfacto.models import api, crud, schemas
from dfacto.models.api.command import CommandStatus
from tests.conftest import FakeORMService

pytestmark = pytest.mark.api


def test_cmd_get(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False}
    state["read_value"] = FakeORMService(id=1, name="Service 1", unit_price=100.0)

    response = api.service.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Service 1"
    assert response.body.unit_price == 100.0


def test_cmd_get_unknown(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False}
    state["read_value"] = None

    response = api.service.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "GET - Object 1 not found."


def test_cmd_get_error(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": True}

    response = api.service.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET - SQL or database error")


def test_cmd_get_multi(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False}
    state["read_value"] = [
        FakeORMService(id=1, name="Service 1", unit_price=100.0),
        FakeORMService(id=2, name="Service 2", unit_price=200.0),
        FakeORMService(id=3, name="Service 3", unit_price=300.0),
        FakeORMService(id=4, name="Service 4", unit_price=400.0),
    ]

    response = api.service.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Service 2"
    assert response.body[0].unit_price == 200.0
    assert response.body[1].id == 3
    assert response.body[1].name == "Service 3"
    assert response.body[1].unit_price == 300.0


def test_cmd_get_multi_error(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": True}

    response = api.service.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-MULTI - SQL or database error")


def test_cmd_get_all(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False}
    state["read_value"] = [
        FakeORMService(id=2, name="Service 2", unit_price=200.0),
        FakeORMService(id=3, name="Service 3", unit_price=300.0),
    ]

    response = api.service.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Service 2"
    assert response.body[0].unit_price == 200.0
    assert response.body[1].id == 3
    assert response.body[1].name == "Service 3"
    assert response.body[1].unit_price == 300.0


def test_cmd_get_all_error(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": True}

    response = api.service.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-ALL - SQL or database error")


def test_cmd_add(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"CREATE": False}

    response = api.service.add(
        schemas.ServiceCreate(name="Service 2", unit_price=200.0, vat_rate_id=3)
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Service 2"
    assert response.body.unit_price == 200.0
    assert response.body.vat_rate_id == 3


def test_cmd_add_error(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"CREATE": True}

    response = api.service.add(
        schemas.ServiceCreate(name="Service 2", unit_price=200.0, vat_rate_id=3)
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD - Cannot add object")


def test_cmd_update(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMService(
        id=1, name="Service 1", unit_price=100.0, vat_rate_id=1
    )

    response = api.service.update(
        obj_id=1,
        obj_in=schemas.ServiceUpdate(name="Service 2", unit_price=200.0, vat_rate_id=3),
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Service 2"
    assert response.body.unit_price == 200.0
    assert response.body.vat_rate_id == 3


def test_cmd_update_unknown(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = None

    response = api.service.update(
        obj_id=1,
        obj_in=schemas.ServiceUpdate(name="Service 2", unit_price=200.0, vat_rate_id=3),
    )

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Object 1 not found.")


def test_cmd_update_error(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False, "UPDATE": True}
    state["read_value"] = FakeORMService(
        id=1, name="Service 1", unit_price=100.0, vat_rate_id=1
    )

    response = api.service.update(
        obj_id=1,
        obj_in=schemas.ServiceUpdate(name="Service 2", unit_price=200.0, vat_rate_id=3),
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Cannot update object 1")


def test_cmd_delete(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = FakeORMService(
        id=1, name="Service 1", unit_price=100.0, vat_rate_id=1
    )

    response = api.service.delete(obj_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is None


def test_cmd_delete_unknown(mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = None

    response = api.service.delete(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Object 1 not found.")


@pytest.mark.parametrize("error", (crud.CrudError, crud.CrudIntegrityError))
def test_cmd_delete_error(error, mock_dfacto_model, mock_schema_from_orm):
    state, methods_called = mock_dfacto_model
    state["raises"] = {"READ": False, "DELETE": error}
    state["read_value"] = FakeORMService(
        id=1, name="Service 1", unit_price=100.0, vat_rate_id=1
    )

    response = api.service.delete(obj_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    if error is crud.CrudError:
        assert response.status is CommandStatus.FAILED
        assert response.reason.startswith("DELETE - Cannot delete object 1")
    else:
        assert response.status is CommandStatus.REJECTED
        assert response.reason.startswith(
            "DELETE - Object 1 is used by at least one other object."
        )
