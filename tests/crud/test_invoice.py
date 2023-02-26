# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
import dataclasses
from datetime import date, datetime
from typing import cast

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models import db, crud, models, schemas
from tests.conftest import FAKE_TIME

pytestmark = pytest.mark.crud


def test_crud_init():
    assert crud.invoice.model is models.Invoice


def test_crud_get(dbsession, init_data):
    test_data = init_data

    invoice = crud.invoice.get(dbsession, test_data.invoices[0].id)

    assert invoice is test_data.invoices[0]


def test_crud_get_unknown(dbsession, init_data):
    test_data = init_data
    ids = [inv.id for inv in test_data.invoices]

    invoice = crud.invoice.get(dbsession, 100)

    assert 100 not in ids
    assert invoice is None


def test_crud_get_error(dbsession, init_data, mock_get):
    state, _called = mock_get
    state["failed"] = True

    test_data = init_data

    with pytest.raises(crud.CrudError):
        _invoice = crud.invoice.get(dbsession, test_data.invoices[0].id)


@pytest.mark.parametrize(
    "kwargs, offset, length",
    (
        ({}, 0, None),
        ({"limit": 2}, 0, 2),
        ({"skip": 2}, 2, None),
        ({"skip": 2, "limit": 2}, 2, 2)
    )
)
def test_crud_get_multi(kwargs, offset, length, dbsession, init_data):
    invoices = init_data.invoices

    obj_list = crud.invoice.get_multi(dbsession, **kwargs)

    skip = kwargs.get("skip", 0)
    length = length or len(invoices) - skip
    assert len(obj_list) == length
    for i, obj in enumerate(obj_list):
        assert obj is invoices[i + offset]


