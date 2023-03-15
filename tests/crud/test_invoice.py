# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

from dfacto.backend import crud, models, schemas
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
        ({"skip": 2, "limit": 2}, 2, 2),
    ),
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

    invoice = crud.invoice.create(obj_in=)

    assert invoice.id is not None
    assert invoice.client_id == client.id
    assert invoice.raw_amount == 0.0
    assert invoice.vat == 0.0
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
        _invoice = crud.invoice.create(obj_in=)
    assert len(client.invoices) == initial_invoices_count
    assert (
        len(
            (
                dbsession.scalars(
                    sa.select(models.Invoice).where(
                        models.Invoice.client_id == client.id
                    )
                ).all()
            )
        )
        == initial_invoices_count
    )
    assert (
        len(dbsession.scalars(sa.select(models.StatusLog)).all()) == initial_log_count
    )


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
    assert (
        len(
            (
                dbsession.scalars(
                    sa.select(models.Invoice).where(
                        models.Invoice.client_id == client.id
                    )
                ).all()
            )
        )
        == initial_invoices_count
    )
    assert (
        len(dbsession.scalars(sa.select(models.StatusLog)).all()) == initial_log_count
    )


def test_crud_add_item(dbsession, init_data):
    client = init_data.clients[0]
    invoice = client.invoices[0]
    assert invoice.status is models.InvoiceStatus.DRAFT
    items_count = len(invoice.items)
    raw_amount = invoice.raw_amount
    vat = invoice.vat
    service = init_data.services[1]

    item = crud.invoice.add_item(
        dbsession, invoice_=invoice, service=service, quantity=2
    )

    assert item.service_id == service.id
    assert item.quantity == 2
    assert item.raw_amount == service.unit_price * 2
    assert item.vat == service.vat_rate.rate * service.unit_price * 2 / 100
    assert item.invoice_id == invoice.id
    assert len(invoice.items) == items_count + 1
    assert invoice.items[items_count] == item
    assert invoice.raw_amount == raw_amount + item.raw_amount
    assert invoice.vat == vat + item.vat


def test_crud_add_item_default_qty(dbsession, init_data):
    client = init_data.clients[0]
    invoice = client.invoices[0]
    assert invoice.status is models.InvoiceStatus.DRAFT
    items_count = len(invoice.items)
    raw_amount = invoice.raw_amount
    vat = invoice.vat
    service = init_data.services[1]

    item = crud.invoice.add_item(dbsession, invoice_=invoice, service=service)

    assert item.service_id == service.id
    assert item.quantity == 1
    assert item.raw_amount == service.unit_price
    assert item.vat == service.vat_rate.rate * service.unit_price / 100
    assert item.invoice_id == invoice.id
    assert len(invoice.items) == items_count + 1
    assert invoice.items[items_count] == item
    assert invoice.raw_amount == raw_amount + item.raw_amount
    assert invoice.vat == vat + item.vat


def test_crud_add_item_non_draft(dbsession, init_data):
    client = init_data.clients[1]
    invoice = client.invoices[0]
    assert invoice.status is not models.InvoiceStatus.DRAFT
    items_count = len(invoice.items)
    raw_amount = invoice.raw_amount
    vat = invoice.vat
    service = init_data.services[1]

    with pytest.raises(AssertionError):
        _item = crud.invoice.add_item(
            dbsession, invoice_=invoice, service=service, quantity=2
        )

    assert len(invoice.items) == items_count
    assert invoice.raw_amount == raw_amount
    assert invoice.vat == vat


def test_crud_add_item_commit_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[0]
    invoice = client.invoices[0]
    assert invoice.status is models.InvoiceStatus.DRAFT
    items_count = len(invoice.items)
    raw_amount = invoice.raw_amount
    vat = invoice.vat
    service = init_data.services[1]

    with pytest.raises(crud.CrudError):
        _item = crud.invoice.add_item(
            dbsession, invoice_=invoice, service=service, quantity=2
        )

    assert len(invoice.items) == items_count
    assert invoice.raw_amount == raw_amount
    assert invoice.vat == vat


