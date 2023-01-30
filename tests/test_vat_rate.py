# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for `dfacto` package."""

# Cf. https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2

import pytest
import sqlalchemy as sa
import sqlalchemy.exc

from dfacto.models.command import CommandStatus
from dfacto.models import models
from dfacto.models.vat_rate import VatRateModel
from dfacto.models.schemas import VatRate, VatRateCreate, VatRateUpdate


@pytest.fixture()
def mock_commit(monkeypatch):
    state = {"failed": False}
    called = []

    def _commit(_):
        called.append(True)
        if state["failed"]:
            raise sa.exc.SQLAlchemyError("Commit failed")

    # monkeypatch.setattr("dfacto.models.vat_rate.Session.commit", _commit)
    monkeypatch.setattr("dfacto.models.vat_rate.scoped_session.commit", _commit)

    return state, called


@pytest.fixture()
def mock_get(monkeypatch):
    state = {"failed": False}
    called = []

    def _get(_1, _2, _3):
        called.append(True)
        if state["failed"]:
            raise sa.exc.SQLAlchemyError("Get failed")

    monkeypatch.setattr("dfacto.models.vat_rate.scoped_session.get", _get)

    return state, called


@pytest.fixture()
def mock_select(monkeypatch):
    state = {"failed": False}
    called = []

    def _select(_):
        called.append(True)
        if state["failed"]:
            raise sa.exc.SQLAlchemyError("Select failed")

    monkeypatch.setattr("dfacto.models.vat_rate.sqlalchemy.select", _select)

    return state, called


def test_init(dbsession):
    assert dbsession.scalars(sa.select(models.VatRate)).first() is None

    VatRateModel(dbsession)

    vat_rates = dbsession.scalars(sa.select(models.VatRate)).all()
    assert len(vat_rates) == 3
    for i in range(len(VatRateModel.PRESET_RATE_IDS)):
        assert vat_rates[i].id == VatRateModel.PRESET_RATES[i]["id"]
        assert vat_rates[i].rate == VatRateModel.PRESET_RATES[i]["rate"]


def test_init_twice(dbsession, vat_rate_model, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    assert dbsession.scalars(sa.select(models.VatRate)).first() is not None

    VatRateModel(dbsession)

    vat_rates = dbsession.scalars(sa.select(models.VatRate)).all()
    assert len(vat_rates) == 3
    assert len(called) == 0


def test_get_default(vat_rate_model):
    report = vat_rate_model.get()

    assert report.status == CommandStatus.COMPLETED
    default_vr = report.body
    assert isinstance(default_vr, VatRate)
    assert default_vr.id == VatRateModel.DEFAULT_RATE_ID
    assert default_vr.rate == VatRateModel.PRESET_RATES[0]["rate"]


def test_get(vat_rate_model):
    report = vat_rate_model.get(VatRateModel.DEFAULT_RATE_ID + 1)

    assert report.status == CommandStatus.COMPLETED
    vr = report.body
    assert isinstance(vr, VatRate)
    assert vr.id == VatRateModel.PRESET_RATES[1]["id"]
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]


def test_get_unknown(vat_rate_model):
    response = vat_rate_model.get(10)

    assert response.status == CommandStatus.COMPLETED
    assert response.body is None


def test_get_error(vat_rate_model, mock_get):
    state, _called = mock_get
    state["failed"] = True

    response = vat_rate_model.get()

    assert response.status == CommandStatus.FAILED
    assert response.reason.startswith("VAT_RATE-GET - SQL or database error:")


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
    assert response.reason.startswith("VAT_RATE-GET-MULTI - SQL or database error:")


def test_add(dbsession, vat_rate_model):
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
    ).first() is None

    report = vat_rate_model.add(VatRateCreate(rate=30))

    assert report.status == CommandStatus.COMPLETED
    assert isinstance(report.body, models.VatRate)
    assert report.body.rate == 30.0
    try:
        vr = dbsession.scalars(sa.select(models.VatRate).where(models.VatRate.rate == 30.0)).one()
    except sa.exc.SQLAlchemyError:
        vr = None
    assert vr is not None
    assert vr.rate == 30.0


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_add_commit_error(dbsession, vat_rate_model, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
    ).first() is None

    report = vat_rate_model.add(VatRateCreate(rate=30))

    assert report.status == CommandStatus.FAILED
    assert report.reason.startswith("VAT_RATE-ADD - Cannot add VAT rate 30")
    assert report.body is None


def test_update(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 1
    vr = dbsession.scalars(sa.select(models.VatRate).where(models.VatRate.id == vr_id)).first()
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]

    report = vat_rate_model.update(vr_id, VatRateUpdate(10.0))

    assert report.status == CommandStatus.COMPLETED
    assert isinstance(report.body, models.VatRate)
    assert report.body.rate == 10.0
    vr = dbsession.scalars(sa.select(models.VatRate).where(models.VatRate.id == vr_id)).first()
    assert vr.rate == 10.0


