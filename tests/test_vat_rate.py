# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for `dfacto` package."""

# Cf. https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session

from dfacto.models.api.command import CommandStatus
from dfacto.models.schemas import VatRate, VatRateCreate, VatRateUpdate
from dfacto.models import db, models
from dfacto.models.api.api_v1.vat_rate import VatRateModel


@pytest.fixture(autouse=True)
def init_vat_rates(dbsession: sa.orm.scoped_session) -> None:
    db.init_db_data(dbsession)


@pytest.fixture
def vat_rate_model(dbsession):
    return VatRateModel(dbsession)


def test_init(dbsession):
    VatRateModel(dbsession)

    vat_rates = dbsession.scalars(sa.select(models.VatRate)).all()
    assert len(vat_rates) == 3
    for i in range(len(VatRateModel.PRESET_RATE_IDS)):
        assert vat_rates[i].id == VatRateModel.PRESET_RATES[i]["id"]
        assert vat_rates[i].rate == VatRateModel.PRESET_RATES[i]["rate"]


def test_init_twice(dbsession, vat_rate_model, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    VatRateModel(dbsession)

    vat_rates = dbsession.scalars(sa.select(models.VatRate)).all()
    assert len(vat_rates) == 3
    assert len(called) == 0


def test_get(vat_rate_model):
    report = vat_rate_model.get(VatRateModel.DEFAULT_RATE_ID + 1)

    assert report.status == CommandStatus.COMPLETED
    vr = report.body
    assert isinstance(vr, VatRate)
    assert vr.id == VatRateModel.PRESET_RATES[1]["id"]
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]


def test_get_unknown(vat_rate_model):
    response = vat_rate_model.get(10)

    assert response.status == CommandStatus.FAILED
    assert response.reason == "GET - Object 10 not found."
    assert response.body is None


def test_get_error(vat_rate_model, mock_get):
    state, _called = mock_get
    state["failed"] = True

    response = vat_rate_model.get(VatRateModel.DEFAULT_RATE_ID)

    assert response.status == CommandStatus.FAILED
    assert response.reason.startswith("GET - SQL or database error:")


def test_get_default(vat_rate_model):
    report = vat_rate_model.get_default()

    assert report.status == CommandStatus.COMPLETED
    default_vr = report.body
    assert isinstance(default_vr, VatRate)
    assert default_vr.id == VatRateModel.DEFAULT_RATE_ID
    assert default_vr.rate == VatRateModel.PRESET_RATES[0]["rate"]


def test_get_multi(dbsession, vat_rate_model):
    # Add a VAT rate
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    dbsession.commit()

    skip = len(VatRateModel.PRESET_RATE_IDS) - 1
    response = vat_rate_model.get_multi(skip=skip, limit=2)

    assert response.status == CommandStatus.COMPLETED
    vat_rates = response.body
    assert len(vat_rates) == 2
    assert vat_rates[0].id == VatRateModel.PRESET_RATES[skip]["id"]
    assert vat_rates[0].rate == VatRateModel.PRESET_RATES[skip]["rate"]
    assert vat_rates[1].id == vr_id
    assert vat_rates[1].rate == 12.3


def test_get_multi_error(vat_rate_model, mock_select):
    state, _called = mock_select
    state["failed"] = True

    response = vat_rate_model.get_multi(skip=0, limit=2)

    assert response.status == CommandStatus.FAILED
    assert response.reason.startswith("GET-MULTI - SQL or database error:")


def test_get_all(dbsession, vat_rate_model):
    # Add a VAT rate
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    dbsession.commit()

    response = vat_rate_model.get_all()

    assert response.status == CommandStatus.COMPLETED
    vat_rates = response.body
    assert len(vat_rates) == len(VatRateModel.PRESET_RATES) + 1
    for i in range(len(VatRateModel.PRESET_RATES)):
        assert vat_rates[i].id == VatRateModel.PRESET_RATES[i]["id"]
        assert vat_rates[i].rate == VatRateModel.PRESET_RATES[i]["rate"]
    assert vat_rates[3].id == vr_id
    assert vat_rates[3].rate == 12.3


def test_get_all_error(vat_rate_model, mock_select):
    state, _called = mock_select
    state["failed"] = True

    response = vat_rate_model.get_all()

    assert response.status == CommandStatus.FAILED
    assert response.reason.startswith("GET-ALL - SQL or database error:")