def test_crud_clear_invoice_no_basket(dbsession, init_data):
    client = init_data.clients[0]
    invoice = client.invoices[0]
    assert invoice.status is models.InvoiceStatus.DRAFT
    item_ids = [item.id for item in invoice.items]
    assert all([item not in client.basket.items for item in invoice.items])

    crud.invoice.clear_invoice(dbsession, invoice_=invoice)

    for item_id in item_ids:
        assert (
            dbsession.scalars(
                sa.select(models.Item).where(models.Item.id == item_id)
            ).first()
            is None
        )

    assert len(invoice.items) == 0
    assert invoice.raw_amount == 0.0
    assert invoice.vat == 0.0


def test_crud_clear_invoice_in_basket(dbsession, init_data):
    client = init_data.clients[0]
    invoice = client.invoices[0]
    assert invoice.status is models.InvoiceStatus.DRAFT
    item_ids = [item.id for item in invoice.items]
    invoice.items[0].basket_id = client.basket.id
    item_in_basket = invoice.items[0]

    crud.invoice.clear_invoice(dbsession, invoice_=invoice)

    it1 = dbsession.scalars(
        sa.select(models.Item).where(models.Item.id == item_ids[0])
    ).first()
    assert it1 == item_in_basket

    assert len(invoice.items) == 0
    assert invoice.raw_amount == 0.0
    assert invoice.vat == 0.0


def test_crud_clear_invoice_non_draft(dbsession, init_data):
    client = init_data.clients[1]
    invoice = client.invoices[0]
    assert invoice.status is not models.InvoiceStatus.DRAFT
    items = [(item.id, item) for item in invoice.items]
    items_count = len(invoice.items)
    expected_raw_amount = invoice.raw_amount
    expected_vat = invoice.vat

    with pytest.raises(AssertionError):
        crud.invoice.clear_invoice(dbsession, invoice_=invoice)

    for item_id, item in items:
        it = dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id)
        ).first()
        assert it == item

    assert len(invoice.items) == items_count
    assert invoice.raw_amount == expected_raw_amount
    assert invoice.vat == expected_vat


def test_crud_clear_invoice_commit_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[0]
    invoice = client.invoices[0]
    assert invoice.status is models.InvoiceStatus.DRAFT
    items = [(item.id, item) for item in invoice.items]
    items_count = len(invoice.items)
    expected_raw_amount = invoice.raw_amount
    expected_vat = invoice.vat

    with pytest.raises(crud.CrudError):
        crud.invoice.clear_invoice(dbsession, invoice_=invoice)

    for item_id, item in items:
        it = dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id)
        ).first()
        assert it == item

    assert len(invoice.items) == items_count
    assert invoice.raw_amount == expected_raw_amount
    assert invoice.vat == expected_vat


def test_crud_delete_invoice_no_basket(dbsession, init_data):
    client = init_data.clients[0]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is models.InvoiceStatus.DRAFT
    item_ids = [item.id for item in invoice.items]
    assert len(item_ids) > 0
    log_ids = [log.id for log in invoice.status_log]
    assert len(log_ids) > 0
    assert all([item not in client.basket.items for item in invoice.items])

    crud.invoice.delete_invoice(dbsession, invoice_=invoice)

    assert (
        dbsession.scalars(
            sa.select(models.Invoice).where(models.Invoice.id == invoice_id)
        ).first()
        is None
    )
    for item_id in item_ids:
        assert (
            dbsession.scalars(
                sa.select(models.Item).where(models.Item.id == item_id)
            ).first()
            is None
        )
    for log_id in log_ids:
        assert (
            dbsession.scalars(
                sa.select(models.StatusLog).where(models.StatusLog.id == log_id)
            ).first()
            is None
        )


def test_crud_delete_invoice_in_basket(dbsession, init_data):
    client = init_data.clients[0]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is models.InvoiceStatus.DRAFT
    item_ids = [item.id for item in invoice.items]
    assert len(item_ids) > 1
    log_ids = [log.id for log in invoice.status_log]
    assert len(log_ids) > 0
    invoice.items[0].basket_id = client.basket.id
    item_in_basket = invoice.items[0]

    crud.invoice.delete_invoice(dbsession, invoice_=invoice)

    assert (
        dbsession.scalars(
            sa.select(models.Invoice).where(models.Invoice.id == invoice_id)
        ).first()
        is None
    )

    assert (
        dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_ids[0])
        ).first()
        == item_in_basket
    )
    for item_id in item_ids[1:]:
        assert (
            dbsession.scalars(
                sa.select(models.Item).where(models.Item.id == item_id)
            ).first()
            is None
        )
    for log_id in log_ids:
        assert (
            dbsession.scalars(
                sa.select(models.StatusLog).where(models.StatusLog.id == log_id)
            ).first()
            is None
        )


