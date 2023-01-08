import datetime
import logging
import logging.config
import sys

from sqlalchemy import insert, select, update, delete, ScalarResult

from dfacto.models import db
from dfacto.models.vat_rate import VatRate, VatRateModel
from dfacto.models.service import Service, ServiceModel, _Service
from dfacto.models.model import Client, Invoice

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

    vat_rate_model = VatRateModel()

    vat_rates = vat_rate_model.list_vat_rates()
    print(vat_rates)

    v = vat_rate_model.get_vat_rate(vat_rate_model.DEFAULT_RATE_ID + 1)
    print(v)

    v = vat_rate_model.update_vat_rate(vat_rate_model.DEFAULT_RATE_ID + 1, 10)
    print(v)

    v = vat_rate_model.add_vat_rate(30)
    print(v)

    try:
        vat_rate_model.delete_vat_rate(vat_rate_model.DEFAULT_RATE_ID + 2)
    except db.RejectedCommand as exc:
        print(exc)

    vat_rate_model.reset_vat_rates()
    vat_rates = vat_rate_model.list_vat_rates()
    print(vat_rates)

    s1 = _Service("Service 1", 100.0)
    db.Session.add(s1)
    db.Session.commit()

    s = ServiceModel.get_service(s1.id)
    print(s)

    # for s, p, v in (("Service 1", 25.0, None), ("Service 2", 250.0, 3)):
    #     # v = v or 1
    #     print(f"Creating service: {s}, {p}, {v}")
    #     service = _Service(s, p)
    #     if v is not None:
    #         vat_rate = db.Session.get(_VatRate, v)
    #         service.vat_rate = vat_rate
    #     db.Session.add(service)
    # db.Session.commit()
    #
    # c1 = Client(
    #     name="John Doe",
    #     code="CL0001",
    #     address="1 rue du coin",
    #     zip_code="12345",
    #     city="ICI",
    #     active=True,
    # )
    # db.Session.add(c1)
    # db.Session.commit()
    #
    # client = db.Session.scalars(select(Client).filter_by(name="John Doe").limit(1)).first()
    # service = db.Session.get(_Service, 2)
    # print(client, service)
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
    # stmt = select(Client).where(Client.name.in_(["John Doe", "Foo", "Bar"]))
    # for client in db.Session.scalars(stmt):
    #     print(client)
    #     if client.name == "John Doe":
    #         client.invoices = []
    #     if client.name == "Bar":
    #         bar_id = client.id
    # bar = db.Session.get(Client, bar_id)
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
