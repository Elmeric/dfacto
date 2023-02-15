# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import dataclasses
from typing import Any

import pytest

from dfacto.models.api.command import CommandStatus
from dfacto.models import crud, schemas, api
from tests.conftest import FakeORMModel

pytestmark = pytest.mark.api


@dataclasses.dataclass
class FakeORMClient(FakeORMModel):
    name: str
    address: str
    zip_code: str
    city: str
    is_active: bool = True
    basket: "FakeORMBasket" = None
    # invoices: list["FakeORMInvoice"] = dataclasses.field(default_factory=list)
    invoices: list[str] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.basket is None:
            self.basket = FakeORMBasket(
                id=1, raw_amount=0.0, vat=0.0, net_amount=0.0, client_id=self.id, items=[]
            )

    @property
    def has_emitted_invoices(self):
        return any(invoice != "DRAFT" for invoice in self.invoices)


@dataclasses.dataclass
class FakeORMBasket(FakeORMModel):
    raw_amount: float
    vat: float
    net_amount: float
    client_id: int
    items: list[str] = dataclasses.field(default_factory=list)


@pytest.fixture()
def mock_schema_from_orm(monkeypatch):
    def _from_orm(obj):
        return obj

    monkeypatch.setattr(schemas.Client, "from_orm", _from_orm)
    monkeypatch.setattr(schemas.Basket, "from_orm", _from_orm)


@pytest.fixture()
def mock_client_model(mock_dfacto_model, monkeypatch):
    state, methods_called = mock_dfacto_model

    def _get_basket(_db, _id):
        methods_called.append("GET_BASKET")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    monkeypatch.setattr(crud.client, "get_basket", _get_basket)

    return state, methods_called


def test_cmd_get(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
    )

    response = api.client.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Name 1"
    assert response.body.address == "Address"
    assert response.body.zip_code == "12345"
    assert response.body.city == "CITY"
    assert response.body.is_active


def test_cmd_get_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = None

    response = api.client.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "GET - Object 1 not found."


def test_cmd_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True}

    response = api.client.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET - SQL or database error")