def test_update_same_rate(dbsession, vat_rate_model, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    vr_id = VatRateModel.DEFAULT_RATE_ID + 1
    vr = dbsession.scalars(sa.select(models.VatRate).where(models.VatRate.id == vr_id)).first()
    rate = VatRateModel.PRESET_RATES[1]["rate"]
    assert vr.rate == rate

    report = vat_rate_model.update(vr_id, VatRateUpdate(rate))

    assert report.status == CommandStatus.COMPLETED
    vr = dbsession.scalars(sa.select(models.VatRate).where(models.VatRate.id == vr_id)).first()
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]
    assert len(called) == 0


def test_update_unknown(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is None

    report = vat_rate_model.update(vr_id, VatRateUpdate(12.3))

    assert report.status == CommandStatus.FAILED
    assert report.reason == f"VAT_RATE-UPDATE - VAT rate {vr_id} not found."
    assert report.body is None


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_update_commit_error(dbsession, vat_rate_model, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    vr_id = VatRateModel.DEFAULT_RATE_ID + 1
    vr = dbsession.scalars(sa.select(models.VatRate).where(models.VatRate.id == vr_id)).first()
    assert vr.rate == VatRateModel.PRESET_RATES[1]["rate"]

    report = vat_rate_model.update(vr_id, VatRateUpdate(10.0))

    assert report.status == CommandStatus.FAILED
    assert report.reason.startswith(
        f"VAT_RATE-UPDATE - Cannot update VAT rate {vr_id}:"
    )
    assert report.body is None


def test_delete(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is None
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    dbsession.commit()
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is not None

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.COMPLETED
    assert isinstance(report.body, models.VatRate)
    assert report.body.rate == 12.3
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is None


def test_delete_unknown(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is None

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.FAILED
    assert report.reason == f"VAT_RATE-DELETE - VAT rate {vr_id} not found."
    assert report.body is None


def test_delete_default(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is not None

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.REJECTED
    assert report.reason == "VAT_RATE-DELETE - Default VAT rates cannot be deleted."
    assert report.body is None
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is not None


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_delete_in_use(dbsession, vat_rate_model):
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    service = models._Service(name="A service", unit_price=100.0, vat_rate_id=vr_id)
    dbsession.add(service)
    dbsession.commit()
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is not None

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.REJECTED
    assert report.reason == f"VAT_RATE-DELETE - VAT rate with id {vr_id} is used by at least 'A service' service."
    assert report.body is None


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_delete_commit_error(dbsession, vat_rate_model, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is None
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is not None

    report = vat_rate_model.delete(vr_id)

    assert report.status == CommandStatus.FAILED
    assert report.reason.startswith(
        f"VAT_RATE-DELETE - Cannot delete VAT rate {vr_id}:"
    )
    assert report.body is None


def test_reset(dbsession, vat_rate_model):
    # Change the second preset rate
    dbsession.execute(
        sa.update(models.VatRate), [{"id": VatRateModel.DEFAULT_RATE_ID + 1, "rate": 10.0}]
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
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is None


def test_reset_some_in_use(dbsession, vat_rate_model):
    # Add a not-used rate
    vr_id = VatRateModel.DEFAULT_RATE_ID + 3
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id, "rate": 12.3}])
    # Add an in-use rate
    vr_id_in_use = VatRateModel.DEFAULT_RATE_ID + 4
    dbsession.execute(sa.insert(models.VatRate), [{"id": vr_id_in_use, "rate": 45.6}])
    service = models._Service(name="A service", unit_price=100.0, vat_rate_id=vr_id_in_use)
    dbsession.add(service)
    dbsession.commit()
    # Check that test conditions are OK
    assert len(dbsession.scalars(sa.select(models.VatRate)).all()) == 5

    report = vat_rate_model.reset()

    assert report.status == CommandStatus.COMPLETED
    assert report.reason == "VAT_RATE-RESET - Some VAT rate are in-use: all are kept."
    assert report.body is None
    # The not-used rate is present
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id)
    ).first() is not None
    # The in-use rate is present
    assert dbsession.scalars(
        sa.select(models.VatRate).where(models.VatRate.id == vr_id_in_use)
    ).first() is not None


@pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
def test_reset_commit_error(dbsession, vat_rate_model, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    report = vat_rate_model.reset()

    assert report.status == CommandStatus.FAILED
    assert report.reason == "VAT_RATE-RESET - SQL error while resetting VAT rates."
    assert report.body is None
