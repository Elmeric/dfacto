# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# Cf. https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2

import dataclasses
import sys
from datetime import datetime, timedelta
from sqlite3 import Connection as SQLite3Connection
from typing import Any, Optional, Union, cast

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.event import listen
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from dfacto.backend import crud, models, schemas
from dfacto.backend.db.session import init_db_data
from dfacto.backend.models.base_model import BaseModel


def _set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# https://github.com/sqlalchemy/sqlalchemy/issues/7716
# https://docs.sqlalchemy.org/en/14/dialects/sqlite.html#pysqlite-serializable
# @event.listens_for(engine, "connect")
def do_connect(dbapi_connection, connection_record):
    # disable pysqlite's emitting of the BEGIN statement entirely.
    # also stops it from emitting COMMIT before any DDL.
    dbapi_connection.isolation_level = None


# @event.listens_for(engine, "begin")
def do_begin(conn):
    # emit our own BEGIN
    conn.exec_driver_sql("BEGIN")


@pytest.fixture(scope="session")
def engine():
    # engine = create_engine(
    #     r"sqlite+pysqlite:///F:\Users\Documents\Python\dfacto_test.db"
    # )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    listen(engine, "connect", _set_sqlite_pragma)
    listen(engine, "connect", do_connect)
    listen(engine, "begin", do_begin)
    return engine


@pytest.fixture(scope="session")
def tables(engine):
    BaseModel.metadata.create_all(engine)
    yield
    BaseModel.metadata.drop_all(engine)