def test_cmd_get_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = FakeORMBasket(
        id=1,
        raw_amount=100.0, vat=10.0, net_amount=110.0,
        client_id=1
    )

    response = api.client.get_basket(client_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.raw_amount == 100.0
    assert response.body.vat == 10.0
    assert response.body.net_amount == 110.0


def test_cmd_get_basket_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = None

    response = api.client.get_basket(client_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "GET-BASKET - Basket of client 1 not found."


def test_cmd_get_basket_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True}

    response = api.client.get_basket(client_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-BASKET - SQL or database error")


def test_cmd_get_multi(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = [
        FakeORMClient(
            id=1,
            name="Name 1",
            address="Address 1", zip_code="1", city="CITY 1",
        ),
        FakeORMClient(
            id=2,
            name="Name 2",
            address="Address 2", zip_code="2", city="CITY 2",
        ),
        FakeORMClient(
            id=3,
            name="Name 3",
            address="Address 3", zip_code="3", city="CITY 3",
            is_active=False,
        ),
        FakeORMClient(
            id=4,
            name="Name 4",
            address="Address 4", zip_code="4", city="CITY 4",
        ),
    ]

    response = api.client.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body[0].id == 2
    assert response.body[0].name == "Name 2"
    assert response.body[0].address == "Address 2"
    assert response.body[0].zip_code == "2"
    assert response.body[0].city == "CITY 2"
    assert response.body[0].is_active
    assert response.body[1].id == 3
    assert response.body[1].name == "Name 3"
    assert response.body[1].address == "Address 3"
    assert response.body[1].zip_code == "3"
    assert response.body[1].city == "CITY 3"
    assert not response.body[1].is_active


def test_cmd_get_multi_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True}

    response = api.client.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-MULTI - SQL or database error")


def test_cmd_get_all(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = [
        FakeORMClient(
            id=2,
            name="Name 2",
            address="Address 2", zip_code="2", city="CITY 2",
        ),
        FakeORMClient(
            id=3,
            name="Name 3",
            address="Address 3", zip_code="3", city="CITY 3",
            is_active=False,
        ),
    ]

    response = api.client.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0].id == 2
    assert response.body[0].name == "Name 2"
    assert response.body[0].address == "Address 2"
    assert response.body[0].zip_code == "2"
    assert response.body[0].city == "CITY 2"
    assert response.body[0].is_active
    assert response.body[1].id == 3
    assert response.body[1].name == "Name 3"
    assert response.body[1].address == "Address 3"
    assert response.body[1].zip_code == "3"
    assert response.body[1].city == "CITY 3"
    assert not response.body[1].is_active


def test_cmd_get_all_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True}

    response = api.client.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-ALL - SQL or database error")


@pytest.mark.parametrize("is_active", (False, None))
def test_cmd_add(is_active, mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"CREATE": False}

    address = schemas.Address(
        address="Address",
        zip_code="12345",
        city="CITY",
    )
    response = api.client.add(
        schemas.ClientCreate(name="Super client", address=address, is_active=is_active)
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Super client"
    assert response.body.address.address == "Address"
    assert response.body.address.zip_code == "12345"
    assert response.body.address.city == "CITY"
    assert response.body.is_active is is_active


def test_cmd_add_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"CREATE": True}

    address = schemas.Address(
        address="Address",
        zip_code="12345",
        city="CITY",
    )
    response = api.client.add(
        schemas.ClientCreate(name="Super client", address=address, is_active=True)
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD - Cannot add object")


def test_cmd_update(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
    )

    address = schemas.Address(
        address="New address",
        zip_code="67890",
        city="New city",
    )
    response = api.client.update(
        obj_id=1,
        obj_in=schemas.ClientUpdate(name="New client", address=address, is_active=False)
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "New client"
    assert response.body.address == "New address"
    assert response.body.zip_code == "67890"
    assert response.body.city == "New city"
    assert not response.body.is_active


def test_cmd_update_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = None

    address = schemas.Address(
        address="New address",
        zip_code="67890",
        city="New city",
    )
    response = api.client.update(
        obj_id=1,
        obj_in=schemas.ClientUpdate(name="New client", address=address, is_active=False)
    )

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Object 1 not found.")


def test_cmd_update_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": True}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
    )

    address = schemas.Address(
        address="New address",
        zip_code="67890",
        city="New city",
    )
    response = api.client.update(
        obj_id=1,
        obj_in=schemas.ClientUpdate(name="New client", address=address, is_active=False)
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE - Cannot update object 1")


def test_cmd_delete(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
    )

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is None


def test_cmd_delete_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = None

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Object 1 not found.")


def test_cmd_delete_has_emitted_invoices(mock_client_model, mock_schema_from_orm):
    # item = FakeORMItem(id=1, name="Service 1", unit_price=100.0)
    client = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
        basket=FakeORMBasket(
            id=1, raw_amount=100.0, vat=10.0, net_amount=110.0, client_id=1, items=["Item 1"]
        ),
        invoices=["EMITTED"],
    )
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = client

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "DELETE - Client Client 1 has non-DRAFT invoices and cannot be deleted."
    assert response.body is None


def test_cmd_delete_non_empty_basket(mock_client_model, mock_schema_from_orm):
    # item = FakeORMItem(id=1, name="Service 1", unit_price=100.0)
    client = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
        basket=FakeORMBasket(
            id=1, raw_amount=100.0, vat=10.0, net_amount=110.0, client_id=1, items=["Item 1"]
        )
    )
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = client

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "DELETE - Client Client 1 has a non-empty basket and cannot be deleted."
    assert response.body is None


def test_cmd_delete_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": True}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
    )

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Cannot delete object 1")
