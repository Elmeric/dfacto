import datetime
import random
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from dfacto.models import db
from dfacto.models.basket import BasketModel
from dfacto.models.client import ClientModel
from dfacto.models.db import BaseModel
from dfacto.models.invoice import InvoiceModel
from dfacto.models.item import ItemModel
from dfacto.models.models import InvoiceStatus, _Client
from dfacto.models.schemas import (
    ServiceCreate,
    ServiceUpdate,
    VatRateCreate,
    VatRateUpdate,
)
from dfacto.models.service import ServiceModel
from dfacto.models.vat_rate import VatRateModel
from dfacto.models import crud, models, schemas


def main():
    print(f"Creating db schema: {db.engine} {id(db.engine)}", db.Session)
    BaseModel.metadata.create_all(db.engine)
    print("DB schema is created")

    start_time = datetime.datetime.now()

    vat_rate_model = VatRateModel(db.Session)
    service_model = ServiceModel(db.Session)
    item_model = ItemModel(db.Session, service_model)
    basket_model = BasketModel(db.Session, service_model, item_model)
    invoice_model = InvoiceModel(db.Session, service_model, item_model, basket_model)
    client_model = ClientModel(db.Session, basket_model)

    cmd_report = vat_rate_model.get_default()
    print(cmd_report.body)

    cmd_report = vat_rate_model.get_multi()
    print(cmd_report.body)

    v = vat_rate_model.get(vat_rate_model.DEFAULT_RATE_ID + 1)
    print(v.body)

    cmd_report = vat_rate_model.update(
        vat_rate_model.DEFAULT_RATE_ID + 1, VatRateUpdate(5.5)
    )
    print(cmd_report)

    cmd_report = vat_rate_model.add(VatRateCreate(30))
    print(cmd_report)

    # try:
    #     vat_rate_model.delete(vat_rate_model.DEFAULT_RATE_ID + 2)
    # except RejectedCommand as exc:
    #     print(exc)

    # vat_rate_model.reset()
    cmd_report = vat_rate_model.get_multi()
    vat_rates = cmd_report.body
    print(vat_rates)

    for vr in vat_rates:
        cmd_report = vat_rate_model.delete(vr.id)
        print(cmd_report, cmd_report.body)

    cmd_report = service_model.add(
        ServiceCreate(
            name=f"Service {random.randint(1, 1000)}",
            unit_price=100.0,
            vat_rate_id=vat_rate_model.DEFAULT_RATE_ID,
        )
    )
    print(cmd_report, cmd_report.body)

    cmd_report = service_model.get(1)
    print(cmd_report, cmd_report.body)

    # s2 = service_model.update(s.id, name="New service")
    # print(s2)
    cmd_report = service_model.update(1, ServiceUpdate(unit_price=50))
    print(cmd_report, cmd_report.body)
    cmd_report = service_model.update(2, ServiceUpdate(vat_rate_id=3))
    print(cmd_report, cmd_report.body)
    vat_rate_model.add(VatRateCreate(30))
    cmd_report = service_model.update(
        2, ServiceUpdate(name="Great service", unit_price=75, vat_rate_id=4)
    )
    print(cmd_report, cmd_report.body)

    cmd_report = service_model.delete(7)
    print(cmd_report, cmd_report.body)

    cmd_report = service_model.get_multi()
    services = cmd_report.body
    print(services)

    cmd_report = vat_rate_model.delete(4)
    print(cmd_report, cmd_report.body)

    clients = client_model.list_all()
    if not any(c.name == "John Doe" for c in clients):
        cmd_report = client_model.add(
            name="John Doe",
            address="1 rue du coin",
            zip_code="12345",
            city="ICI",
        )
        print(cmd_report)

    cl: _Client = db.Session.get(_Client, 1)
    if cl.has_emitted_invoices:
        print(f"Client {cl.name} has emitted invoices")
    else:
        print(f"Client {cl.name} has no emitted invoices")

    c: _Client = db.Session.execute(
        select(_Client).filter(_Client.has_emitted_invoices)
    ).scalar()
    if c is not None:
        print(f"Client with emitted invoices: {c.name}, {c.invoices[0].code}")

    cmd_report = client_model.delete(cl.id)
    print(cmd_report)

    cmd_report = client_model.add(
        name="John Doe",
        address="1 rue du coin",
        zip_code="12345",
        city="ICI",
    )
    print(cmd_report)

    cl: _Client = db.Session.get(_Client, 1)
    cmd_report = invoice_model.create_from_basket(cl.basket.id)
    print(cmd_report)

    cmd_report = basket_model.add_item(cl.basket.id, 2, 2)
    print(cmd_report)

    cmd_report = invoice_model.create_from_basket(cl.basket.id)
    # inv = invoice.create_from_basket(cl.basket.id, clear_basket=False)
    print(cmd_report)

    cmd_report = basket_model.add_item(cl.basket.id, 3, 3)
    cmd_report = basket_model.add_item(cl.basket.id, 4, 4)
    for it in cl.basket.items:
        print(it.service.name)
    basket_model.remove_item(2)
    for it in cl.basket.items:
        print(it.service.name)

    inv = invoice_model.list_all()[-1]
    cmd_report = invoice_model.remove_item(inv.content[0].id)
    print(cmd_report)

    invoice_model.add_item(inv.id, 2, 4)
    invoice_model.update_status(inv.id, InvoiceStatus.PAID)
    cmd_report = invoice_model.update_status(inv.id, InvoiceStatus.DRAFT)
    print(cmd_report)
    print(inv.status)

    cmd_report = invoice_model.create_from_basket(cl.basket.id)
    print(cmd_report)

    print(basket_model.list_all())
    print(invoice_model.get(1))
    print(invoice_model.list_all())

    db.Session.commit()
    db.Session.remove()

    end_time = datetime.datetime.now()
    print(f"exec time: {end_time - start_time}")


