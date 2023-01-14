import datetime
import logging
import logging.config
import random
import sys

from sqlalchemy import select

from dfacto.models import basket, client, db, invoice, service, vat_rate
from dfacto.models.model import InvoiceStatus, _Client

# from dcfs_editor.models.initdb import initDb
# from dcfs_editor import dcfsconstants as dc
# from dcfs_editor.logconfig import LOGGING_CONFIG


# logging.config.dictConfig(LOGGING_CONFIG)
# logging.basicConfig(filename='../dcfs_data/log/dcfs_editor.log',
#                     filemode='w',
#                     level=logging.DEBUG,
#                     # format='(%(asctime)s - %(name)s - %(levelname)-5s) - %(message)s',)
#                     format='(%(name)-36s - %(levelname)-5s) - %(message)s', )

logger = logging.getLogger(__name__)


def main():
    db.create_schema()
    #    initDb()

    start_time = datetime.datetime.now()

    vat_rate.init()

    print(vat_rate.get_default())

    vat_rates = vat_rate.list_all()
    print(vat_rates)

    v = vat_rate.get(vat_rate.DEFAULT_RATE_ID + 1)
    print(v)

    v = vat_rate.update(vat_rate.DEFAULT_RATE_ID + 1, 5.5)
    print(v)

    v = vat_rate.add(30)
    print(v)

    # try:
    #     vat_rate.delete(vat_rate.DEFAULT_RATE_ID + 2)
    # except db.RejectedCommand as exc:
    #     print(exc)

    # vat_rate.reset()
    vat_rates = vat_rate.list_all()
    print(vat_rates)

    for vr in vat_rates:
        try:
            vat_rate.delete(vr.id)
        except db.RejectedCommand as exc:
            print(exc)
        except db.FailedCommand as exc:
            print(exc)

    try:
        s1 = service.add(f"Service {random.randint(1, 1000)}", 100.0)
    except db.FailedCommand as exc:
        print(exc)
        return
    else:
        print(s1)

    s = service.get(s1.id)
    print(s)

    # s2 = service.update(s.id, name="New service")
    # print(s2)
    s2 = service.update(1, unit_price=50)
    print(s2)
    s2 = service.update(2, vat_rate_id=3)
    print(s2)
    s2 = service.update(2, name="Great service", unit_price=75, vat_rate_id=4)
    print(s2)

    try:
        service.delete(5)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)

    services = service.list_all()
    print(services)

    try:
        vat_rate.delete(4)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)

    clients = client.list_all()
    if not any(c.name == "John Doe" for c in clients):
        try:
            c1 = client.add(
                name="John Doe",
                address="1 rue du coin",
                zip_code="12345",
                city="ICI",
            )
        except db.RejectedCommand as exc:
            print(exc)
            return
        else:
            print(c1)

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

    try:
        client.delete(cl.id)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)

    try:
        c1 = client.add(
            name="John Doe",
            address="1 rue du coin",
            zip_code="12345",
            city="ICI",
        )
    except db.FailedCommand as exc:
        print(exc)
    else:
        print(c1)

    cl: _Client = db.Session.get(_Client, 1)
    try:
        inv = invoice.create_from_basket(cl.basket.id)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)
    else:
        print(inv)

    it = basket.add_item(cl.basket.id, s2.id, 2)
    print(it)

    try:
        inv = invoice.create_from_basket(cl.basket.id)
        # inv = invoice.create_from_basket(cl.basket.id, clear_basket=False)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)
    else:
        print(inv)

    it1 = basket.add_item(cl.basket.id, 3, 3)
    it2 = basket.add_item(cl.basket.id, 4, 4)
    for it in cl.basket.items:
        print(it.service.name)
    basket.remove_item(it1.id)
    for it in cl.basket.items:
        print(it.service.name)

    try:
        invoice.remove_item(inv.content[0].id)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)

    invoice.add_item(inv.id, 2, 4)
    invoice.update_status(inv.id, InvoiceStatus.PAID)
    try:
        invoice.update_status(inv.id, InvoiceStatus.DRAFT)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)
    print(inv.status)

    inv = invoice.create_from_basket(cl.basket.id)
    try:
        invoice.delete(inv.id)
    except db.RejectedCommand as exc:
        print(exc)
    except db.FailedCommand as exc:
        print(exc)

    db.Session.commit()
    db.Session.remove()

    end_time = datetime.datetime.now()
    print(f"exec time: {end_time - start_time}")

    return

    try:
        c1 = client.add(
            name="John Doe",
            address="1 rue du coin",
            zip_code="12345",
            city="ICI",
        )
    except db.RejectedCommand as exc:
        print(exc)
        return
    else:
        print(c1)

    client.rename(c1.id, "Foo Bar")
    client.change_address(
        c1.id, client.Address("3 imapasse ouverte", "33000", "LA-BAS")
    )
    client.on_hold(c1.id)

    cl = client.get(c1.id)
    print(cl)
    print(cl.basket.content)

    it = basket.add_item(cl.basket.id, s2.id, 2)
    print(it)
    print(cl.basket.content)

    s = service.get(1)
    it = basket.add_item(cl.basket.id, s.id, 2)
    print(it)
    print(cl.basket.content)
    print(f"{cl.basket.raw_amount}, {cl.basket.vat}, {cl.basket.net_amount}")
    #
    #
    # i1 = Invoice(
    #     code="FC0001",
    #     date=datetime.date.today(),
    #     due_date=datetime.date.today(),
    #     status="DRAFT",
    # )
    # i2 = Invoice(
    #     code="FC0002",
    #     date=datetime.date.today(),
    #     due_date=datetime.date.today(),
    #     status="PAID",
    # )
    # i3 = Invoice(
    #     code="FC0003",
    #     date=datetime.date.today(),
    #     due_date=datetime.date.today(),
    #     status="EMITTED",
    # )
    # db.Session.add_all([c1, c2, c3, i1, i2, i3])
    #
    # i1.client = c1
    # i3.client = c3
    # c2.invoices.append(i2)
    #
    # db.Session.commit()
    #
    # print("*" * 10)
    # stmt = select(_Client).where(_Client.name.in_(["John Doe", "Foo", "Bar"]))
    # for client in db.Session.scalars(stmt):
    #     print(client)
    #     if client.name == "John Doe":
    #         client.invoices = []
    #     if client.name == "Bar":
    #         bar_id = client.id
    # bar = db.Session.get(_Client, bar_id)
    # print(">> ", bar_id, bar)
    # db.Session.delete(bar)
    # db.Session.commit()

    db.Session.remove()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("exception")
        sys.exit(1)
