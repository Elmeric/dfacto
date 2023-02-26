# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import dataclasses
from typing import Optional
from datetime import date

import pytest

from dfacto.models.api.command import CommandStatus
from dfacto.models import crud, schemas, api
from dfacto.models.models.invoice import InvoiceStatus
from dfacto.models.util import Period, PeriodFilter
from tests.conftest import FakeORMVatRate, FakeORMService, FakeORMClient, FakeORMItem, FakeORMBasket, FakeORMInvoice

pytestmark = pytest.mark.api


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
        methods_called.append("CREATE")
        exc = state["raises"]["CREATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return FakeORMInvoice(id=1, status=InvoiceStatus.DRAFT)

    monkeypatch.setattr(crud.invoice, "create", _create)
    monkeypatch.setattr(crud.invoice, "create_from_basket", _create_from_basket)

    return state, methods_called


def test_cmd_add(mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {"CREATE": False}

    response = api.invoice.add(
        schemas.InvoiceCreate(client_id=1)
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_add_error(mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {"CREATE": True}

    response = api.invoice.add(
        schemas.InvoiceCreate(client_id=1)
    )

    assert len(methods_called) == 1
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith("ADD - Cannot add object")


@pytest.mark.parametrize("clear", (True, False))
def test_cmd_create_from_basket(clear, mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CREATE": False}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket
    # state["read_value"] = FakeORMBasket(
    #     id=1,
    #     raw_amount=100.0, vat=10.0, net_amount=110.0,
    #     client_id=1,
    #     client=FakeORMClient(
    #         id=1,
    #         name="Name 1",
    #         address="Address", zip_code="12345", city="CITY"
    #     ),
    #     items=["item1", "item2"],
    # )

    response = api.invoice.create_from_basket(client_id=1, clear_basket=clear)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.COMPLETED
    assert response.body is not None


def test_cmd_create_from_basket_create_error(mock_invoice_model, mock_schema_from_orm):
    state, methods_called = mock_invoice_model
    state["raises"] = {"READ": False, "CREATE": True}
    client = FakeORMClient(
        id=1,
        name="Name 1",
        address="Address", zip_code="12345", city="CITY"
        )
    client.basket.items = ["item1", "item2"]
    state["read_value"] = client.basket

    response = api.invoice.create_from_basket(client_id=1)

    assert len(methods_called) == 2
    assert "GET" in methods_called
    assert "CREATE" in methods_called
    assert response.status is CommandStatus.FAILED
    assert response.reason.startswith(
        "CREATE_FROM-BASKET - Cannot create invoice from basket of client"
    )