@pytest.fixture
def dbsession(engine, tables):
    """Returns a sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    # session = Session(bind=connection, join_transaction_mode="create_savepoint")
    session_factory = sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    session = session_factory()

    yield session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()


#
# Mock some methods of the sqlalchemy 'scoped_session'
#
@pytest.fixture()
def mock_commit(monkeypatch):
    state = {"failed": False}
    called = []

    def _commit(_):
        called.append(True)
        if state["failed"]:
            raise SQLAlchemyError("Commit failed")

    monkeypatch.setattr("dfacto.backend.crud.base.Session.commit", _commit)

    return state, called


@pytest.fixture()
def mock_get(monkeypatch):
    state = {"failed": False}
    called = []

    def _get(_1, _2, _3, **kwargs):
        called.append(True)
        if state["failed"]:
            raise SQLAlchemyError("Get failed")

    monkeypatch.setattr("dfacto.backend.crud.base.Session.get", _get)

    return state, called


@pytest.fixture()
def mock_select(monkeypatch):
    state = {"failed": False}
    called = []

    def _select(_):
        called.append(True)
        if state["failed"]:
            raise SQLAlchemyError("Select failed")

    monkeypatch.setattr("dfacto.backend.crud.base.select", _select)
    monkeypatch.setattr(sys.modules["dfacto.backend.crud.client"], "select", _select)

    return state, called


FAKE_TIME = datetime(2023, 2, 22, 21, 54, 30)


@pytest.fixture
def mock_datetime_now(monkeypatch):
    class mydatetime:
        @classmethod
        def now(cls):
            return FAKE_TIME

    monkeypatch.setattr(
        sys.modules["dfacto.backend.crud.invoice"], "datetime", mydatetime
    )


@pytest.fixture()
def mock_schema_from_orm(monkeypatch):
    def _from_orm(obj):
        return obj

    monkeypatch.setattr(schemas.VatRate, "from_orm", _from_orm)
    monkeypatch.setattr(schemas.Service, "from_orm", _from_orm)
    monkeypatch.setattr(schemas.Client, "from_orm", _from_orm)
    monkeypatch.setattr(schemas.Basket, "from_orm", _from_orm)
    monkeypatch.setattr(schemas.Item, "from_orm", _from_orm)
    monkeypatch.setattr(schemas.Invoice, "from_orm", _from_orm)


#
# Mock some methods of the CRUDBase class used by all DFactoModel command API
#
@pytest.fixture()
def mock_dfacto_model(monkeypatch):
    state = {"raises": {}, "read_value": None}
    methods_called = []

    def _get(_, _db, _id):
        methods_called.append("GET")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _get_multi(_, _db, *, skip: int = 0, limit: int = 100):
        methods_called.append("GET_MULTI")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"][skip : skip + limit]

    def _get_all(_, _db):
        methods_called.append("GET_ALL")
        exc = state["raises"]["READ"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return state["read_value"]

    def _create(_, _db, *, obj_in: schemas.ServiceCreate):
        methods_called.append("CREATE")
        exc = state["raises"]["CREATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            obj_in.id = 1
            return obj_in

    def _update(
        _, _db, *, db_obj, obj_in: Union[schemas.ServiceUpdate, dict[str, Any]]
    ):
        methods_called.append("UPDATE")
        exc = state["raises"]["UPDATE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            obj_data = dataclasses.asdict(db_obj)
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.flatten()
                # update_data = dataclasses.asdict(obj_in)
            for field in obj_data:
                if (
                    field in update_data
                    and update_data[field] is not None
                    and getattr(db_obj, field) != update_data[field]
                ):
                    setattr(db_obj, field, update_data[field])
            return db_obj

    def _delete(_, db: Session, *, db_obj: dict[str, Any]) -> None:
        methods_called.append("DELETE")
        exc = state["raises"]["DELETE"]
        if exc is crud.CrudError or exc is crud.CrudIntegrityError:
            raise exc
        elif exc:
            raise crud.CrudError
        else:
            return

    monkeypatch.setattr(crud.base.CRUDBase, "get", _get)
    monkeypatch.setattr(crud.base.CRUDBase, "get_multi", _get_multi)
    monkeypatch.setattr(crud.base.CRUDBase, "get_all", _get_all)
    monkeypatch.setattr(crud.base.CRUDBase, "create", _create)
    monkeypatch.setattr(crud.base.CRUDBase, "update", _update)
    monkeypatch.setattr(crud.base.CRUDBase, "delete", _delete)

    return state, methods_called


@dataclasses.dataclass
class TestData:
    vat_rates: list[models.VatRate]
    services: list[models.Service]
    clients: list[models.Client]
    items: list[models.Item]
    invoices: list[models.Invoice]


# class PresetRate(TypedDict):
#     name: str
#     rate: float
#     is_default: bool
#     is_preset: bool
#
#
# PRESET_RATES: list[PresetRate] = [
#     {"name": "taux zéro", "rate": 0.0, "is_default": True, "is_preset": True},
#     {"name": "taux particulier", "rate": 2.1, "is_default": False, "is_preset": True},
#     {"name": "taux réduit", "rate": 5.5, "is_default": False, "is_preset": True},
#     {"name": "taux intermédiaire", "rate": 10, "is_default": False, "is_preset": True},
#     {"name": "taux normal", "rate": 20, "is_default": False, "is_preset": True},
# ]
#
#
# def init_db_data(session: Session) -> None:
#     if session.scalars(select(models.VatRate)).first() is None:
#         # No VAT rates in the database: add the presets and mark "taux zéro" as default.
#         session.execute(insert(models.VatRate), PRESET_RATES)
#         session.commit()


@pytest.fixture
def init_data(dbsession: Session) -> TestData:
    # VAT rates (5 preset rates, 3 custom rates)
    init_db_data(dbsession)
    for i in range(3):
        vat_rate = models.VatRate(
            name=f"Rate {i + 1}", rate=12.5 + 2.5 * i  # Rate_1 to _3  # 12.5, 15, 17.5
        )
        dbsession.add(vat_rate)
    dbsession.commit()
    vat_rates = cast(
        list[models.VatRate], dbsession.scalars(select(models.VatRate)).all()
    )
    # Services
    for i in range(5):
        service = models.Service(
            name=f"Service_{i + 1}",  # Service_1 to _5
            unit_price=100 + 10 * i,  # 100, 110, 120, 130, 140
            vat_rate_id=i + 1,  # 1 to 5 (rates: 0, 2.1, 5.5, 10, 20)
        )
        dbsession.add(service)
    dbsession.commit()
    services = cast(
        list[models.Service], dbsession.scalars(select(models.Service)).all()
    )
    # Clients
    for i in range(5):
        client = models.Client(
            name=f"Client_{i + 1}",  # Client_1 to _5
            address=f"Address_{i + 1}",  # Address_1 to _5
            zip_code=f"1234{i + 1}",  # 12341 to 12345
            city=f"CITY_{i + 1}",  # CITY_1 to _5
            email=f"client_{i + 1}@domain.com",
        )
        dbsession.add(client)
    dbsession.commit()
    clients = cast(list[models.Client], dbsession.scalars(select(models.Client)).all())
    # Invoices (empty)
    for i in range(5):
        invoice = models.Invoice(
            client_id=clients[i % 5].id, status=models.InvoiceStatus(i + 1)
        )
        dbsession.add(invoice)
        dbsession.flush([invoice])
        for j in range(i):
            prev_log = models.StatusLog(
                invoice_id=invoice.id,
                from_=datetime.now() - timedelta(days=10 * (i - j - 2)),
                to=datetime.now() - timedelta(days=10 * (i - j - 1)),
                status=models.InvoiceStatus(j + 1),
            )
            dbsession.add(prev_log)
        log = models.StatusLog(
            invoice_id=invoice.id,
            from_=datetime.now(),
            to=None,
            status=models.InvoiceStatus(i + 1),
        )
        dbsession.add(log)
    dbsession.commit()
    invoices = cast(
        list[models.Invoice], dbsession.scalars(select(models.Invoice)).all()
    )
    # Items
    for i in range(20):
        service = services[i % 5]
        quantity = i + 1
        raw_amount = service.unit_price * quantity
        vat = raw_amount * service.vat_rate.rate / 100
        item = models.Item(
            raw_amount=raw_amount,
            vat=vat,
            service_id=service.id,
            quantity=quantity,
        )
        if i < 10:
            basket = clients[i % 5].basket
            item.basket_id = basket.id
            dbsession.add(item)
            basket.raw_amount += raw_amount
            basket.vat += vat
        else:
            invoice = invoices[i % 5]
            item.invoice_id = invoice.id
            dbsession.add(item)
            invoice.raw_amount += raw_amount
            invoice.vat += vat
    dbsession.commit()
    items = cast(list[models.Item], dbsession.scalars(select(models.Item)).all())

    return TestData(
        vat_rates=vat_rates,
        services=services,
        clients=clients,
        items=items,
        invoices=invoices,
    )


@dataclasses.dataclass
class FakeORMModel:
    id: int


@dataclasses.dataclass
class FakeORMClient(FakeORMModel):
    name: str
    address: str
    zip_code: str
    city: str
    email: str
    is_active: bool = True
    basket: "FakeORMBasket" = None
    # invoices: list["FakeORMInvoice"] = dataclasses.field(default_factory=list)
    invoices: list[str] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.basket is None:
            self.basket = FakeORMBasket(
                id=1,
                raw_amount=0.0,
                vat=0.0,
                client_id=self.id,
                items=[],
            )

    @property
    def has_emitted_invoices(self):
        return any(invoice != "DRAFT" for invoice in self.invoices)


@dataclasses.dataclass
class FakeORMBasket(FakeORMModel):
    raw_amount: float
    vat: float
    client_id: int
    items: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class FakeORMInvoice(FakeORMModel):
    client_id: int = 1
    raw_amount: float = 0.0
    vat: float = 0.0
    status: models.InvoiceStatus = models.InvoiceStatus.DRAFT


@dataclasses.dataclass
class FakeORMItem(FakeORMModel):
    raw_amount: float
    vat: float
    service_id: int
    quantity: int = 1
    service: "FakeORMService" = None
    basket_id: Optional[int] = 1
    invoice_id: Optional[int] = None
    basket: "FakeORMBasket" = None
    invoice: "FakeORMInvoice" = None


@dataclasses.dataclass
class FakeORMService(FakeORMModel):
    unit_price: float
    name: str = "Service"
    vat_rate_id: int = 1
    vat_rate: "FakeORMVatRate" = None


@dataclasses.dataclass
class FakeORMVatRate(FakeORMModel):
    rate: float
    name: str = "Rate"
    is_default: bool = False
    is_preset: bool = False
    services: list["FakeORMService"] = dataclasses.field(default_factory=list)