def test_crud_get_multi_error(dbsession, init_data, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _invoices = crud.invoice.get_multi(dbsession)


def test_crud_get_all(dbsession, init_data):
    invoices = crud.invoice.get_all(dbsession)

    for i, invoice in enumerate(invoices):
        assert invoice is init_data.invoices[i]


def test_crud_get_all_error(dbsession, init_data, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _invoices = crud.invoice.get_all(dbsession)


def test_crud_create(dbsession, init_data, mock_datetime_now):
    client = init_data.clients[1]

    invoice = crud.invoice.create(
        dbsession,
        obj_in=schemas.InvoiceCreate(client_id=client.id)
    )

    assert invoice.id is not None
    assert invoice.client_id == client.id
    assert invoice.raw_amount == 0.0
    assert invoice.vat == 0.0
    assert invoice.net_amount == 0.0
    assert invoice.status is models.InvoiceStatus.DRAFT
    assert invoice.client is client
    assert len(invoice.items) == 0
    assert len(invoice.status_log) == 1
    assert invoice.status_log[0].invoice_id == invoice.id
    assert invoice.status_log[0].status is models.InvoiceStatus.DRAFT
    assert invoice.status_log[0].from_ == FAKE_TIME
    assert invoice.status_log[0].to is None
    try:
        inv = dbsession.get(models.Invoice, invoice.id)
    except sa.exc.SQLAlchemyError:
        inv = None
    assert inv.client_id == client.id
    assert inv.raw_amount == 0.0
    assert inv.vat == 0.0
    assert inv.net_amount == 0.0
    assert inv.status is models.InvoiceStatus.DRAFT
    assert inv.client is client
    assert len(inv.items) == 0
    assert len(inv.status_log) == 1
    assert inv.status_log[0].invoice_id == inv.id
    assert inv.status_log[0].status is models.InvoiceStatus.DRAFT
    assert inv.status_log[0].from_ == FAKE_TIME
    assert inv.status_log[0].to is None


def test_crud_create_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[1]
    initial_invoices_count = len(client.invoices)
    initial_log_count = len(dbsession.scalars(sa.select(models.StatusLog)).all())

    with pytest.raises(crud.CrudError):
        _invoice = crud.invoice.create(
            dbsession,
            obj_in=schemas.InvoiceCreate(client_id=client.id)
        )
    assert len(client.invoices) == initial_invoices_count
    assert len(
        (
            dbsession.scalars(
                sa.select(models.Invoice).where(models.Invoice.client_id == client.id)
            ).all()
        )
    ) == initial_invoices_count
    assert len(dbsession.scalars(sa.select(models.StatusLog)).all()) == initial_log_count


@pytest.mark.parametrize("clear", (True, False))
def test_crud_invoice_from_basket(clear, dbsession, init_data, mock_datetime_now):
    client = init_data.clients[1]
    basket = client.basket
    raw_amount = basket.raw_amount
    vat = basket.vat
    items_count = len(basket.items)
    assert items_count > 0

    invoice = crud.invoice.invoice_from_basket(dbsession, client.basket)

    assert invoice.id is not None
    assert invoice.client_id == client.id
    assert invoice.raw_amount == raw_amount
    assert invoice.vat == vat
    assert invoice.net_amount == raw_amount + vat
    assert invoice.status is models.InvoiceStatus.DRAFT
    assert invoice.client is client
    assert len(invoice.items) == items_count
    assert len(invoice.status_log) == 1
    assert invoice.status_log[0].invoice_id == invoice.id
    assert invoice.status_log[0].status is models.InvoiceStatus.DRAFT
    assert invoice.status_log[0].from_ == FAKE_TIME
    assert invoice.status_log[0].to is None

    inv = dbsession.get(models.Invoice, invoice.id)
    assert inv.client_id == client.id
    assert inv.raw_amount == raw_amount
    assert inv.vat == vat
    assert inv.net_amount == raw_amount + vat
    assert inv.status is models.InvoiceStatus.DRAFT
    assert inv.client is client
    assert len(inv.items) == items_count
    assert len(inv.status_log) == 1
    assert inv.status_log[0].invoice_id == inv.id
    assert inv.status_log[0].status is models.InvoiceStatus.DRAFT
    assert inv.status_log[0].from_ == FAKE_TIME
    assert inv.status_log[0].to is None

    if clear:
        assert len(basket.items) == 0


def test_crud_invoice_from_basket_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[1]
    initial_invoices_count = len(client.invoices)
    initial_log_count = len(dbsession.scalars(sa.select(models.StatusLog)).all())

    with pytest.raises(crud.CrudError):
        _invoice = crud.invoice.invoice_from_basket(dbsession, client.basket)
    assert len(client.invoices) == initial_invoices_count
    assert len(
        (
            dbsession.scalars(
                sa.select(models.Invoice).where(models.Invoice.client_id == client.id)
            ).all()
        )
    ) == initial_invoices_count
    assert len(dbsession.scalars(sa.select(models.StatusLog)).all()) == initial_log_count
#
#
# def test_crud_update(dbsession, init_clients):
#     client = init_clients[0]
#
#     address = schemas.Address(
#         address="1 rue de l'église",
#         zip_code="67890",
#         city="La Bas",
#     )
#     updated = crud.client.update(
#         dbsession,
#         db_obj=client,
#         obj_in=schemas.ClientUpdate(
#             name="Super client",
#             address=address,
#             is_active=False
#         )
#     )
#
#     assert updated.id == client.id
#     assert updated.name == "Super client"
#     assert updated.address == address.address
#     assert updated.zip_code == address.zip_code
#     assert updated.city == address.city
#     assert not updated.is_active
#     try:
#         c = dbsession.get(models.Client, updated.id)
#     except sa.exc.SQLAlchemyError:
#         c = None
#     assert c.name == "Super client"
#     assert c.address == address.address
#     assert c.zip_code == address.zip_code
#     assert c.city == address.city
#     assert not c.is_active
#
#
# def test_crud_update_partial(dbsession, init_clients):
#     client = init_clients[0]
#
#     address = schemas.Address(
#         address=client.address,
#         zip_code="67890",
#         city=client.city,
#     )
#     updated = crud.client.update(
#         dbsession,
#         db_obj=client,
#         obj_in=schemas.ClientUpdate(address=address)
#     )
#
#     assert updated.id == client.id
#     assert updated.name == client.name
#     assert updated.address == client.address
#     assert updated.zip_code == address.zip_code
#     assert updated.city == client.city
#     assert updated.is_active
#     try:
#         c = dbsession.get(models.Client, updated.id)
#     except sa.exc.SQLAlchemyError:
#         c = None
#     assert c.name == client.name
#     assert c.address == client.address
#     assert c.zip_code == address.zip_code
#     assert c.city == client.city
#     assert c.is_active
#
#
# def test_crud_update_idem(dbsession, init_clients, mock_commit):
#     state, called = mock_commit
#     state["failed"] = False
#
#     client = init_clients[0]
#
#     address = schemas.Address(
#         address=client.address,
#         zip_code=client.zip_code,
#         city=client.city,
#     )
#     updated = crud.client.update(
#         dbsession,
#         db_obj=client,
#         obj_in=schemas.ClientUpdate(address=address)
#     )
#
#     assert updated == client
#     assert len(called) == 0
#
#
# def test_crud_update_error(dbsession, init_clients, mock_commit):
#     state, called = mock_commit
#     state["failed"] = True
#
#     client = init_clients[0]
#
#     with pytest.raises(crud.CrudError):
#         _updated = crud.client.update(
#             dbsession,
#             db_obj=client,
#             obj_in=schemas.ClientUpdate(name="Wonderful client")
#         )
#
#     assert (
#         dbsession.scalars(
#             sa.select(models.Client).where(models.Client.name == "Wonderful client")
#         ).first()
#         is None
#     )
#
#
# def test_crud_delete(dbsession, init_clients):
#     client = init_clients[0]
#     assert dbsession.get(models.Client, client.id) is not None
#
#     crud.client.delete(dbsession, db_obj=client)
#
#     assert dbsession.get(models.Client, client.id) is None
#
#
# def test_crud_delete_error(dbsession, init_clients, mock_commit):
#     state, called = mock_commit
#     state["failed"] = True
#
#     client = init_clients[0]
#     assert dbsession.get(models.Client, client.id) is not None
#
#     with pytest.raises(crud.CrudError):
#         crud.client.delete(dbsession, db_obj=client)
#
#     assert dbsession.get(models.Client, client.id) is not None
#
#
# def test_crud_add_to_basket(dbsession, init_clients, init_services):
#     client = init_clients[0]
#     service = init_services[0]
#
#     item = crud.client.add_to_basket(
#         dbsession, basket=client.basket, service=service, quantity=2
#     )
#
#     assert item.service_id == service.id
#     assert item.quantity == 2
#     assert item.raw_amount == service.unit_price * 2
#     assert item.vat == service.vat_rate.rate
#     assert item.net_amount == item.raw_amount + item.vat
#     assert item.basket_id == client.basket.id
#     assert len(client.basket.items) == 1
#     assert client.basket.items[0] == item
#     assert client.basket.raw_amount == item.raw_amount
#     assert client.basket.vat == item.vat
#     assert client.basket.net_amount == item.net_amount
#
#
# def test_crud_add_to_basket_default_qty(dbsession, init_clients, init_services):
#     client = init_clients[0]
#     service = init_services[0]
#
#     item = crud.client.add_to_basket(dbsession, basket=client.basket, service=service)
#
#     assert item.service_id == service.id
#     assert item.quantity == 1
#     assert item.raw_amount == service.unit_price
#     assert item.vat == service.vat_rate.rate
#     assert item.net_amount == item.raw_amount + item.vat
#     assert item.basket_id == client.basket.id
#     assert len(client.basket.items) == 1
#     assert client.basket.items[0] == item
#     assert client.basket.raw_amount == item.raw_amount
#     assert client.basket.vat == item.vat
#     assert client.basket.net_amount == item.net_amount
#
#
# def test_crud_add_to_basket_commit_error(
#     dbsession, init_clients, init_services, mock_commit
# ):
#     state, _called = mock_commit
#     state["failed"] = True
#
#     client = init_clients[0]
#     service = init_services[0]
#
#     with pytest.raises(crud.CrudError):
#         _item = crud.client.add_to_basket(
#             dbsession, basket=client.basket, service=service, quantity=2
#         )
#
#     assert len(client.basket.items) == 0
#     assert client.basket.raw_amount == 0.0
#     assert client.basket.vat == 0.0
#     assert client.basket.net_amount == 0.0
#
#
# def test_crud_update_item_quantity(dbsession, init_items):
#     item = init_items[0]
#     assert item.quantity == 1
#     basket = item.basket
#     raw_amount = item.raw_amount
#     vat = item.vat
#     net_amount = item.net_amount
#     expected_raw_amount = raw_amount * 2
#     expected_vat = vat * 2
#     expected_net_amount = net_amount * 2
#     expected_basket_raw_amount = basket.raw_amount - raw_amount + expected_raw_amount
#     expected_basket_vat = basket.vat - vat + expected_vat
#     expected_basket_net_amount = basket.net_amount - net_amount + expected_net_amount
#
#     crud.client.update_item_quantity(dbsession, db_obj=item, quantity=2)
#
#     assert item.quantity == 2
#     assert item.raw_amount == expected_raw_amount
#     assert item.vat == expected_vat
#     assert item.net_amount == expected_net_amount
#     assert basket.raw_amount == expected_basket_raw_amount
#     assert basket.vat == expected_basket_vat
#     assert basket.net_amount == expected_basket_net_amount
#
#
# def test_crud_update_item_quantity_commit_error(dbsession, init_items, mock_commit):
#     state, _called = mock_commit
#     state["failed"] = True
#
#     item = init_items[0]
#     assert item.quantity == 1
#     basket = item.basket
#     expected_raw_amount = item.raw_amount
#     expected_vat = item.vat
#     expected_net_amount = item.net_amount
#     expected_basket_raw_amount = basket.raw_amount
#     expected_basket_vat = basket.vat
#     expected_basket_net_amount = basket.net_amount
#
#     with pytest.raises(crud.CrudError):
#         crud.client.update_item_quantity(dbsession, db_obj=item, quantity=2)
#
#     assert item.quantity == 1
#     assert item.raw_amount == expected_raw_amount
#     assert item.vat == expected_vat
#     assert item.net_amount == expected_net_amount
#     assert basket.raw_amount == expected_basket_raw_amount
#     assert basket.vat == expected_basket_vat
#     assert basket.net_amount == expected_basket_net_amount
#
#
# def test_crud_remove_from_basket_no_invoice(dbsession, init_items):
#     item = init_items[0]
#     item_id = item.id
#     basket = item.basket
#     expected_raw_amount = basket.raw_amount - item.raw_amount
#     expected_vat = basket.vat - item.vat
#     expected_net_amount = basket.net_amount - item.net_amount
#
#     crud.client.remove_from_basket(dbsession, db_obj=item)
#
#     assert (
#         dbsession.scalars(
#             sa.select(models.Item).where(models.Item.id == item_id)
#         ).first()
#         is None
#     )
#
#     assert len(basket.items) == 1
#     assert basket.raw_amount == expected_raw_amount
#     assert basket.vat == expected_vat
#     assert basket.net_amount == expected_net_amount
#
#
# @pytest.mark.xfail(reason="Invoices not implemented")
# def test_crud_remove_from_basket_in_invoice(dbsession, init_items):
#     # TODO
#     item = init_items[0]
#     item_id = item.id
#     basket = item.basket
#     expected_raw_amount = basket.raw_amount - item.raw_amount
#     expected_vat = basket.vat - item.vat
#     expected_net_amount = basket.net_amount - item.net_amount
#
#     crud.client.remove_from_basket(dbsession, db_obj=item)
#
#     it = dbsession.scalars(
#         sa.select(models.Item).where(models.Item.id == item_id)
#     ).first()
#     assert it == item
#
#     assert len(basket.items) == 1
#     assert basket.raw_amount == expected_raw_amount
#     assert basket.vat == expected_vat
#     assert basket.net_amount == expected_net_amount
#
#
# def test_crud_remove_from_basket_commit_error(dbsession, init_items, mock_commit):
#     state, _called = mock_commit
#     state["failed"] = True
#
#     item = init_items[0]
#     item_id = item.id
#     basket = item.basket
#     raw_amount = basket.raw_amount
#     vat = basket.vat
#     net_amount = basket.net_amount
#
#     with pytest.raises(crud.CrudError):
#         crud.client.remove_from_basket(dbsession, db_obj=item)
#
#     it = dbsession.scalars(
#         sa.select(models.Item).where(models.Item.id == item_id)
#     ).first()
#     assert it == item
#
#     assert len(basket.items) == 2
#     assert basket.items[0] == it
#     assert basket.raw_amount == raw_amount
#     assert basket.vat == vat
#     assert basket.net_amount == net_amount
#
#
# def test_crud_clear_basket_no_invoice(dbsession, init_items):
#     item1 = init_items[0]
#     item_id1 = item1.id
#     basket = item1.basket
#     item2 = init_items[5]
#     item_id2 = item2.id
#     assert basket == item2.basket
#     expected_raw_amount = basket.raw_amount - item1.raw_amount - item2.raw_amount
#     expected_vat = basket.vat - item1.vat - item2.vat
#     expected_net_amount = basket.net_amount - item1.net_amount - item2.net_amount
#
#     crud.client.clear_basket(dbsession, db_obj=basket)
#
#     assert (
#         dbsession.scalars(
#             sa.select(models.Item).where(models.Item.id == item_id1)
#         ).first()
#         is None
#     )
#     assert (
#         dbsession.scalars(
#             sa.select(models.Item).where(models.Item.id == item_id2)
#         ).first()
#         is None
#     )
#
#     assert len(basket.items) == 0
#     assert basket.raw_amount == expected_raw_amount
#     assert basket.vat == expected_vat
#     assert basket.net_amount == expected_net_amount
#
#
# @pytest.mark.xfail(reason="Invoices not implemented")
# def test_crud_clear_basket_in_invoice(dbsession, init_items):
#     # TODO
#     item1 = init_items[0]
#     item_id1 = item1.id
#     basket = item1.basket
#     item2 = init_items[5]
#     item_id2 = item2.id
#     assert basket == item2.basket
#     expected_raw_amount = basket.raw_amount - item1.raw_amount - item2.raw_amount
#     expected_vat = basket.vat - item1.vat - item2.vat
#     expected_net_amount = basket.net_amount - item1.net_amount - item2.net_amount
#
#     crud.client.clear_basket(dbsession, db_obj=basket)
#
#     it1 = dbsession.scalars(
#         sa.select(models.Item).where(models.Item.id == item_id1)
#     ).first()
#     assert it1 == item1
#     it2 = dbsession.scalars(
#         sa.select(models.Item).where(models.Item.id == item_id2)
#     ).first()
#     assert it2 == item2
#
#     assert len(basket.items) == 0
#     assert basket.raw_amount == expected_raw_amount
#     assert basket.vat == expected_vat
#     assert basket.net_amount == expected_net_amount
#
#
# def test_crud_clear_basket_commit_error(dbsession, init_items, mock_commit):
#     state, _called = mock_commit
#     state["failed"] = True
#
#     item1 = init_items[0]
#     item_id1 = item1.id
#     basket = item1.basket
#     item2 = init_items[5]
#     item_id2 = item2.id
#     assert basket == item2.basket
#     expected_raw_amount = basket.raw_amount
#     expected_vat = basket.vat
#     expected_net_amount = basket.net_amount
#
#     with pytest.raises(crud.CrudError):
#         crud.client.clear_basket(dbsession, db_obj=basket)
#
#     it1 = dbsession.scalars(
#         sa.select(models.Item).where(models.Item.id == item_id1)
#     ).first()
#     assert it1 == item1
#     it2 = dbsession.scalars(
#         sa.select(models.Item).where(models.Item.id == item_id2)
#     ).first()
#     assert it2 == item2
#
#     assert len(basket.items) == 2
#     assert basket.raw_amount == expected_raw_amount
#     assert basket.vat == expected_vat
#     assert basket.net_amount == expected_net_amount
#
#
# def test_client_from_orm(dbsession, init_clients):
#     client = init_clients[0]
#
#     from_db = schemas.Client.from_orm(client)
#
#     assert from_db.id == client.id
#     assert from_db.name == client.name
#     assert from_db.address == schemas.Address(client.address, client.zip_code, client.city)
#     assert from_db.is_active is client.is_active
#     assert from_db.code == f"CL{str(from_db.id).zfill(5)}"
#
#
# def test_basket_from_orm(dbsession, init_clients):
#     basket = init_clients[0].basket
#
#     from_db = schemas.Basket.from_orm(basket)
#
#     assert from_db.id == basket.id
#     assert from_db.raw_amount == basket.raw_amount
#     assert from_db.vat == basket.vat
#     assert from_db.net_amount == basket.net_amount
#     for i, item in enumerate(from_db.items):
#         assert item == schemas.Item.from_orm(basket.items[i])
#
#
# def test_item_from_orm(dbsession, init_items):
#     item = init_items[0]
#
#     from_db = schemas.Item.from_orm(item)
#
#     assert from_db.id == item.id
#     assert from_db.raw_amount == item.raw_amount
#     assert from_db.vat == item.vat
#     assert from_db.net_amount == item.net_amount
#     assert from_db.service_id == item.service_id
#     assert from_db.quantity == item.quantity
#     assert from_db.service == schemas.Service.from_orm(item.service)
