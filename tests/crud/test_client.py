# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from datetime import date
from decimal import Decimal
from random import randint
from typing import cast

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import crud, models, schemas
from dfacto.backend.db.session import init_db_data
from dfacto.backend.util import Period

pytestmark = pytest.mark.crud


@pytest.fixture
def init_clients(dbsession: Session) -> list[models.Client]:
    init_db_data(dbsession)

    for i in range(5):
        client = models.Client(
            name=f"Client_{i + 1}",
            address=f"{i * 1} rue Nationale {i + 1}",
            zip_code=f"1234{i + 1}",
            city=f"CITY_{i + 1}",
            email=f"client_{i + 1}@domain.com",
            is_active=False if i < 3 else True,
        )
        dbsession.add(client)
        dbsession.commit()

    clients = cast(
        list[models.Client], dbsession.scalars(sa.select(models.Client)).all()
    )
    return clients


@pytest.fixture
def init_services(dbsession: Session) -> list[models.Service]:
    for i in range(5):
        service = models.Service(
            id=randint(1, 10000),
            version=1,
            name=f"Service_{i + 1}",
            unit_price=Decimal(100 + 10 * i),
            vat_rate_id=(i % 3) + 1,
        )
        dbsession.add(service)
    dbsession.commit()

    services = cast(
        list[models.Service], dbsession.scalars(sa.select(models.Service)).all()
    )
    return services


@pytest.fixture
def init_items(
    init_clients, init_services, dbsession: sa.orm.Session
) -> list[models.Item]:
    clients = init_clients
    services = init_services

    for i in range(10):
        service = services[i % 5]
        quantity = i + 1
        item = models.Item(
            service_id=service.id,
            service_version=service.version,
            quantity=quantity,
        )
        basket = clients[i % 5].basket
        item.basket_id = basket.id
        dbsession.add(item)
        dbsession.commit()

    items = cast(list[models.Item], dbsession.scalars(sa.select(models.Item)).all())
    return items


def test_crud_init():
    assert crud.client.model is models.Client


def test_crud_get(dbsession, init_clients):
    clients = init_clients

    client = crud.client.get(dbsession, clients[0].id)

    assert client is clients[0]


def test_crud_get_unknown(dbsession, init_clients):
    clients = init_clients
    ids = [c.id for c in clients]

    client = crud.client.get(dbsession, 100)

    assert 100 not in ids
    assert client is None


def test_crud_get_error(dbsession, init_clients, mock_get):
    state, _called = mock_get
    state["failed"] = True

    clients = init_clients

    with pytest.raises(crud.CrudError):
        _client = crud.client.get(dbsession, clients[0].id)


def test_crud_get_active(dbsession, init_clients):
    clients = crud.client.get_active(dbsession)

    assert len(clients) == 2
    assert clients[0] is init_clients[3]
    assert clients[1] is init_clients[4]


