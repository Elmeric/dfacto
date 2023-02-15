# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import cast

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models import db, crud, models, schemas

pytestmark = pytest.mark.crud


@pytest.fixture
def init_clients(dbsession: sa.orm.scoped_session) -> list[models.Client]:
    db.init_db_data(dbsession)

    for i in range(5):
        client = models.Client(
            name=f"Client_{i + 1}",
            address=f"{i * 1} rue Nationale {i + 1}",
            zip_code=f"1234{i + 1}",
            city=f"CITY_{i + 1}",
        )
        dbsession.add(client)
        dbsession.commit()

    clients = cast(
        list[models.Client],
        dbsession.scalars(sa.select(models.Client)).all()
    )
    return clients


def test_crud_init():
    assert crud.client.model is models.Client


def test_crud_get(dbsession, init_clients):
    clients = init_clients

    client = crud.client.get(dbsession, id_=clients[0].id)

    assert client is clients[0]


def test_crud_get_unknown(dbsession, init_clients):
    clients = init_clients
    ids = [c.id for c in clients]

    client = crud.client.get(dbsession, id_=100)

    assert 100 not in ids
    assert client is None


def test_crud_get_error(dbsession, init_clients, mock_get):
    state, _called = mock_get
    state["failed"] = True

    clients = init_clients

    with pytest.raises(crud.CrudError):
        _client = crud.client.get(dbsession, id_=clients[0].id)


def test_crud_get_basket(dbsession, init_clients):
    clients = init_clients

    basket = crud.client.get_basket(dbsession, id_=clients[0].id)

    assert basket is clients[0].basket
    assert basket.raw_amount == 0.0
    assert basket.vat == 0.0
    assert basket.net_amount == 0.0
    assert basket.client_id == clients[0].id
    assert len(basket.items) == 0


def test_crud_get_basket_unknown(dbsession, init_clients):
    clients = init_clients
    ids = [c.id for c in clients]

    basket = crud.client.get_basket(dbsession, id_=100)

    assert 100 not in ids
    assert basket is None


@pytest.mark.parametrize(
    "kwargs, offset, length",
    (
        ({}, 0, None),
        ({"limit": 2}, 0, 2),
        ({"skip": 2}, 2, None),
        ({"skip": 2, "limit": 2}, 2, 2)
    )
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
        _clients = crud.vat_rate.get_multi(dbsession)


def test_crud_get_all(dbsession, init_clients):
    clients = crud.client.get_all(dbsession)

    for i, client in enumerate(clients):
        assert client is init_clients[i]


def test_crud_get_all_error(dbsession, init_clients, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _clients = crud.client.get_all(dbsession)


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
            is_active=is_active
        )
    )

    assert client.id is not None
    assert client.name == "Super client"
    assert client.address == address.address
    assert client.zip_code == address.zip_code
    assert client.city == address.city
    assert client.is_active is expected
    try:
        c = dbsession.get(models.Client, client.id)
    except sa.exc.SQLAlchemyError:
        c = None
    assert c.name == "Super client"
    assert c.address == address.address
    assert c.zip_code == address.zip_code
    assert c.city == address.city
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
                is_active=True
            )
        )
    assert len(
        dbsession.scalars(
            sa.select(models.Client).where(models.Client.name == "Client_1")
        ).all()
    ) == 1


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
                is_active=True
            )
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
            is_active=False
        )
    )

    assert updated.id == client.id
    assert updated.name == "Super client"
    assert updated.address == address.address
    assert updated.zip_code == address.zip_code
    assert updated.city == address.city
    assert not updated.is_active
    try:
        c = dbsession.get(models.Client, updated.id)
    except sa.exc.SQLAlchemyError:
        c = None
    assert c.name == "Super client"
    assert c.address == address.address
    assert c.zip_code == address.zip_code
    assert c.city == address.city
    assert not c.is_active


def test_crud_update_partial(dbsession, init_clients):
    client = init_clients[0]

    address = schemas.Address(
        address=client.address,
        zip_code="67890",
        city=client.city,
    )
    updated = crud.client.update(
        dbsession,
        db_obj=client,
        obj_in=schemas.ClientUpdate(address=address)
    )

    assert updated.id == client.id
    assert updated.name == client.name
    assert updated.address == client.address
    assert updated.zip_code == address.zip_code
    assert updated.city == client.city
    assert updated.is_active
    try:
        c = dbsession.get(models.Client, updated.id)
    except sa.exc.SQLAlchemyError:
        c = None
    assert c.name == client.name
    assert c.address == client.address
    assert c.zip_code == address.zip_code
    assert c.city == client.city
    assert c.is_active


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
        dbsession,
        db_obj=client,
        obj_in=schemas.ClientUpdate(address=address)
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
            obj_in=schemas.ClientUpdate(name="Wonderful client")
        )

    assert (
        dbsession.scalars(
            sa.select(models.Client).where(models.Client.name == "Wonderful client")
        ).first()
        is None
    )


def test_crud_delete(dbsession, init_clients):
    client = init_clients[0]
    assert dbsession.get(models.Client, client.id) is not None

    crud.client.delete(dbsession, db_obj=client)

    assert dbsession.get(models.Client, client.id) is None


def test_crud_delete_error(dbsession, init_clients, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    client = init_clients[0]
    assert dbsession.get(models.Client, client.id) is not None

    with pytest.raises(crud.CrudError):
        crud.client.delete(dbsession, db_obj=client)

    assert dbsession.get(models.Client, client.id) is not None


def test_schema_from_orm(dbsession, init_clients):
    client = init_clients[0]

    from_db = schemas.Client.from_orm(client)

    assert from_db.id == client.id
    assert from_db.name == client.name
    assert from_db.address == schemas.Address(client.address, client.zip_code, client.city)
    assert from_db.is_active is client.is_active
    assert from_db.code == f"CL{str(from_db.id).zfill(5)}"
