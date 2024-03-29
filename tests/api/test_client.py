# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import date
from decimal import Decimal

import pytest

from dfacto.backend import api, crud, schemas
from dfacto.backend.api.command import CommandStatus
from dfacto.backend.models.invoice import InvoiceStatus
from dfacto.backend.util import Period, PeriodFilter
from tests.conftest import (
    FakeORMBasket,
    FakeORMClient,
    FakeORMGlobals,
    FakeORMInvoice,
    FakeORMItem,
    FakeORMService,
    FakeORMVatRate,
)

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

    def _update_item_quantity(_db, item, quantity):
        methods_called.append("UPDATE_ITEM_QUANTITY")
        exc = state["raises"]["UPDATE_ITEM_QUANTITY"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError

    def _remove_item(_db, item):
        methods_called.append("REMOVE_ITEM")
        exc = state["raises"]["REMOVE_ITEM"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError

    def _clear_basket(_db, basket):
        methods_called.append("CLEAR_BASKET")
        exc = state["raises"]["CLEAR_BASKET"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError

    def _delete(_db, db_obj):
        methods_called.append("DELETE")
        exc = state["raises"]["DELETE"]
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
    monkeypatch.setattr(crud.client, "remove_item", _remove_item)
    monkeypatch.setattr(crud.client, "clear_basket", _clear_basket)
    monkeypatch.setattr(crud.client, "delete", _delete)

    return state, methods_called


@pytest.fixture()
def mock_invoice_model(mock_dfacto_model, monkeypatch):
    state, methods_called = mock_dfacto_model

    def _get_current_globals(_db):
        methods_called.append("GET_CURRENT_GLOBALS")
        exc = state["raises"]["GET_CURRENT_GLOBALS"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["globals_value"]

    def _create(_db, obj_in):
        methods_called.append("CREATE")
        exc = state["raises"]["CREATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return FakeORMInvoice(id=1)

    def _invoice_from_basket(_db, basket, globals_id, clear_basket):
        methods_called.append("CREATE_FROM_BASKET")
        exc = state["raises"]["CREATE_FROM_BASKET"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return FakeORMInvoice(id=1)

    def _add_item(_db, invoice_, service, quantity):
        methods_called.append("ADD_TO_INVOICE")
        exc = state["raises"]["ADD_TO_INVOICE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["return_value"]

    def _clear_invoice(_db, invoice_):
        methods_called.append("CLEAR_INVOICE")
        exc = state["raises"]["CLEAR_INVOICE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["return_value"]

    def _delete_invoice(_db, invoice_):
        methods_called.append("DELETE_INVOICE")
        exc = state["raises"]["DELETE_INVOICE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["return_value"]

    def _mark_as(_db, invoice_, status):
        methods_called.append("MARK_AS")
        exc = state["raises"]["MARK_AS"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["return_value"]

    monkeypatch.setattr(crud.invoice, "get_current_globals", _get_current_globals)
    monkeypatch.setattr(crud.invoice, "create", _create)
    monkeypatch.setattr(crud.invoice, "invoice_from_basket", _invoice_from_basket)
    monkeypatch.setattr(crud.invoice, "add_item", _add_item)
    monkeypatch.setattr(crud.invoice, "clear_invoice", _clear_invoice)
    monkeypatch.setattr(crud.invoice, "delete_invoice", _delete_invoice)
    monkeypatch.setattr(crud.invoice, "mark_as", _mark_as)

    return state, methods_called


def test_cmd_get(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address",
        zip_code="12345",
        city="CITY",
        email="name_1@domain.com",
    )

    response = api.client.get(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


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
            address="Address",
            zip_code="12345",
            city="CITY",
            email="name_1@domain.com",
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
        address="Address",
        zip_code="12345",
        city="CITY",
        email="super.client@domain.com",
    )
    client.basket.items = ["item1", "item2"]
    expected_body = client.basket
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
        (
            {"status": InvoiceStatus.DRAFT, "filter_": PeriodFilter.CURRENT_MONTH},
            "GET_INVOICES_BY_STATUS",
        ),
    ),
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
        period=Period(end=date(2022, 12, 31)),
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
            address="Address 1",
            zip_code="1",
            city="CITY 1",
            email="name_1@domain.com",
        ),
        FakeORMClient(
            id=2,
            name="Name 2",
            address="Address 2",
            zip_code="2",
            city="CITY 2",
            email="name_2@domain.com",
        ),
        FakeORMClient(
            id=3,
            name="Name 3",
            address="Address 3",
            zip_code="3",
            city="CITY 3",
            email="name_3@domain.com",
            is_active=False,
        ),
        FakeORMClient(
            id=4,
            name="Name 4",
            address="Address 4",
            zip_code="4",
            city="CITY 4",
            email="name_4@domain.com",
        ),
    ]

    response = api.client.get_multi(skip=1, limit=2)

    assert len(methods_called) == 1
    assert "GET_MULTI" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body[0] is not None


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
            address="Address 2",
            zip_code="2",
            city="CITY 2",
            email="name_2@domain.com",
        ),
        FakeORMClient(
            id=3,
            name="Name 3",
            address="Address 3",
            zip_code="3",
            city="CITY 3",
            email="name_3@domain.com",
            is_active=False,
        ),
    ]

    response = api.client.get_all()

    assert len(methods_called) == 1
    assert "GET_ALL" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert len(response.body) == 2
    assert response.body[0] is not None
    assert response.body[1] is not None


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
        schemas.ClientCreate(
            name="Super client",
            address=address,
            email="super.client@domain.com",
            is_active=is_active,
        )
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_add_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"CREATE": True}

    address = schemas.Address(
        address="Address",
        zip_code="12345",
        city="CITY",
    )
    response = api.client.add(
        schemas.ClientCreate(
            name="Super client",
            address=address,
            email="super.client@domain.com",
            is_active=True,
        )
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
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )

    address = schemas.Address(
        address="New address",
        zip_code="67890",
        city="New city",
    )
    response = api.client.update(
        obj_id=1,
        obj_in=schemas.ClientUpdate(
            name="New client",
            address=address,
            email="super.client@domain.com",
            is_active=False,
        ),
    )

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


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
        obj_in=schemas.ClientUpdate(
            name="New client",
            address=address,
            email="super.client@domain.com",
            is_active=False,
        ),
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
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )

    address = schemas.Address(
        address="New address",
        zip_code="67890",
        city="New city",
    )
    response = api.client.update(
        obj_id=1,
        obj_in=schemas.ClientUpdate(
            name="New client",
            address=address,
            email="new.client@domain.com",
            is_active=False,
        ),
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
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )

    response = api.client.rename(obj_id=1, name="New client")

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_change_address(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
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
    assert response.body is not None


def test_cmd_change_email(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )

    response = api.client.change_email(obj_id=1, email="new.email@super_provider.com")

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_set_active(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=False,
    )

    response = api.client.set_active(obj_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_set_inactive(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {
        "READ": False,
        "GET_BASKET": False,
        "CLEAR_BASKET": False,
        "UPDATE": False,
    }
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )

    response = api.client.set_inactive(obj_id=1)

    assert len(methods_called) == 4
    assert "GET" in methods_called
    assert "GET_BASKET" in methods_called
    assert "CLEAR_BASKET" in methods_called
    assert "UPDATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_delete(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
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
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
        invoices=["EMITTED"],
    )
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "DELETE": False}
    state["read_value"] = client

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason
        == "DELETE - Client Client 1 has non-DRAFT invoices and cannot be deleted."
    )
    assert response.body is None


def test_cmd_delete_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "DELETE": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
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
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )

    response = api.client.delete(obj_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE - Cannot delete object 1")


def test_cmd_add_to_basket(mock_client_model, mock_service_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_BASKET": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )
    return_value = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
    )
    state["return_value"] = return_value

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 3
    assert "GET" in methods_called
    assert "GET_CURRENT" in methods_called
    assert "ADD_TO_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body == return_value


def test_cmd_add_to_basket_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "ADD_TO_BASKET": False}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )
    state["return_value"] = None

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD-TO-BASKET - SQL or database error")
    assert response.body is None