def test_add(dbsession, vat_rate_model):
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
        ).first()
        is None
    )

    report = vat_rate_model.add(VatRateCreate(rate=30))

    assert report.status == CommandStatus.COMPLETED
    assert isinstance(report.body, VatRate)
    assert report.body.rate == 30.0
    try:
        vr = dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
        ).one()
    except sa.exc.SQLAlchemyError:
        vr = None
    assert vr is not None
    assert vr.rate == 30.0


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_add_commit_error(dbsession, vat_rate_model, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
        ).first()
        is None
    )

    report = vat_rate_model.add(VatRateCreate(rate=30))

    assert report.status == CommandStatus.FAILED
    assert report.reason.startswith("ADD - Cannot add object")
    assert report.body is None


def test_update(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 1
    vr = dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first()
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]

    report = vat_rate_model.update(vr_id, VatRateUpdate(10.0))

    assert report.status == CommandStatus.COMPLETED
    assert isinstance(report.body, VatRate)
    assert report.body.rate == 10.0
    vr = dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first()
    assert vr.rate == 10.0


def test_update_same_rate(dbsession, vat_rate_model, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    vr_id = VatRateModel.DEFAULT_RATE_ID + 1
    vr = dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first()
    rate = VatRateModel.PRESET_RATES[1]["rate"]
    assert vr.rate == rate

    report = vat_rate_model.update(vr_id, VatRateUpdate(rate))

    assert report.status == CommandStatus.COMPLETED
    vr = dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first()
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]
    assert len(called) == 0


def test_update_unknown(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is None
    )

    report = vat_rate_model.update(vr_id, VatRateUpdate(12.3))

    assert report.status == CommandStatus.FAILED
    assert report.reason == f"UPDATE - Object {vr_id} not found."
    assert report.body is None


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_update_commit_error(dbsession, vat_rate_model, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    vr_id = VatRateModel.DEFAULT_RATE_ID + 1
    vr = dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first()
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]

    report = vat_rate_model.update(vr_id, VatRateUpdate(10.0))

    assert report.status == CommandStatus.FAILED
    assert report.reason.startswith(f"UPDATE - Cannot update object {vr_id}:")
    assert report.body is None


def test_delete(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is None
    )
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    dbsession.commit()
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is not None
    )

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.COMPLETED
    assert report.body is None
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is None
    )


def test_delete_unknown(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is None
    )

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.FAILED
    assert report.reason == f"DELETE - Object {vr_id} not found."
    assert report.body is None


def test_delete_default(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is not None
    )

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.REJECTED
    assert report.reason == "DELETE - Default VAT rates cannot be deleted."
    assert report.body is None
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is not None
    )


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_delete_in_use(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    service = models.Service(name="A service", unit_price=100.0, vat_rate_id=vr_id)
    dbsession.add(service)
    dbsession.commit()
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is not None
    )

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.REJECTED
    assert (
        report.reason
        == f"DELETE - VAT rate with id {vr_id} is used by at least 'A service' service."
    )
    assert report.body is None


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_delete_commit_error(dbsession, vat_rate_model, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is None
    )
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is not None
    )

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.FAILED
    assert report.reason.startswith(f"DELETE - Cannot delete object {vr_id}:")
    assert report.body is None


def test_reset(dbsession, vat_rate_model):
    # Change the second preset rate
    dbsession.execute(
        sa.update(models.VatRate),
        [{"id": VatRateModel.DEFAULT_RATE_ID + 1, "rate": 10.0}],
    )
    # Add a not-used rate
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    dbsession.commit()
    # Check that test conditions are OK
    assert len(dbsession.scalars(sa.select(models.VatRate)).all()) == 4

    report = vat_rate_model.reset()

    assert report.status == CommandStatus.COMPLETED
    assert report.reason is None
    assert report.body is None
    # The second preset rate is reset to its default value
    rate_2 = dbsession.get(models.VatRate, VatRateModel.DEFAULT_RATE_ID + 1)
    assert rate_2.rate == VatRateModel.PRESET_RATES[1]["rate"]
    # The not-used rate is deleted
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is None
    )


def test_reset_some_in_use(dbsession, vat_rate_model):
    # Add a not-used rate
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    # Add an in-use rate
    vr_id_in_use = VatRateModel.DEFAULT_RATE_ID + 4
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id_in_use, "rate": 45.6}])
    service = models.Service(
        name="A service", unit_price=100.0, vat_rate_id=vr_id_in_use
    )
    dbsession.add(service)
    dbsession.commit()
    # Check that test conditions are OK
    assert len(dbsession.scalars(sa.select(models.VatRate)).all()) == 5

    report = vat_rate_model.reset()

    assert report.status == CommandStatus.FAILED
    assert (
        report.reason == "VAT_RATE-RESET - Reset failed: some VAT rates may be in use."
    )
    assert report.body is None
    # The not-used rate is de3eted
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id)
        ).first()
        is None
    )
    # The in-use rate is present
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.id == vr_id_in_use)
        ).first()
        is not None
    )