def init_services(dbsession):
    preset_rates = [
        {"id": 1, "rate": 0.0},
        {"id": 2, "rate": 5.5},
        {"id": 3, "rate": 20.0},
    ]
    crud.vat_rate.init_defaults(dbsession, preset_rates)

    services = []
    for i in range(5):
        service = models.Service(
            name=f"Service_{i + 1}",
            unit_price=100 + 10 * i,
            vat_rate_id=(i % 3) + 1
        )
        dbsession.add(service)
        dbsession.commit()
        dbsession.refresh(service)
        services.append(service)

    return services


def update():
    print(f"Creating db schema: {db.engine} {id(db.engine)}", db.Session)
    BaseModel.metadata.create_all(db.engine)
    print("DB schema is created")

    services = init_services(db.Session)

    service = services[0]

    updated = crud.service.update(
        db.Session,
        db_obj=service,
        obj_in=schemas.ServiceUpdate(
            name="Wonderful service",
            unit_price=1000.0,
            vat_rate_id=2
        )
    )

    try:
        assert updated.id == service.id
        assert updated.name == "Wonderful service"
        assert updated.unit_price == 1000.0
        assert updated.vat_rate_id == 2
        assert updated.vat_rate.id == 2
        assert updated.vat_rate.rate == 5.5
    except AssertionError as exc:
        print(exc)

    try:
        s = db.Session.get(models.Service, updated.id)
    except SQLAlchemyError:
        s = None

    try:
        assert s.name == "Wonderful service"
        assert s.unit_price == 1000.0
        assert s.vat_rate_id == 2
        assert s.vat_rate.id == 2
        assert s.vat_rate.rate == 5.5
    except AssertionError as exc:
        print(exc)


if __name__ == "__main__":
    try:
        main()
        # update()
    except Exception as exc:
        print(exc)
        sys.exit(1)