def test_crud_delete_invoice_non_draft(dbsession, init_data):
    client = init_data.clients[1]
    invoice = client.invoices[0]
    assert invoice.status is not models.InvoiceStatus.DRAFT
    items = [(item.id, item) for item in invoice.items]
    items_count = len(invoice.items)
    assert items_count > 0
    logs = [(log.id, log) for log in invoice.status_log]
    logs_count = len(invoice.status_log)
    assert logs_count > 0
    expected_raw_amount = invoice.raw_amount
    expected_vat = invoice.vat

    with pytest.raises(AssertionError):
        crud.invoice.delete_invoice(dbsession, invoice_=invoice)

    for item_id, item in items:
        it = dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id)
        ).first()
        assert it == item
    for log_id, log in logs:
        lg = dbsession.scalars(
            sa.select(models.StatusLog).where(models.StatusLog.id == log_id)
        ).first()
        assert lg == log
    assert len(invoice.items) == items_count
    assert len(invoice.status_log) == logs_count
    assert invoice.raw_amount == expected_raw_amount
    assert invoice.vat == expected_vat


def test_crud_delete_invoice_commit_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[0]
    invoice = client.invoices[0]
    assert invoice.status is models.InvoiceStatus.DRAFT
    items = [(item.id, item) for item in invoice.items]
    items_count = len(invoice.items)
    assert items_count > 0
    logs = [(log.id, log) for log in invoice.status_log]
    logs_count = len(invoice.status_log)
    assert logs_count > 0
    expected_raw_amount = invoice.raw_amount
    expected_vat = invoice.vat

    with pytest.raises(crud.CrudError):
        crud.invoice.delete_invoice(dbsession, invoice_=invoice)

    for item_id, item in items:
        it = dbsession.scalars(
            sa.select(models.Item).where(models.Item.id == item_id)
        ).first()
        assert it == item
    for log_id, log in logs:
        lg = dbsession.scalars(
            sa.select(models.StatusLog).where(models.StatusLog.id == log_id)
        ).first()
        assert lg == log
    assert len(invoice.items) == items_count
    assert len(invoice.status_log) == logs_count
    assert invoice.raw_amount == expected_raw_amount
    assert invoice.vat == expected_vat


def test_crud_cancel_invoice(dbsession, init_data, mock_datetime_now):
    client = init_data.clients[1]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is models.InvoiceStatus.EMITTED
    assert len(invoice.status_log) == 2
    last_log = invoice.status_log[1]
    assert last_log.to is None

    crud.invoice.cancel_invoice(dbsession, invoice_=invoice)

    assert invoice.status is models.InvoiceStatus.CANCELLED
    status_log = dbsession.scalars(
        sa.select(models.StatusLog).where(models.StatusLog.invoice_id == invoice_id)
    ).all()
    assert status_log[1] is last_log
    assert status_log[1].to == FAKE_TIME
    assert status_log[2].status is models.InvoiceStatus.CANCELLED
    assert status_log[2].from_ == FAKE_TIME
    assert status_log[2].to is None


def test_crud_cancel_invoice_bad_status(dbsession, init_data):
    client = init_data.clients[3]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is models.InvoiceStatus.PAID
    logs_count = len(invoice.status_log)
    last_log = invoice.status_log[logs_count - 1]
    assert last_log.to is None

    with pytest.raises(AssertionError):
        crud.invoice.cancel_invoice(dbsession, invoice_=invoice)

    assert invoice.status is models.InvoiceStatus.PAID
    status_log = dbsession.scalars(
        sa.select(models.StatusLog).where(models.StatusLog.invoice_id == invoice_id)
    ).all()
    assert len(status_log) == logs_count
    assert status_log[logs_count - 1] is last_log
    assert status_log[logs_count - 1].to is None
    assert status_log[logs_count - 1].status is models.InvoiceStatus.PAID