def test_crud_get_active_error(dbsession, init_clients, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _clients = crud.client.get_active(dbsession)


def test_crud_get_basket(dbsession, init_clients):
    clients = init_clients

    basket = crud.client.get_basket(dbsession, clients[0].id)

    assert basket is clients[0].basket
    assert basket.client_id == clients[0].id
    assert len(basket.items) == 0


def test_crud_get_basket_unknown(dbsession, init_clients):
    clients = init_clients
    ids = [c.id for c in clients]

    basket = crud.client.get_basket(dbsession, 100)

    assert 100 not in ids
    assert basket is None


def test_crud_get_basket_error(dbsession, init_clients, mock_select):
    state, _called = mock_select
    state["failed"] = True

    clients = init_clients

    with pytest.raises(crud.CrudError):
        _client = crud.client.get_basket(dbsession, clients[0].id)


@pytest.mark.parametrize(
    "kwargs, offset, length",
    (
        ({}, 0, None),
        ({"limit": 2}, 0, 2),
        ({"skip": 2}, 2, None),
        ({"skip": 2, "limit": 2}, 2, 2),
    ),
)
def test_crud_get_multi(kwargs, offset, length, dbsession, init_clients):
    clients = init_clients

    obj_list = crud.client.get_multi(dbsession, **kwargs)

    skip = kwargs.get("skip", 0)
    length = length or len(clients) - skip
    assert len(obj_list) == length
    for i, obj in enumerate(obj_list):
        assert obj is clients[i + offset]


def test_crud_get_multi_error(dbsession, init_clients, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _clients = crud.client.get_multi(dbsession)


def test_crud_get_all(dbsession, init_clients):
    clients = crud.client.get_all(dbsession)

    for i, client in enumerate(clients):
        assert client is init_clients[i]


def test_crud_get_all_error(dbsession, init_clients, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _clients = crud.client.get_all(dbsession)


@pytest.mark.parametrize(
    "period, expected", ((Period(), 1), (Period(end=date(2022, 12, 31)), 0))
)
def test_crud_get_invoices(period, expected, dbsession, init_data):
    test_data = init_data

    invoices = crud.client.get_invoices(
        dbsession, test_data.clients[0].id, period=period
    )

    assert len(invoices) == expected
    if expected == 1:
        assert invoices[0] is test_data.clients[0].invoices[0]


def test_crud_get_invoices_unknown(dbsession, init_data):
    test_data = init_data
    ids = [c.id for c in test_data.clients]

    invoices = crud.client.get_invoices(dbsession, 100, period=Period())

    assert 100 not in ids
    assert len(invoices) == 0


def test_crud_get_invoice_error(dbsession, init_data, mock_select):
    state, _called = mock_select
    state["failed"] = True

    test_data = init_data

    with pytest.raises(crud.CrudError):
        _invoices = crud.client.get_invoices(
            dbsession, test_data.clients[0].id, period=Period()
        )


@pytest.mark.parametrize(
    "status, period, expected",
    (
        (models.InvoiceStatus.DRAFT, Period(), 1),
        (models.InvoiceStatus.DRAFT, Period(end=date(2022, 12, 31)), 0),
        (models.InvoiceStatus.PAID, Period(), 0),
        (models.InvoiceStatus.PAID, Period(end=date(2022, 12, 31)), 0),
    ),
)
def test_crud_get_invoices_by_status(status, period, expected, dbsession, init_data):
    test_data = init_data

    invoices = crud.client.get_invoices_by_status(
        dbsession, test_data.clients[0].id, status=status, period=period
    )

    assert len(invoices) == expected
    if expected == 1:
        assert invoices[0] is test_data.clients[0].invoices[0]


def test_crud_get_invoices_by_status_unknown(dbsession, init_data):
    test_data = init_data
    ids = [c.id for c in test_data.clients]

    invoices = crud.client.get_invoices_by_status(
        dbsession, 100, status=models.InvoiceStatus.DRAFT, period=Period()
    )

    assert 100 not in ids
    assert len(invoices) == 0


def test_crud_get_invoice_by_status_error(dbsession, init_data, mock_select):
    state, _called = mock_select
    state["failed"] = True

    test_data = init_data

    with pytest.raises(crud.CrudError):
        _invoices = crud.client.get_invoices_by_status(
            dbsession,
            test_data.clients[0].id,
            status=models.InvoiceStatus.DRAFT,
            period=Period(),
        )


@pytest.mark.parametrize("is_active, expected", ((False, False), (None, True)))
def test_crud_create(is_active, expected, dbsession, init_clients):
    address = schemas.Address(
        address="1 rue de l'église",
        zip_code="67890",
        city="La Bas",
    )
    client = crud.client.create(
        dbsession,
        obj_in=schemas.ClientCreate(
            name="Super client",
            address=address,
            email="super.client@domain.com",
            is_active=is_active,
        ),
    )

    assert client.id is not None
    assert client.name == "Super client"
    assert client.address == address.address
    assert client.zip_code == address.zip_code
    assert client.city == address.city
    assert client.email == "super.client@domain.com"
    assert client.is_active is expected
    try:
        c = dbsession.get(models.Client, client.id)
    except sa.exc.SQLAlchemyError:
        c = None
    assert c.name == "Super client"
    assert c.address == address.address
    assert c.zip_code == address.zip_code
    assert c.city == address.city
    assert c.email == "super.client@domain.com"
    assert c.is_active is expected


def test_crud_create_duplicate(dbsession, init_clients):
    address = schemas.Address(
        address="1 rue de l'église",
        zip_code="67890",
        city="La Bas",
    )
    with pytest.raises(crud.CrudError):
        _client = crud.client.create(
            dbsession,
            obj_in=schemas.ClientCreate(
                name="Client_1",
                address=address,
                email="super.client@domain.com",
                is_active=True,
            ),
        )
    assert (
        len(
            dbsession.scalars(
                sa.select(models.Client).where(models.Client.name == "Client_1")
            ).all()
        )
        == 1
    )


def test_crud_create_error(dbsession, init_clients, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    address = schemas.Address(
        address="1 rue de l'église",
        zip_code="67890",
        city="La Bas",
    )
    with pytest.raises(crud.CrudError):
        _client = crud.client.create(
            dbsession,
            obj_in=schemas.ClientCreate(
                name="Super client",
                address=address,
                email="super.client@domain.com",
                is_active=True,
            ),
        )
    assert (
        dbsession.scalars(
            sa.select(models.Client).where(models.Client.name == "Super client")
        ).first()
        is None
    )


def test_crud_update(dbsession, init_clients):
    client = init_clients[0]

    address = schemas.Address(
        address="1 rue de l'église",
        zip_code="67890",
        city="La Bas",
    )
    updated = crud.client.update(
        dbsession,
        db_obj=client,
        obj_in=schemas.ClientUpdate(
            name="Super client",
            address=address,
            email="super.client@domain.com",
            is_active=False,
        ),
    )

    assert updated.id == client.id
    assert updated.name == "Super client"
    assert updated.address == address.address
    assert updated.zip_code == address.zip_code
    assert updated.city == address.city
    assert updated.email == "super.client@domain.com"
    assert not updated.is_active
    try:
        c = dbsession.get(models.Client, updated.id)
    except sa.exc.SQLAlchemyError:
        c = None
    assert c.name == "Super client"
    assert c.address == address.address
    assert c.zip_code == address.zip_code
    assert c.city == address.city
    assert c.email == "super.client@domain.com"
    assert not c.is_active


def test_crud_update_partial(dbsession, init_clients):
    client = init_clients[0]

    address = schemas.Address(
        address=client.address,
        zip_code="67890",
        city=client.city,
    )
    updated = crud.client.update(
        dbsession, db_obj=client, obj_in=schemas.ClientUpdate(address=address)
    )

    assert updated.id == client.id
    assert updated.name == client.name
    assert updated.address == client.address
    assert updated.zip_code == address.zip_code
    assert updated.city == client.city
    assert updated.email == client.email
    assert not updated.is_active
    try:
        c = dbsession.get(models.Client, updated.id)
    except sa.exc.SQLAlchemyError:
        c = None
    assert c.name == client.name
    assert c.address == client.address
    assert c.zip_code == address.zip_code
    assert c.city == client.city
    assert c.email == client.email
    assert not c.is_active


def test_crud_update_idem(dbsession, init_clients, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    client = init_clients[0]

    address = schemas.Address(
        address=client.address,
        zip_code=client.zip_code,
        city=client.city,
    )
    updated = crud.client.update(
        dbsession, db_obj=client, obj_in=schemas.ClientUpdate(address=address)
    )

    assert updated == client
    assert len(called) == 0


def test_crud_update_error(dbsession, init_clients, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    client = init_clients[0]

    with pytest.raises(crud.CrudError):
        _updated = crud.client.update(
            dbsession,
            db_obj=client,
            obj_in=schemas.ClientUpdate(name="Wonderful client"),
        )

    assert (
        dbsession.scalars(
            sa.select(models.Client).where(models.Client.name == "Wonderful client")
        ).first()
        is None
    )


def test_crud_delete(dbsession, init_data):
    client = init_data.clients[0]
    assert dbsession.get(models.Client, client.id) is not None
    assert not client.has_emitted_invoices
    basket_items_ids = [item.id for item in client.basket.items]
    invoices_ids = [invoice.id for invoice in client.invoices]

    crud.client.delete(dbsession, db_obj=client)

    assert dbsession.get(models.Client, client.id) is None
    for id_ in basket_items_ids:
        assert dbsession.get(models.Item, id_) is None
    for id_ in invoices_ids:
        assert dbsession.get(models.Invoice, id_) is None


def test_crud_delete_has_emitted_invoices(dbsession, init_data):
    client = init_data.clients[1]
    assert dbsession.get(models.Client, client.id) is not None
    invoices_count = len(client.invoices)

    with pytest.raises(
        AssertionError, match="Cannot delete client with non-draft invoices"
    ):
        crud.client.delete(dbsession, db_obj=client)

    cl = dbsession.get(models.Client, client.id)
    assert cl is not None
    assert len(cl.invoices) == invoices_count


def test_crud_delete_error(dbsession, init_data, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    client = init_data.clients[0]
    assert dbsession.get(models.Client, client.id) is not None
    basket_items_count = len(client.basket.items)
    invoices_count = len(client.invoices)

    with pytest.raises(crud.CrudError):
        crud.client.delete(dbsession, db_obj=client)

    cl = dbsession.get(models.Client, client.id)
    assert cl is not None
    assert len(cl.invoices) == invoices_count
    assert len(cl.basket.items) == basket_items_count


def test_crud_add_to_basket(dbsession, init_clients, init_services):
    client = init_clients[0]
    service = init_services[0]

    item = crud.client.add_to_basket(
        dbsession, basket=client.basket, service=service, quantity=2
    )

    assert item.service_id == service.id
    assert item.service_version == service.version
    assert item.quantity == 2
    assert item.basket_id == client.basket.id
    assert len(client.basket.items) == 1
    assert client.basket.items[0] == item


def test_crud_add_to_basket_default_qty(dbsession, init_clients, init_services):
    client = init_clients[0]
    service = init_services[0]

    item = crud.client.add_to_basket(dbsession, basket=client.basket, service=service)

    assert item.service_id == service.id
    assert item.service_version == service.version
    assert item.quantity == 1
    assert item.basket_id == client.basket.id
    assert len(client.basket.items) == 1
    assert client.basket.items[0] == item


def test_crud_add_to_basket_commit_error(
    dbsession, init_clients, init_services, mock_commit
):
    state, _called = mock_commit
    state["failed"] = True

    client = init_clients[0]
    service = init_services[0]

    with pytest.raises(crud.CrudError):
        _item = crud.client.add_to_basket(
            dbsession, basket=client.basket, service=service, quantity=2
        )

    assert len(client.basket.items) == 0


def test_crud_update_item_quantity(dbsession, init_data):
    client = init_data.clients[0]
    basket = client.basket
    item = basket.items[0]
    invoice = client.invoices[0]
    item.invoice_id = invoice.id
    quantity = 2

    crud.client.update_item_quantity(dbsession, item=item, quantity=quantity)

    assert item.quantity == quantity


def test_crud_update_item_quantity_commit_error(dbsession, init_items, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    item = init_items[0]
    assert item.quantity == 1

    with pytest.raises(crud.CrudError):
        crud.client.update_item_quantity(dbsession, item=item, quantity=2)

    assert item.quantity == 1


def test_crud_remove_item_in_basket_only(dbsession, init_data):
    client = init_data.clients[0]
    basket = client.basket
    items_count = len(basket.items)
    item = basket.items[0]
    assert item not in client.invoices
    item_id = item.id

    crud.client.remove_item(dbsession, item=item)

    assert (
        dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id)
        ).first()
        is None
    )

    assert len(basket.items) == items_count - 1


def test_crud_remove_item_in_invoice_only(dbsession, init_data):
    client = init_data.clients[0]
    invoice = client.invoices[0]
    items_count = len(invoice.items)
    item = invoice.items[0]
    assert item not in client.basket.items
    item_id = item.id

    crud.client.remove_item(dbsession, item=item)

    assert (
        dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id)
        ).first()
        is None
    )

    assert len(invoice.items) == items_count - 1


def test_crud_remove_item_commit_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[0]
    basket = client.basket
    items_count = len(basket.items)
    item = basket.items[0]
    assert item not in client.invoices
    item_id = item.id

    with pytest.raises(crud.CrudError):
        crud.client.remove_item(dbsession, item=item)

    it = dbsession.scalars(
        sa.select(models.Item).where(models.Item.id == item_id)
    ).first()
    assert it == item

    assert len(basket.items) == items_count
    assert it == item


def test_crud_clear_basket_no_invoice(dbsession, init_items):
    item1 = init_items[0]
    item_id1 = item1.id
    basket = item1.basket
    item2 = init_items[5]
    item_id2 = item2.id
    assert basket == item2.basket

    crud.client.clear_basket(dbsession, basket=basket)

    assert (
        dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id1)
        ).first()
        is None
    )
    assert (
        dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id2)
        ).first()
        is None
    )

    assert len(basket.items) == 0