def test_cmd_add_to_basket_unknown(
    mock_client_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_BASKET": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "GET_CURRENT" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "ADD-TO-BASKET - Client 1 or service 1 not found."
    assert response.body is None


def test_cmd_add_to_basket_add_error(
    mock_client_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_BASKET": True}
    state["read_value"] = FakeORMClient(
        id=1,
        name="Client 1",
        address="Address 1",
        zip_code="1",
        city="CITY 1",
        email="client_1@domain.com",
        is_active=True,
    )
    state["return_value"] = None

    response = api.client.add_to_basket(1, service_id=1, quantity=2)

    assert len(methods_called) == 3
    assert "GET" in methods_called
    assert "GET_CURRENT" in methods_called
    assert "ADD_TO_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        "ADD-TO-BASKET - Cannot add to basket of client 1"
    )
    assert response.body is None


def test_cmd_update_item_quantity(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    item = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT),
    )
    state["read_value"] = item
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE_ITEM_QUANTITY" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is item


def test_cmd_update_item_quantity_bad_quantity(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT),
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=0)

    assert len(methods_called) == 0
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "UPDATE-ITEM - Item quantity shall be at least one."
    assert response.body is None


def test_cmd_update_item_quantity_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE-ITEM - SQL or database error")
    assert response.body is None


