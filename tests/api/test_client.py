# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import date

import pytest

from dfacto.models.api.command import CommandStatus
from dfacto.models import crud, schemas, api
from dfacto.models.models.invoice import InvoiceStatus
from dfacto.models.util import Period, PeriodFilter
from tests.conftest import FakeORMVatRate, FakeORMService, FakeORMClient, FakeORMItem, FakeORMBasket, FakeORMInvoice

pytestmark = pytest.mark.api


@pytest.fixture()
def mock_client_model(mock_dfacto_model, monkeypatch):
    state, methods_called = mock_dfacto_model

    def _get_active(_db):
        methods_called.append("GET_ACTIVE")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _get_basket(_db, _id):
        methods_called.append("GET_BASKET")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _get_invoices(_db, _id, period):
        methods_called.append("GET_INVOICES")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _get_invoices_by_status(_db, _id, status, period):
        methods_called.append("GET_INVOICES_BY_STATUS")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _add_to_basket(_db, basket, service, quantity):
        methods_called.append("ADD_TO_BASKET")
        exc = state["raises"]["ADD_TO_BASKET"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["return_value"]

    def _update_item_quantity(_db, db_obj, quantity):
        methods_called.append("UPDATE_ITEM_QUANTITY")
        exc = state["raises"]["UPDATE_ITEM_QUANTITY"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError

    def _remove_from_basket(_db, db_obj):
        methods_called.append("REMOVE_FROM_BASKET")
        exc = state["raises"]["REMOVE_FROM_BASKET"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError

    def _clear_basket(_db, db_obj):
        methods_called.append("CLEAR_BASKET")
        exc = state["raises"]["CLEAR_BASKET"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError

    monkeypatch.setattr(crud.client, "get_active", _get_active)
    monkeypatch.setattr(crud.client, "get_basket", _get_basket)
    monkeypatch.setattr(crud.client, "get_invoices", _get_invoices)
    monkeypatch.setattr(crud.client, "get_invoices_by_status", _get_invoices_by_status)
    monkeypatch.setattr(crud.client, "add_to_basket", _add_to_basket)
    monkeypatch.setattr(crud.client, "update_item_quantity", _update_item_quantity)
    monkeypatch.setattr(crud.client, "remove_from_basket", _remove_from_basket)
    monkeypatch.setattr(crud.client, "clear_basket", _clear_basket)

    return state, methods_called


@pytest.fixture()
def mock_invoice_model(mock_dfacto_model, monkeypatch):
    state, methods_called = mock_dfacto_model

    def _create(_db, obj_in):
        methods_called.append("CREATE")
        exc = state["raises"]["CREATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)

    def _create_from_basket(_db, basket, clear_basket):
        methods_called.append("CREATE_FROM_BASKET")
        exc = state["raises"]["CREATE_FROM_BASKET"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)

    monkeypatch.setattr(crud.invoice, "create", _create)
    monkeypatch.setattr(crud.invoice, "invoice_from_basket", _create_from_basket)

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


def test_cmd_get_active(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    expected_body = [
        FakeORMClient(
            id=1,
            name="Name 1",
            address="Address", zip_code="12345", city="CITY",
            is_active=True,
        )
    ]
    state["read_value"] = expected_body

    response = api.client.get_active()

    assert len(methods_called) == 1
    assert "GET_ACTIVE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body == expected_body


def test_cmd_get_active_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True}

    response = api.client.get_active()

    assert len(methods_called) == 1
    assert "GET_ACTIVE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-ACTIVE - SQL or database error")
    assert response.body is None


def test_cmd_get_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    client.basket.items = ["item1", "item2"]
    expected_body = client.basket
    # expected_body = FakeORMBasket(
    #     id=1,
    #     raw_amount=100.0, vat=10.0, net_amount=110.0,
    #     client_id=1
    # )
    state["read_value"] = expected_body

    response = api.client.get_basket(obj_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body == expected_body


def test_cmd_get_basket_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = None

    response = api.client.get_basket(obj_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "GET-BASKET - Basket of client 1 not found."
    assert response.body is None


def test_cmd_get_basket_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True}

    response = api.client.get_basket(obj_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-BASKET - SQL or database error")
    assert response.body is None


@pytest.mark.parametrize(
    "kwargs, called",
    (
        ({}, "GET_INVOICES"),
        ({"status": InvoiceStatus.DRAFT}, "GET_INVOICES_BY_STATUS"),
        ({"filter_": PeriodFilter.CURRENT_MONTH}, "GET_INVOICES"),
        ({"period": Period(end=date(2022, 12, 31))}, "GET_INVOICES"),
        ({"status": InvoiceStatus.DRAFT, "filter_": PeriodFilter.CURRENT_MONTH}, "GET_INVOICES_BY_STATUS",)
    )
)
def test_cmd_get_invoices(kwargs, called, mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    expected_body = [FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)]
    state["read_value"] = expected_body

    response = api.client.get_invoices(obj_id=1, **kwargs)

    assert len(methods_called) == 1
    assert called in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body == expected_body


def test_cmd_get_invoices_rejected(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    expected_body = [FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)]
    state["read_value"] = expected_body

    response = api.client.get_invoices(
        obj_id=1,
        filter_=PeriodFilter.CURRENT_MONTH,
        period=Period(end=date(2022, 12, 31))
    )

    assert response.status is CommandStatus.REJECTED
    assert response.reason == "'filter' and 'period' arguments are mutually exclusive."
    assert response.body is None


def test_cmd_get_invoices_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True}

    response = api.client.get_invoices(obj_id=1)

    assert len(methods_called) == 1
    assert "GET_INVOICES" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("GET-INVOICES - SQL or database error")
    assert response.body is None


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


def test_cmd_rename(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
    )

    response = api.client.rename(obj_id=1, name="New client")

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "New client"
    assert response.body.address == "Address 1"
    assert response.body.zip_code == "1"
    assert response.body.city == "CITY 1"
    assert response.body.is_active


def test_cmd_change_address(mock_client_model, mock_schema_from_orm):
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
    response = api.client.change_address(obj_id=1, address=address)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Client 1"
    assert response.body.address == "New address"
    assert response.body.zip_code == "67890"
    assert response.body.city == "New city"
    assert response.body.is_active


@pytest.mark.parametrize("activate", (True, False))
def test_cmd_set_active(activate, mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=not activate,
    )
    if activate:
        response = api.client.set_active(obj_id=1)
    else:
        response = api.client.set_inactive(obj_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body.id == 1
    assert response.body.name == "Client 1"
    assert response.body.address == "Address 1"
    assert response.body.zip_code == "1"
    assert response.body.city == "CITY 1"
    assert response.body.is_active is activate


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
        # basket=FakeORMBasket(
        #     id=1, raw_amount=100.0, vat=10.0, net_amount=110.0, client_id=1, items=["Item 1"]
        # ),
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
        # basket=FakeORMBasket(
        #     id=1, raw_amount=100.0, vat=10.0, net_amount=110.0, client_id=1, items=["Item 1"]
        # )
    )
    client.basket.items = ["items1", "items2"]
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = client

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "DELETE - Client Client 1 has a non-empty basket and cannot be deleted."
    assert response.body is None


def test_cmd_delete_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "DELETE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1", zip_code="1", city="CITY 1",
        is_active=True,
    )

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - SQL or database error")


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


def test_cmd_add_to_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_BASKET": False}
    state["read_value"] = ("basket", "service")
    return_value = FakeORMItem(
        id=1,
        raw_amount=100.0,
        vat=10.0,
        net_amount=110.0,
        service_id=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            unit_price=50.0,
            name="Service 1",
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=10.0)
        )
    )
    state["return_value"] = return_value

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 3
    assert "GET_BASKET" in methods_called
    assert "GET" in methods_called
    assert "ADD_TO_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body == return_value


def test_cmd_add_to_basket_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "ADD_TO_BASKET": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD-TO-BASKET - SQL or database error")
    assert response.body is None


def test_cmd_add_to_basket_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_BASKET": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "ADD-TO-BASKET - Client 1 or service 1 not found."
    assert response.body is None


def test_cmd_add_to_basket_add_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_BASKET": True}
    state["read_value"] = ("basket", "service")
    state["return_value"] = None

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 3
    assert "GET_BASKET" in methods_called
    assert "GET" in methods_called
    assert "ADD_TO_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD-TO-BASKET - Cannot add to basket of client 1")
    assert response.body is None


def test_cmd_update_item_quantity(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = FakeORMItem(
        id=1,
        raw_amount=1.0,
        vat=2.0,
        net_amount=3.0,
        service_id=1,
        quantity=1,
        invoice=FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE_ITEM_QUANTITY" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is None


def test_cmd_update_item_quantity_bad_quantity(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = FakeORMItem(
        id=1,
        raw_amount=1.0,
        vat=2.0,
        net_amount=3.0,
        service_id=1,
        quantity=1,
        invoice=FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, quantity=0)

    assert len(methods_called) == 0
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "UPDATE-ITEM - Item quantity shall be at least one."
    assert response.body is None


def test_cmd_update_item_quantity_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.update_item_quantity(1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("BASKET-UPDATE-ITEM - SQL or database error")
    assert response.body is None


def test_cmd_update_item_quantity_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.update_item_quantity(1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "BASKET-UPDATE-ITEM - Item 1 not found."
    assert response.body is None


def test_cmd_update_item_quantity_in_invoice(
    mock_client_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = FakeORMItem(
        id=1,
        raw_amount=1.0,
        vat=2.0,
        net_amount=3.0,
        service_id=1,
        quantity=1,
        invoice=FakeORMInvoice(id=1, status=InvoiceStatus.EMITTED)
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "BASKET-UPDATE-ITEM - Cannot change items of a non-draft invoice."
    assert response.body is None


def test_cmd_update_item_quantity_update_error(
    mock_client_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": True}
    state["read_value"] = FakeORMItem(
        id=1,
        raw_amount=1.0,
        vat=2.0,
        net_amount=3.0,
        service_id=1,
        quantity=1,
        invoice=FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE_ITEM_QUANTITY" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("BASKET-UPDATE-ITEM - Cannot remove item 1")
    assert response.body is None


def test_cmd_remove_from_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_FROM_BASKET": False}
    state["read_value"] = "item"
    state["return_value"] = None

    response = api.client.remove_from_basket(1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "REMOVE_FROM_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is None


def test_cmd_remove_from_basket_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "REMOVE_FROM_BASKET": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.remove_from_basket(1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("REMOVE-FROM-BASKET - SQL or database error")
    assert response.body is None


def test_cmd_remove_from_basket_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_FROM_BASKET": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.remove_from_basket(1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "REMOVE-FROM-BASKET - Item 1 not found."
    assert response.body is None


def test_cmd_remove_from_basket_remove_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_FROM_BASKET": True}
    state["read_value"] = "item"
    state["return_value"] = None

    response = api.client.remove_from_basket(1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "REMOVE_FROM_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("REMOVE-FROM-BASKET - Cannot remove item 1")
    assert response.body is None


def test_cmd_clear_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "CLEAR_BASKET": False}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket
    # state["read_value"] = FakeORMBasket(
    #     id=1,
    #     raw_amount=100.0,
    #     vat=10.0,
    #     net_amount=110.0,
    #     client_id=1,
    #     items=["Item 1", "Item 2"]
    # )

    response = api.client.clear_basket(1)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "CLEAR_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is None


def test_cmd_clear_basket_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "CLEAR_BASKET": False}
    state["read_value"] = None

    response = api.client.clear_basket(1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("CLEAR-BASKET - SQL or database error")
    assert response.body is None


def test_cmd_clear_basket_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "CLEAR_BASKET": False}
    state["read_value"] = None

    response = api.client.clear_basket(1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "CLEAR-BASKET - Basket of client 1 not found."
    assert response.body is None


def test_cmd_clear_basket_clear_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "CLEAR_BASKET": True}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket
    # state["read_value"] = FakeORMBasket(
    #     id=1,
    #     raw_amount=100.0,
    #     vat=10.0,
    #     net_amount=110.0,
    #     client_id=1,
    #     items=["Item 1", "Item 2"]
    # )

    response = api.client.clear_basket(1)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "CLEAR_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("CLEAR-BASKET - Cannot clear basket of client 1")
    assert response.body is None


def test_cmd_create_invoice(mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {"CREATE": False}

    response = api.client.create_invoice(obj_id=1)

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_create_invoice_error(mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {"CREATE": True}

    response = api.client.create_invoice(obj_id=1)

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        "CREATE-INVOICE - Cannot create an invoice for client 1"
    )
    assert response.body is None


@pytest.mark.parametrize("clear", (True, False))
def test_cmd_invoice_from_basket(
    clear, mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CREATE_FROM_BASKET": False}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket

    response = api.client.invoice_from_basket(obj_id=1, clear_basket=clear)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "CREATE_FROM_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_invoice_from_empty_basket(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CREATE": False}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    state["read_value"] = client.basket
    assert len(client.basket.items) == 0

    response = api.client.invoice_from_basket(obj_id=1, clear_basket=False)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_invoice_from_basket_get_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": True, "CREATE_FROM_BASKET": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.invoice_from_basket(obj_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("CREATE-FROM-BASKET - SQL or database error")
    assert response.body is None


def test_cmd_invoice_from_basket_unknown(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CREATE_FROM_BASKET": False}
    state["read_value"] = None

    response = api.client.invoice_from_basket(obj_id=1)

    assert len(methods_called) == 1
    assert "GET_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "CREATE_FROM-BASKET - Basket of client 1 not found."
    assert response.body is None


def test_cmd_invoice_from_basket_create_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CREATE_FROM_BASKET": True}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket

    response = api.client.invoice_from_basket(obj_id=1)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "CREATE_FROM_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        "CREATE_FROM-BASKET - Cannot create invoice from basket of client 1"
    )
    assert response.body is None