def test_crud_cancel_invoice_commit_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[1]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is models.InvoiceStatus.EMITTED
    logs_count = len(invoice.status_log)
    last_log = invoice.status_log[logs_count - 1]
    assert last_log.to is None

    with pytest.raises(crud.CrudError):
        crud.invoice.cancel_invoice(dbsession, invoice_=invoice)

    assert invoice.status is models.InvoiceStatus.EMITTED
    status_log = dbsession.scalars(
        sa.select(models.StatusLog).where(models.StatusLog.invoice_id == invoice_id)
    ).all()
    assert len(status_log) == logs_count
    assert status_log[logs_count - 1] is last_log
    assert status_log[logs_count - 1].to is None
    assert status_log[logs_count - 1].status is models.InvoiceStatus.EMITTED


@pytest.mark.parametrize(
    "status, client_idx, prev_status",
    (
        (models.InvoiceStatus.EMITTED, 0, models.InvoiceStatus.DRAFT),  # from DRAFT
        (
            models.InvoiceStatus.REMINDED,
            1,
            models.InvoiceStatus.EMITTED,
        ),  # from EMITTED
        (models.InvoiceStatus.PAID, 1, models.InvoiceStatus.EMITTED),  # from EMITTED
        (
            models.InvoiceStatus.CANCELLED,
            2,
            models.InvoiceStatus.REMINDED,
        ),  # from REMINDED
    ),
)
def test_crud_mark_as(
    status, client_idx, prev_status, dbsession, init_data, mock_datetime_now
):
    client = init_data.clients[client_idx]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is prev_status
    logs_count = len(invoice.status_log)
    last_log = invoice.status_log[logs_count - 1]
    assert last_log.to is None

    crud.invoice.mark_as(dbsession, invoice_=invoice, status=status)

    assert invoice.status is status
    status_log = dbsession.scalars(
        sa.select(models.StatusLog).where(models.StatusLog.invoice_id == invoice_id)
    ).all()
    assert status_log[logs_count - 1] is last_log
    assert status_log[logs_count - 1].to == FAKE_TIME
    assert status_log[logs_count].status is status
    assert status_log[logs_count].from_ == FAKE_TIME
    assert status_log[logs_count].to is None


def test_crud_mark_as_bad_status(dbsession, init_data):
    client = init_data.clients[3]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is models.InvoiceStatus.PAID
    logs_count = len(invoice.status_log)
    last_log = invoice.status_log[logs_count - 1]
    assert last_log.to is None

    with pytest.raises(AssertionError):
        crud.invoice.mark_as(
            dbsession, invoice_=invoice, status=models.InvoiceStatus.DRAFT
        )

    assert invoice.status is models.InvoiceStatus.PAID
    status_log = dbsession.scalars(
        sa.select(models.StatusLog).where(models.StatusLog.invoice_id == invoice_id)
    ).all()
    assert len(status_log) == logs_count
    assert status_log[logs_count - 1] is last_log
    assert status_log[logs_count - 1].to is None
    assert status_log[logs_count - 1].status is models.InvoiceStatus.PAID


def test_crud_mark_as_commit_error(dbsession, init_data, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    client = init_data.clients[1]
    invoice = client.invoices[0]
    invoice_id = invoice.id
    assert invoice.status is models.InvoiceStatus.EMITTED
    logs_count = len(invoice.status_log)
    last_log = invoice.status_log[logs_count - 1]
    assert last_log.to is None

    with pytest.raises(crud.CrudError):
        crud.invoice.mark_as(
            dbsession, invoice_=invoice, status=models.InvoiceStatus.PAID
        )

    assert invoice.status is models.InvoiceStatus.EMITTED
    status_log = dbsession.scalars(
        sa.select(models.StatusLog).where(models.StatusLog.invoice_id == invoice_id)
    ).all()
    assert len(status_log) == logs_count
    assert status_log[logs_count - 1] is last_log
    assert status_log[logs_count - 1].to is None
    assert status_log[logs_count - 1].status is models.InvoiceStatus.EMITTED


def test_invoice_from_orm(dbsession, init_data):
    invoice = init_data.invoices[0]

    from_db = schemas.Invoice.from_orm(invoice)

    assert from_db.id == invoice.id
    assert from_db.raw_amount == invoice.raw_amount
    assert from_db.vat == invoice.vat
    assert from_db.net_amount == from_db.raw_amount + from_db.vat
    assert from_db.status == invoice.status
    assert from_db.client_id == invoice.client_id
    for i, item in enumerate(from_db.items):
        assert item == schemas.Item.from_orm(invoice.items[i])
    i = 0
    for status, log in from_db.status_log.items():
        assert log == schemas.StatusLog.from_orm(invoice.status_log[i])
        i += 1