def test_cmd_update_item_quantity_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "UPDATE-ITEM - Item 1 not found."
    assert response.body is None


def test_cmd_update_item_quantity_bad_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        basket=FakeORMBasket(
            id=1,
            client_id=2,
            items=["items1"],
        ),
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason == "UPDATE-ITEM - Item 1 is not part of the basket of client 1."
    )
    assert response.body is None


def test_cmd_update_item_quantity_bad_invoice(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=2, status=InvoiceStatus.DRAFT),
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason
        == "UPDATE-ITEM - Item 1 is not part of any invoice of client 1."
    )
    assert response.body is None


def test_cmd_update_item_quantity_non_draft(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.EMITTED),
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason == "UPDATE-ITEM - Cannot change items of a non-draft invoice."
    )
    assert response.body is None


def test_cmd_update_item_quantity_update_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "UPDATE_ITEM_QUANTITY": True}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT),
    )
    state["return_value"] = None

    response = api.client.update_item_quantity(1, item_id=1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "UPDATE_ITEM_QUANTITY" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("UPDATE-ITEM - Cannot remove item 1")
    assert response.body is None


def test_cmd_remove_item(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_ITEM": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT),
    )
    state["return_value"] = None

    response = api.client.remove_item(1, item_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "REMOVE_ITEM" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is None


def test_cmd_remove_item_get_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "REMOVE_ITEM": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.remove_item(1, item_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("REMOVE-ITEM - SQL or database error")
    assert response.body is None


def test_cmd_remove_item_unknown(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_ITEM": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.remove_item(1, item_id=100)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "REMOVE-ITEM - Item 100 not found."
    assert response.body is None


def test_cmd_remove_item_bad_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_ITEM": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        basket=FakeORMBasket(
            id=1,
            client_id=2,
            items=["items1"],
        ),
    )
    state["return_value"] = None

    response = api.client.remove_item(1, item_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason == "REMOVE-ITEM - Item 1 is not part of the basket of client 1."
    )
    assert response.body is None


def test_cmd_remove_item_bad_invoice(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_ITEM": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=2, status=InvoiceStatus.DRAFT),
    )
    state["return_value"] = None

    response = api.client.remove_item(1, item_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason
        == "REMOVE-ITEM - Item 1 is not part of any invoice of client 1."
    )
    assert response.body is None


def test_cmd_remove_item_non_draft(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_ITEM": False}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.PAID),
    )
    state["return_value"] = None

    response = api.client.remove_item(1, item_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason == "REMOVE-ITEM - Cannot remove items from a non-draft invoice."
    )
    assert response.body is None


def test_cmd_remove_item_remove_error(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "REMOVE_ITEM": True}
    state["read_value"] = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
        invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT),
    )
    state["return_value"] = None

    response = api.client.remove_item(1, item_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "REMOVE_ITEM" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("REMOVE-ITEM - Cannot remove item 1")
    assert response.body is None


def test_cmd_clear_basket(mock_client_model, mock_schema_from_orm):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "CLEAR_BASKET": False}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address",
        zip_code="12345",
        city="CITY",
        email="name_1@domain.com",
    )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket

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
        address="Address",
        zip_code="12345",
        city="CITY",
        email="name_1@domain.com",
    )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket

    response = api.client.clear_basket(1)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "CLEAR_BASKET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("CLEAR-BASKET - Cannot clear basket of client 1")
    assert response.body is None


