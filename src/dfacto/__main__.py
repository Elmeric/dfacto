import datetime
import random
import sys

from sqlalchemy import select, exc

from dfacto.models import db
from dfacto.models.basket import BasketModel
from dfacto.models.client import ClientModel
from dfacto.models.invoice import InvoiceModel
from dfacto.models.item import ItemModel
from dfacto.models.db import BaseModel
from dfacto.models.models import InvoiceStatus, _Client
from dfacto.models.service import ServiceModel
from dfacto.models.vat_rate import VatRateModel
from dfacto.models.schemas import VatRateCreate, VatRateUpdate


def main():
    print(f"Creating db schema: {db.engine} {id(db.engine)}", db.Session)
    BaseModel.metadata.create_all(db.engine)
    print("DB schema is created")
    # db.create_schema()
    #    initDb()

    start_time = datetime.datetime.now()

    vat_rate_model = VatRateModel(db.Session)
    service_model = ServiceModel(db.Session, vat_rate_model)
    item_model = ItemModel(db.Session, service_model)
    basket_model = BasketModel(db.Session, service_model, item_model)
    invoice_model = InvoiceModel(db.Session, service_model, item_model, basket_model)
    client_model = ClientModel(db.Session, basket_model)

    cmd_report = vat_rate_model.get()
    print(cmd_report.body)

    cmd_report = vat_rate_model.get_multi()
    print(cmd_report.body)

    v = vat_rate_model.get(vat_rate_model.DEFAULT_RATE_ID + 1)
    print(v.body)

    cmd_report = vat_rate_model.update(vat_rate_model.DEFAULT_RATE_ID + 1, VatRateCreate(5.5))
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
        print(cmd_report)

    cmd_report = service_model.add(f"Service {random.randint(1, 1000)}", 100.0)
    print(cmd_report)

    cmd_report = service_model.get(1)
    print(cmd_report)

    # s2 = service_model.update(s.id, name="New service")
    # print(s2)
    cmd_report = service_model.update(1, unit_price=50)
    print(cmd_report)
    cmd_report = service_model.update(2, vat_rate_id=3)
    print(cmd_report)
    vat_rate_model.add(VatRateCreate(30))
    cmd_report = service_model.update(
        2, name="Great service", unit_price=75, vat_rate_id=4
    )
    print(cmd_report)

    cmd_report = service_model.delete(5)
    print(cmd_report)

    services = service_model.list_all()
    print(services)

    cmd_report = vat_rate_model.delete(4)
    print(cmd_report)

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


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc)
        sys.exit(1)