def test_crud_clear_basket_in_invoice(dbsession, init_data):
    client = init_data.clients[0]
    basket = client.basket
    item_ids = [item.id for item in basket.items]
    invoice = client.invoices[0]
    basket.items[0].invoice_id = invoice.id
    item_in_invoice = basket.items[0]

    crud.client.clear_basket(dbsession, basket=basket)

    it1 = dbsession.scalars(
        sa.select(models.Item).where(models.Item.id == item_ids[0])
    ).first()
    assert it1 == item_in_invoice

    assert len(basket.items) == 0


def test_crud_clear_basket_commit_error(dbsession, init_items, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    item1 = init_items[0]
    item_id1 = item1.id
    basket = item1.basket
    item2 = init_items[5]
    item_id2 = item2.id
    assert basket == item2.basket

    with pytest.raises(crud.CrudError):
        crud.client.clear_basket(dbsession, basket=basket)

    it1 = dbsession.scalars(
        sa.select(models.Item).where(models.Item.id == item_id1)
    ).first()
    assert it1 == item1
    it2 = dbsession.scalars(
        sa.select(models.Item).where(models.Item.id == item_id2)
    ).first()
    assert it2 == item2

    assert len(basket.items) == 2


def test_client_from_orm(dbsession, init_clients):
    client = init_clients[0]

    from_db = schemas.Client.from_orm(client)

    assert from_db.id == client.id
    assert from_db.name == client.name
    assert from_db.address == schemas.Address(
        client.address, client.zip_code, client.city
    )
    assert from_db.is_active is client.is_active
    assert from_db.code == f"CL{str(from_db.id).zfill(5)}"


def test_basket_from_orm(dbsession, init_data):
    basket = init_data.clients[0].basket

    from_db = schemas.Basket.from_orm(basket)

    assert from_db.id == basket.id
    for i, item in enumerate(from_db.items):
        assert item == schemas.Item.from_orm(basket.items[i])


def test_item_from_orm(dbsession, init_data):
    item = init_data.items[0]

    from_db = schemas.Item.from_orm(item)

    assert from_db.id == item.id
    assert from_db.service_id == item.service_id
    assert from_db.quantity == item.quantity
    assert from_db.service == schemas.Service.from_orm(item.service)