def test_cmd_create_invoice(mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {
        "CREATE": False,
        "GET_CURRENT_GLOBALS": False,
    }
    globals_ = FakeORMGlobals(
        id=1,
        due_delta=30,
        penalty_rate=Decimal("12.0"),
        discount_rate=Decimal("1.5"),
        is_current=True,
    )
    state["globals_value"] = globals_

    response = api.client.create_invoice(obj_id=1)

    assert len(methods_called) == 2
    assert "GET_CURRENT_GLOBALS" in methods_called
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_create_invoice_error(mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {
        "CREATE": True,
        "GET_CURRENT_GLOBALS": False,
    }
    globals_ = FakeORMGlobals(
        id=1,
        due_delta=30,
        penalty_rate=Decimal("12.0"),
        discount_rate=Decimal("1.5"),
        is_current=True,
    )
    state["globals_value"] = globals_

    response = api.client.create_invoice(obj_id=1)

    assert len(methods_called) == 2
    assert "GET_CURRENT_GLOBALS" in methods_called
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
    state["raises"] = {
        "READ": False,
        "CREATE_FROM_BASKET": False,
        "GET_CURRENT_GLOBALS": False,
    }
    globals_ = FakeORMGlobals(
        id=1,
        due_delta=30,
        penalty_rate=Decimal("12.0"),
        discount_rate=Decimal("1.5"),
        is_current=True,
    )
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address",
        zip_code="12345",
        city="CITY",
        email="name_1@domain.com",
    )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket
    state["globals_value"] = globals_

    response = api.client.invoice_from_basket(obj_id=1, clear_basket=clear)

    assert len(methods_called) == 3
    assert "GET_BASKET" in methods_called
    assert "GET_CURRENT_GLOBALS" in methods_called
    assert "CREATE_FROM_BASKET" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_invoice_from_empty_basket(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {
        "READ": False,
        "GET_CURRENT_GLOBALS": False,
        "CREATE": False,
    }
    globals_ = FakeORMGlobals(
        id=1,
        due_delta=30,
        penalty_rate=Decimal("12.0"),
        discount_rate=Decimal("1.5"),
        is_current=True,
    )
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address",
        zip_code="12345",
        city="CITY",
        email="name_1@domain.com",
    )
    state["read_value"] = client.basket
    state["globals_value"] = globals_
    assert len(client.basket.items) == 0

    response = api.client.invoice_from_basket(obj_id=1, clear_basket=False)

    assert len(methods_called) == 4
    assert "GET_BASKET" in methods_called
    assert "GET_CURRENT_GLOBALS" in methods_called  # Twice
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
    state["raises"] = {
        "READ": False,
        "GET_CURRENT_GLOBALS": False,
        "CREATE": False,
    }
    globals_ = FakeORMGlobals(
        id=1,
        due_delta=30,
        penalty_rate=Decimal("12.0"),
        discount_rate=Decimal("1.5"),
        is_current=True,
    )
    state["read_value"] = None
    state["globals_value"] = globals_

    response = api.client.invoice_from_basket(obj_id=1)

    assert len(methods_called) == 2
    assert "GET_BASKET" in methods_called
    assert "GET_CURRENT_GLOBALS" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "CREATE_FROM-BASKET - Basket of client 1 not found."
    assert response.body is None


def test_cmd_invoice_from_basket_create_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {
        "READ": False,
        "GET_CURRENT_GLOBALS": False,
        "CREATE_FROM_BASKET": True,
    }
    globals_ = FakeORMGlobals(
        id=1,
        due_delta=30,
        penalty_rate=Decimal("12.0"),
        discount_rate=Decimal("1.5"),
        is_current=True,
    )
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address",
        zip_code="12345",
        city="CITY",
        email="name_1@domain.com",
    )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket
    state["globals_value"] = globals_

    response = api.client.invoice_from_basket(obj_id=1)

    assert len(methods_called) == 3
    assert "GET_BASKET" in methods_called
    assert "CREATE_FROM_BASKET" in methods_called
    assert "GET_CURRENT_GLOBALS" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        "CREATE_FROM-BASKET - Cannot create invoice from basket of client 1"
    )
    assert response.body is None


def test_cmd_add_to_invoice(
    mock_client_model, mock_invoice_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_INVOICE": False}
    state["read_value"] = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT)
    return_value = FakeORMItem(
        id=1,
        service_id=1,
        service_version=1,
        quantity=2,
        service=FakeORMService(
            id=1,
            name="Service 1",
            unit_price=Decimal("50.00"),
            vat_rate_id=1,
            vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
        ),
    )
    state["return_value"] = return_value

    response = api.client.add_to_invoice(1, invoice_id=1, service_id=1, quantity=2)

    assert len(methods_called) == 3
    assert "GET" in methods_called
    assert "ADD_TO_INVOICE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is not None


def test_cmd_add_to_invoice_get_error(
    mock_client_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": True, "ADD_TO_INVOICE": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.add_to_invoice(1, invoice_id=1, service_id=1, quantity=2)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD-TO-INVOICE - SQL or database error")
    assert response.body is None


def test_cmd_add_to_invoice_unknown(
    mock_client_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_INVOICE": False}
    state["read_value"] = None
    state["return_value"] = None

    response = api.client.add_to_invoice(1, invoice_id=1, service_id=1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "ADD-TO-INVOICE - Invoice 1 or service 1 not found."
    assert response.body is None


def test_cmd_add_to_invoice_bad_client(
    mock_client_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_INVOICE": False}
    state["read_value"] = FakeORMInvoice(id=1, client_id=2, status=InvoiceStatus.DRAFT)
    state["return_value"] = None

    response = api.client.add_to_invoice(1, invoice_id=1, service_id=1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "ADD-TO-INVOICE - Invoice 1 is not owned by client 1."
    assert response.body is None


def test_cmd_add_to_invoice_non_draft(
    mock_client_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_INVOICE": False}
    state["read_value"] = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.PAID)
    state["return_value"] = None

    response = api.client.add_to_invoice(1, invoice_id=1, service_id=1, quantity=2)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason == "ADD-TO-INVOICE - Cannot add items to a non-draft invoice."
    )
    assert response.body is None


def test_cmd_add_to_invoice_add_error(
    mock_client_model, mock_invoice_model, mock_service_model, mock_schema_from_orm
):
    state, methods_called = mock_client_model
    state["raises"] = {"READ": False, "ADD_TO_INVOICE": True}
    state["read_value"] = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT)
    state["return_value"] = None

    response = api.client.add_to_invoice(1, invoice_id=1, service_id=1, quantity=2)

    assert len(methods_called) == 3
    assert "GET" in methods_called
    assert "ADD_TO_INVOICE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD-TO-INVOICE - Cannot add to invoice 1")
    assert response.body is None


def test_cmd_clear_invoice(mock_client_model, mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CLEAR_INVOICE": False}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT)
    invoice.items = [
        FakeORMItem(
            id=1,
            service_id=1,
            service_version=1,
            quantity=2,
            service=FakeORMService(
                id=1,
                name="Service 1",
                unit_price=Decimal("50.00"),
                vat_rate_id=1,
                vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
            ),
            basket=FakeORMBasket(
                id=1,
                client_id=2,
                items=["items1"],
            ),
            invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT),
        )
    ]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.clear_invoice(1, invoice_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "CLEAR_INVOICE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is None


def test_cmd_clear_invoice_get_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": True, "CLEAR_INVOICE": False}
    state["read_value"] = None

    response = api.client.clear_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("CLEAR-INVOICE - SQL or database error")
    assert response.body is None


def test_cmd_clear_invoice_unknown(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CLEAR_INVOICE": False}
    state["read_value"] = None

    response = api.client.clear_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "CLEAR-INVOICE - Invoice 1 not found."
    assert response.body is None


def test_cmd_clear_invoice_bad_client(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CLEAR_INVOICE": False}
    invoice = FakeORMInvoice(id=1, client_id=2, status=InvoiceStatus.DRAFT)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.clear_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "CLEAR-INVOICE - Invoice 1 is not an invoice of client 1."
    assert response.body is None


def test_cmd_clear_invoice_non_draft(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CLEAR_INVOICE": False}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.PAID)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.clear_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "CLEAR-INVOICE - Cannot clear a non-draft invoice."
    assert response.body is None


def test_cmd_clear_invoice_clear_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CLEAR_INVOICE": True}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.clear_invoice(1, invoice_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "CLEAR_INVOICE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        "CLEAR-INVOICE - Cannot clear invoice 1 of client 1"
    )
    assert response.body is None


def test_cmd_delete_invoice(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "DELETE_INVOICE": False}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT)
    invoice.items = [
        FakeORMItem(
            id=1,
            service_id=1,
            service_version=1,
            quantity=2,
            service=FakeORMService(
                id=1,
                name="Service 1",
                unit_price=Decimal("50.00"),
                vat_rate_id=1,
                vat_rate=FakeORMVatRate(id=1, rate=Decimal("10.00")),
            ),
            basket=FakeORMBasket(
                id=1,
                client_id=2,
                items=["items1"],
            ),
            invoice=FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT),
        )
    ]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.delete_invoice(1, invoice_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE_INVOICE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is None


def test_cmd_delete_invoice_get_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": True, "DELETE_INVOICE": False}
    state["read_value"] = None

    response = api.client.delete_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("DELETE-INVOICE - SQL or database error")
    assert response.body is None


def test_cmd_delete_invoice_unknown(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "DELETE_INVOICE": False}
    state["read_value"] = None

    response = api.client.delete_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "DELETE-INVOICE - Invoice 1 not found."
    assert response.body is None


def test_cmd_delete_invoice_bad_client(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "DELETE_INVOICE": False}
    invoice = FakeORMInvoice(id=1, client_id=2, status=InvoiceStatus.DRAFT)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.delete_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason == "DELETE-INVOICE - Invoice 1 is not an invoice of client 1."
    )
    assert response.body is None


def test_cmd_delete_invoice_non_draft(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "DELETE_INVOICE": False}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.PAID)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.delete_invoice(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert response.reason == "DELETE-INVOICE - Cannot delete a non-draft invoice."
    assert response.body is None


def test_cmd_delete_invoice_clear_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "DELETE_INVOICE": True}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.delete_invoice(1, invoice_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "DELETE_INVOICE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        "DELETE-INVOICE - Cannot delete invoice 1 of client 1"
    )
    assert response.body is None


@pytest.mark.parametrize(
    "cmd, prev_status",
    (
        ("mark_as_emitted", InvoiceStatus.DRAFT),
        ("mark_as_reminded", InvoiceStatus.EMITTED),
        ("mark_as_paid", InvoiceStatus.EMITTED),
        ("mark_as_cancelled", InvoiceStatus.REMINDED),
    ),
)
def test_cmd_mark_as(
    cmd, prev_status, mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "MARK_AS": False}
    invoice = FakeORMInvoice(id=1, client_id=1, status=prev_status)
    state["read_value"] = invoice
    state["return_value"] = None

    response = getattr(api.client, cmd)(1, invoice_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "MARK_AS" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.reason is None
    assert response.body is not None


def test_cmd_mark_as_get_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": True, "MARK_AS": False}
    state["read_value"] = None

    response = api.client.mark_as_emitted(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("MARK_AS-INVOICE - SQL or database error")
    assert response.body is None


def test_cmd_mark_as_unknown(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "MARK_AS": False}
    state["read_value"] = None

    response = api.client.mark_as_paid(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason == "MARK_AS-INVOICE - Invoice 1 not found."
    assert response.body is None


def test_cmd_mark_as_bad_client(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "MARK_AS": False}
    invoice = FakeORMInvoice(id=1, client_id=2, status=InvoiceStatus.EMITTED)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.mark_as_cancelled(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason == "MARK_AS-INVOICE - Invoice 1 is not an invoice of client 1."
    )
    assert response.body is None


def test_cmd_mark_as_bad_status(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "MARK_AS": False}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.PAID)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.mark_as_reminded(1, invoice_id=1)

    assert len(methods_called) == 1
    assert "GET" in methods_called
    assert response.status is CommandStatus.REJECTED
    assert (
        response.reason
        == f"MARK_AS-INVOICE - Invoice status transition from {InvoiceStatus.PAID} to {InvoiceStatus.REMINDED} is not allowed."
    )
    assert response.body is None


def test_cmd_mark_as_mark_error(
    mock_client_model, mock_invoice_model, mock_schema_from_orm
):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "MARK_AS": True}
    invoice = FakeORMInvoice(id=1, client_id=1, status=InvoiceStatus.DRAFT)
    invoice.items = ["item1", "item2"]
    state["read_value"] = invoice
    state["return_value"] = None

    response = api.client.mark_as_emitted(1, invoice_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "MARK_AS" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        f"MARK_AS-INVOICE - Cannot mark invoice 1 of client 1 as {InvoiceStatus.EMITTED}"
    )
    assert response.body is None


# TODO: How to patch the "command" decorator
# def test_cmd_preview_invoice(dbsession, init_data):
#     client_ = init_data.clients[0]
#
#     response = api.client.preview_invoice(
#         4, invoice_id=4, mode=api.client.HtmlMode.SHOW
#     )
#
#     assert response.status is CommandStatus.COMPLETED
#     assert response.reason is None
#     assert response.body is not None
